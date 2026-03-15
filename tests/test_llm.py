from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock

from mcp_server.llm.anthropic import AnthropicProvider
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.openai import OpenAIProvider


def test_anthropic_satisfies_protocol() -> None:
    provider = AnthropicProvider(api_key="test-key")
    assert isinstance(provider, LLMProvider)


def test_openai_satisfies_protocol() -> None:
    provider = OpenAIProvider(api_key="test-key")
    assert isinstance(provider, LLMProvider)


@patch("mcp_server.llm.factory.get_settings")
def test_factory_returns_anthropic(mock_get_settings: MagicMock) -> None:
    from mcp_server.llm.factory import get_provider

    mock_settings = MagicMock()
    mock_settings.default_provider = "anthropic"
    mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
    mock_get_settings.return_value = mock_settings
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)


@patch("mcp_server.llm.factory.get_settings")
def test_factory_returns_openai(mock_get_settings: MagicMock) -> None:
    from mcp_server.llm.factory import get_provider

    mock_settings = MagicMock()
    mock_settings.default_provider = "openai"
    mock_settings.openai_api_key.get_secret_value.return_value = "test-key"
    mock_get_settings.return_value = mock_settings
    provider = get_provider()
    assert isinstance(provider, OpenAIProvider)


@patch("mcp_server.llm.factory.get_settings")
def test_factory_raises_on_unknown(mock_get_settings: MagicMock) -> None:
    from mcp_server.llm.factory import get_provider

    mock_settings = MagicMock()
    mock_settings.default_provider = "unknown"
    mock_get_settings.return_value = mock_settings
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider()


@pytest.mark.asyncio
async def test_anthropic_complete() -> None:
    provider = AnthropicProvider(api_key="test-key")
    mock_response = MagicMock()
    mock_response.content = [TextBlock(type="text", text="Hello from Claude")]
    provider.client = MagicMock()
    provider.client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete(
        messages=[{"role": "user", "content": "Hi"}], model="claude-sonnet-4-20250514"
    )
    assert result == "Hello from Claude"


@pytest.mark.asyncio
async def test_openai_complete() -> None:
    provider = OpenAIProvider(api_key="test-key")
    mock_message = MagicMock()
    mock_message.message.content = "Hello from GPT"
    mock_response = MagicMock()
    mock_response.choices = [mock_message]
    provider._client = MagicMock()
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete(
        messages=[{"role": "user", "content": "Hi"}], model="gpt-4o"
    )
    assert result == "Hello from GPT"
