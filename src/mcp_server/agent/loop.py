from __future__ import annotations

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
