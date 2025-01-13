from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Tuple
from llm import LLM
import subprocess
import os
import aiohttp
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomParams
from prompts import INTERVIEW_PROMPT, ASSESS_CANDIDATE_PROMPT

# Load environment variables
load_dotenv(override=True)

# Maximum number of bot instances allowed per room
MAX_BOTS_PER_ROOM = 1

# Dictionary to track bot processes: {pid: (process, room_url)}
bot_procs = {}

# Store Daily API helpers
daily_helpers = {}

def cleanup():
    """Cleanup function to terminate all bot processes.
    Called during server shutdown.
    """
    for entry in bot_procs.values():
        proc = entry[0]
        proc.terminate()
        proc.wait()

def get_bot_file():
    """Get the bot implementation file based on environment configuration."""
    bot_implementation = os.getenv("BOT_IMPLEMENTATION", "openai").lower().strip()
    if not bot_implementation:
        bot_implementation = "openai"
    if bot_implementation not in ["openai", "gemini"]:
        raise ValueError(
            f"Invalid BOT_IMPLEMENTATION: {bot_implementation}. Must be 'openai' or 'gemini'"
        )
    return f"bot_{bot_implementation}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager that handles startup and shutdown tasks."""
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
        aiohttp_session=aiohttp_session,
    )
    yield
    await aiohttp_session.close()
    cleanup()

# Initialize FastAPI app with lifespan manager
app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

llm = LLM()

class ChatRequest(BaseModel):
    resume: str
    messages: List[Dict[str, str]]

@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}

@app.post("/chat")
async def chat_completion(request: ChatRequest):
    try:
        # Format the system prompt with the resume
        system_prompt = INTERVIEW_PROMPT.format(RESUME=request.resume)
        
        # Add the system prompt as the first message
        messages = [{"role": "system", "content": system_prompt}] + request.messages
        
        response = llm.chat_completion(
            messages=messages,
        )
        return {"content": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/feedback")
async def get_feedback(request: ChatRequest):
    try:
        # Format the system prompt with the resume
        system_prompt = ASSESS_CANDIDATE_PROMPT.format(RESUME=request.resume, CONVERSATION=request.messages)

        print(system_prompt)
        
        # Add the system prompt as the first message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Please provide assessment results based on my interview."}
        ]
        
        response = llm.chat_completion(
            messages=messages,
        )
        return {"content": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a router for Daily.co related endpoints
daily_router = APIRouter(prefix="/daily")

async def create_room_and_token() -> Tuple[str, str]:
    """Helper function to create a Daily room and generate an access token."""
    room = await daily_helpers["rest"].create_room(DailyRoomParams())
    if not room.url:
        raise HTTPException(status_code=500, detail="Failed to create room")

    token = await daily_helpers["rest"].get_token(room.url)
    if not token:
        raise HTTPException(status_code=500, detail=f"Failed to get token for room: {room.url}")

    return room.url, token

@daily_router.get("/")
async def start_agent(request: Request):
    """Endpoint for direct browser access to the bot."""
    print("Creating room")
    room_url, token = await create_room_and_token()
    print(f"Room URL: {room_url}")

    # Check if there is already an existing process running in this room
    num_bots_in_room = sum(
        1 for proc in bot_procs.values() if proc[1] == room_url and proc[0].poll() is None
    )
    if num_bots_in_room >= MAX_BOTS_PER_ROOM:
        raise HTTPException(status_code=500, detail=f"Max bot limit reached for room: {room_url}")

    # Spawn a new bot process
    try:
        bot_file = get_bot_file()
        proc = subprocess.Popen(
            [f"python3 -m {bot_file} -u {room_url} -t {token}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    return RedirectResponse(room_url)

@daily_router.post("/connect")
async def rtvi_connect(request: Request) -> Dict[Any, Any]:
    """RTVI connect endpoint that creates a room and returns connection credentials."""
    print("Creating room for RTVI connection")
    room_url, token = await create_room_and_token()
    print(f"Room URL: {room_url}")

    # Start the bot process
    try:
        bot_file = get_bot_file()
        proc = subprocess.Popen(
            [f"python3 -m {bot_file} -u {room_url} -t {token}"],
            shell=True,
            bufsize=1,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        bot_procs[proc.pid] = (proc, room_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start subprocess: {e}")

    # Return the authentication bundle in format expected by DailyTransport
    return {"room_url": room_url, "token": token}

@daily_router.get("/status/{pid}")
def get_status(pid: int):
    """Get the status of a specific bot process."""
    # Look up the subprocess
    proc = bot_procs.get(pid)

    # If the subprocess doesn't exist, return an error
    if not proc:
        raise HTTPException(status_code=404, detail=f"Bot with process id: {pid} not found")

    # Check the status of the subprocess
    status = "running" if proc[0].poll() is None else "finished"
    return JSONResponse({"bot_id": pid, "status": status})

# Include the Daily.co router in the main app
app.include_router(daily_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 