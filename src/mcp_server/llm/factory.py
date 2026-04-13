from pydantic import ValidationError

from mcp_server.config import get_settings
from mcp_server.llm.anthropic import AnthropicProvider
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.openai import OpenAIProvider


def get_provider(provider_name: str | None = None) -> LLMProvider:
    try:
        settings = get_settings()
    except ValidationError as e:
        missing = [str(err["loc"][0]) for err in e.errors() if err["type"] == "missing"]
        if missing:
            raise SystemExit(
                f"Missing required configuration: {', '.join(missing)}\n"
                "Add these to your .env file. Example: ANTHROPIC_API_KEY=sk-ant-..."
            ) from None
        raise SystemExit(f"Configuration error: {e}") from None

    name = provider_name or settings.default_provider

    if name == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
    elif name == "openai":
        if settings.openai_api_key is None:
            raise ValueError(
                "OpenAI API key not configured. Add OPENAI_API_KEY to your .env file."
            )
        return OpenAIProvider(
            api_key=settings.openai_api_key.get_secret_value()
        )
    else:
        raise ValueError(
            f"Unknown provider: {name!r}. Valid options: anthropic, openai"
        )
