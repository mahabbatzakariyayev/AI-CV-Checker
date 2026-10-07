from app.config import get_settings
from app.services.llm.azure_openai_client import AzureOpenAIClient
from app.services.llm.base import LLMClient
from app.services.llm.mock_llm_client import MockLLMClient


def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.llm_backend == "azure" or settings.llm_provider == "azure_openai":
        return AzureOpenAIClient()
    return MockLLMClient()
