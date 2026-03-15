from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock, ToolUseBlock

from mcp_server.llm.anthropic import AnthropicProvider
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.openai import OpenAIProvider
from mcp_server.llm.types import LLMResponse, ToolSchema


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


# --- complete_with_tools tests ---


DUMMY_TOOLS: list[ToolSchema] = [
    {
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
            "required": ["arg1"],
        },
    }
]


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_text_response() -> None:
    provider = AnthropicProvider(api_key="test-key")
    mock_response = MagicMock()
    mock_response.content = [TextBlock(type="text", text="Just text")]
    provider.client = MagicMock()
    provider.client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Hi"}],
        model="claude-sonnet-4-20250514",
        tools=DUMMY_TOOLS,
    )
    assert isinstance(result, LLMResponse)
    assert result.text == "Just text"
    assert result.tool_calls == []
    assert not result.is_tool_use


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_tool_use() -> None:
    provider = AnthropicProvider(api_key="test-key")
    mock_response = MagicMock()
    mock_response.content = [
        ToolUseBlock(
            type="tool_use",
            id="call_123",
            name="test_tool",
            input={"arg1": "hello"},
        )
    ]
    provider.client = MagicMock()
    provider.client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Use the tool"}],
        model="claude-sonnet-4-20250514",
        tools=DUMMY_TOOLS,
    )
    assert result.is_tool_use
    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_123"
    assert result.tool_calls[0].name == "test_tool"
    assert result.tool_calls[0].arguments == {"arg1": "hello"}


@pytest.mark.asyncio
async def test_anthropic_complete_with_tools_passes_system() -> None:
    provider = AnthropicProvider(api_key="test-key")
    mock_response = MagicMock()
    mock_response.content = [TextBlock(type="text", text="ok")]
    provider.client = MagicMock()
    provider.client.messages.create = AsyncMock(return_value=mock_response)

    await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Hi"}],
        model="claude-sonnet-4-20250514",
        tools=DUMMY_TOOLS,
        system="You are helpful.",
    )
    call_kwargs = provider.client.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are helpful."


@pytest.mark.asyncio
async def test_openai_complete_with_tools_text_response() -> None:
    provider = OpenAIProvider(api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = "Just text"
    mock_message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    provider._client = MagicMock()
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Hi"}],
        model="gpt-4o",
        tools=DUMMY_TOOLS,
    )
    assert isinstance(result, LLMResponse)
    assert result.text == "Just text"
    assert result.tool_calls == []
    assert not result.is_tool_use


@pytest.mark.asyncio
async def test_openai_complete_with_tools_tool_use() -> None:
    provider = OpenAIProvider(api_key="test-key")
    mock_tc = MagicMock()
    mock_tc.id = "call_456"
    mock_tc.function.name = "test_tool"
    mock_tc.function.arguments = '{"arg1": "hello"}'
    mock_message = MagicMock()
    mock_message.content = None
    mock_message.tool_calls = [mock_tc]
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    provider._client = MagicMock()
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Use the tool"}],
        model="gpt-4o",
        tools=DUMMY_TOOLS,
    )
    assert result.is_tool_use
    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_456"
    assert result.tool_calls[0].name == "test_tool"
    assert result.tool_calls[0].arguments == {"arg1": "hello"}


@pytest.mark.asyncio
async def test_openai_complete_with_tools_passes_system() -> None:
    provider = OpenAIProvider(api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = "ok"
    mock_message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]
    provider._client = MagicMock()
    provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

    await provider.complete_with_tools(
        messages=[{"role": "user", "content": "Hi"}],
        model="gpt-4o",
        tools=DUMMY_TOOLS,
        system="You are helpful.",
    )
    call_args = provider._client.chat.completions.create.call_args
    messages_sent = call_args[1]["messages"]
    assert messages_sent[0] == {"role": "system", "content": "You are helpful."}
