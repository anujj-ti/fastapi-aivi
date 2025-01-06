from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from llm import LLM

app = FastAPI()
llm = LLM()

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}

@app.post("/chat")
async def chat_completion(request: ChatRequest):
    print(request)
    try:
        response = llm.chat_completion(
            messages=request.messages,
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 