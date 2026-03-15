from mcp_server.config import get_settings
from mcp_server.llm.anthropic import AnthropicProvider
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.openai import OpenAIProvider


def get_provider(provider_name: str | None = None) -> LLMProvider:
    settings = get_settings()
    name = provider_name or settings.default_provider

    if name == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
    elif name == "openai":
        if settings.openai_api_key is None:
            raise ValueError("OpenAI API key not configured")
        return OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value()
        )
    else:
        raise ValueError(f"Unknown provider: {name}")
