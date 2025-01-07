import base64
import logging
import os
from typing import Callable, List, Dict, Optional, Tuple
from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, ToolMessage
from aws_lambda_powertools.metrics import MetricResolution, MetricUnit
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLAUDE_35_SONNET_V2_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

logger = logging.getLogger(__name__)


class LLM:
    def __init__(self):
        logger.info("Initializing ClaudeLangchain")
        # Set region from environment variable
        os.environ['AWS_DEFAULT_REGION'] = os.getenv('REGION', 'us-east-1')

    def chat_completion(
            self,
            messages: list,
            model_id: str = CLAUDE_35_SONNET_V2_MODEL_ID,
            temperature: float = 0.1,
            max_tokens: int = 8192,
    ) -> str:
        try:
            logger.info(f"Calling Claude API with model {model_id}")

            client = ChatBedrock(
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            response: AIMessage = client.invoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"Error during Claude API call: {e}")
            raise

