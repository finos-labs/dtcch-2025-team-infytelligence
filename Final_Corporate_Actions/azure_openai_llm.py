# azure_openai_llm.py
import os
from langchain.chat_models import AzureChatOpenAI

class AzureOpenAIClient:
    def __init__(self):
        """
        For LangChain 0.0.199 + Pydantic < 2 + openai==0.27.2
        Maps openai_api_key to AZURE_OPENAI_KEY so no missing key error.
        """
        azure_api_key = os.getenv("AZURE_OPENAI_KEY", "")
        azure_api_base = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        azure_api_version = os.getenv("AZURE_OPENAI_VERSION", "2023-05-15")
        azure_deployment = os.getenv("AZURE_DEPLOYMENT_NAME", "")

        self.llm = AzureChatOpenAI(
            openai_api_key=azure_api_key,
            openai_api_base=azure_api_base,
            openai_api_version=azure_api_version,
            deployment_name=azure_deployment,
            openai_api_type="azure",
            temperature=0
        )

    def get_llm(self):
        return self.llm 