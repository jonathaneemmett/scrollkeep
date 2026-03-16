from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.types import LLMResponse
from mcp_server.tools.registry import ToolRegistry

MAX_ITERATIONS = 10


async def agent_loop(
    user_message: str,
    provider: LLMProvider,
    model: str,
    workspace: Workspace,
    session: Session,
    registry: ToolRegistry,
) -> str:
    messages = session.load()
    system = workspace.system_prompt()
    tools = registry.schemas()

    messages.append({"role": "user", "content": user_message})
    session.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        response: LLMResponse = await provider.complete_with_tools(
            messages=messages,
            model=model,
            tools=tools,
            system=system,
        )

        if not response.is_tool_use:
            text = response.text or ""
            text_msg = {"role": "assistant", "content": text}
            messages.append(text_msg)
            session.append(text_msg)
            return text

        # Build assistant message with tool calls
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": response.text or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in response.tool_calls
            ],
        }
        messages.append(assistant_msg)
        session.append(assistant_msg)

        # Execute each tool call and append results
        for tc in response.tool_calls:
            result = await registry.execute(tc.name, tc.arguments)
            tool_msg: dict[str, Any] = {
                "role": "tool_result",
                "tool_call_id": tc.id,
                "content": result,
            }
            messages.append(tool_msg)
            session.append(tool_msg)

    return "Error: max iterations reached"


ConfirmFn = Callable[[str, dict[str, Any]], Awaitable[bool]]


async def agent_loop_streaming(
    user_message: str,
    provider: LLMProvider,
    model: str,
    workspace: Workspace,
    session: Session,
    registry: ToolRegistry,
    confirm: ConfirmFn | None = None,
) -> AsyncIterator[str]:
    messages = session.load()
    system = workspace.system_prompt()
    tools = registry.schemas()

    messages.append({"role": "user", "content": user_message})
    session.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        text_parts: list[str] = []
        final_response: LLMResponse | None = None

        async for chunk in provider.stream_with_tools(
            messages=messages,
            model=model,
            tools=tools,
            system=system,
        ):
            if chunk.is_tool_use:
                final_response = chunk
            elif chunk.text:
                text_parts.append(chunk.text)
                yield chunk.text

        if final_response is None or not final_response.is_tool_use:
            text = "".join(text_parts)
            text_msg = {"role": "assistant", "content": text}
            messages.append(text_msg)
            session.append(text_msg)
            return

        # Tool use turn
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": final_response.text or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in final_response.tool_calls
            ],
        }
        messages.append(assistant_msg)
        session.append(assistant_msg)

        for tc in final_response.tool_calls:
            yield f"\n[tool: {tc.name}]\n"
            if confirm and not await confirm(tc.name, tc.arguments):
                result = "Tool execution declined by user."
            else:
                result = await registry.execute(tc.name, tc.arguments)
            tool_msg: dict[str, Any] = {
                "role": "tool_result",
                "tool_call_id": tc.id,
                "content": result,
            }
            messages.append(tool_msg)
            session.append(tool_msg)

    yield "\nError: max iterations reached"