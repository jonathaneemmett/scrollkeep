from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from mcp_server.agent.loop import agent_loop
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.llm.types import LLMResponse, ToolCall
from mcp_server.tools.registry import ToolRegistry


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(path=str(tmp_path / "ws"))


@pytest.fixture
def session(tmp_path: Path) -> Session:
    return Session.create(tmp_path / "sessions")


@pytest.fixture
def mock_registry() -> ToolRegistry:
    reg = ToolRegistry()

    @reg.tool("echo", "Echo back input")
    async def echo(text: str) -> str:
        return text

    return reg


@pytest.mark.asyncio
async def test_single_turn_text_response(
    workspace: Workspace, session: Session, mock_registry: ToolRegistry
) -> None:
    provider = AsyncMock()
    provider.complete_with_tools = AsyncMock(
        return_value=LLMResponse(text="Hello!")
    )

    result = await agent_loop(
        user_message="Hi",
        provider=provider,
        model="test-model",
        workspace=workspace,
        session=session,
        registry=mock_registry,
    )
    assert result == "Hello!"


@pytest.mark.asyncio
async def test_tool_round_trip(
    workspace: Workspace, session: Session, mock_registry: ToolRegistry
) -> None:
    provider = AsyncMock()
    # First call: tool use, second call: text response
    provider.complete_with_tools = AsyncMock(
        side_effect=[
            LLMResponse(
                tool_calls=[
                    ToolCall(id="c1", name="echo", arguments={"text": "ping"})
                ]
            ),
            LLMResponse(text="Got: ping"),
        ]
    )

    result = await agent_loop(
        user_message="echo ping",
        provider=provider,
        model="test-model",
        workspace=workspace,
        session=session,
        registry=mock_registry,
    )
    assert result == "Got: ping"
    assert provider.complete_with_tools.call_count == 2


@pytest.mark.asyncio
async def test_max_iterations(
    workspace: Workspace, session: Session, mock_registry: ToolRegistry
) -> None:
    provider = AsyncMock()
    # Always return tool calls, never text
    provider.complete_with_tools = AsyncMock(
        return_value=LLMResponse(
            tool_calls=[
                ToolCall(id="c1", name="echo", arguments={"text": "loop"})
            ]
        )
    )

    result = await agent_loop(
        user_message="loop forever",
        provider=provider,
        model="test-model",
        workspace=workspace,
        session=session,
        registry=mock_registry,
    )
    assert "max iterations" in result


@pytest.mark.asyncio
async def test_session_persists_messages(
    workspace: Workspace, session: Session, mock_registry: ToolRegistry
) -> None:
    provider = AsyncMock()
    provider.complete_with_tools = AsyncMock(
        return_value=LLMResponse(text="Hi there")
    )

    await agent_loop(
        user_message="Hello",
        provider=provider,
        model="test-model",
        workspace=workspace,
        session=session,
        registry=mock_registry,
    )

    messages = session.load()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
