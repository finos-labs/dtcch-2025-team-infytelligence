# bedrock_llm.py
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()  # Load .env file

class BedrockClient:
    """
    Minimalistic Bedrock client that sends a prompt and returns a text response.
    """

    def __init__(self):
        # Read from environment
        self.region_name = os.getenv("AWS_REGION", "us-west-2")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
        self.client = boto3.client("bedrock-runtime", region_name=self.region_name)

    def predict(self, prompt: str) -> str:
        """
        Send plain text prompt to the Bedrock model, return raw text response.
        """
        response = self.client.invoke_model(
            modelId=self.model_id,
            contentType="text/plain",
            accept="application/json",
            body=prompt
        )
        # Read the returned JSON from the response body (a stream)
        result_json = response["body"].read().decode("utf-8")
        parsed = json.loads(result_json)
        # For Claude or Titan, check the exact JSON structure. Typically "completion" or "results"
        completion_text = parsed.get("completion", "")
        return completion_text
