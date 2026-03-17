from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from mcp_server.agent.context import trim_messages
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.llm.base import LLMProvider
from mcp_server.llm.types import LLMResponse, Usage
from mcp_server.tools.registry import ToolRegistry

log = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_ITERATIONS = 10


async def _call_with_retry(coro_fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Call an async function with exponential backoff on transient errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as e:
            err = str(e).lower()
            retryable = (
                "rate" in err
                or "overloaded" in err
                or "529" in err
                or "429" in err
            )
            if not retryable or attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** (attempt + 1)
            log.warning("Retrying in %ds: %s", wait, e)
            await asyncio.sleep(wait)
    raise RuntimeError("Unreachable")


async def agent_loop(
    user_message: str,
    provider: LLMProvider,
    model: str,
    workspace: Workspace,
    session: Session,
    registry: ToolRegistry,
    max_tokens: int = 4096,
) -> str:
    messages = session.load()
    system = workspace.system_prompt()
    tools = registry.schemas()

    messages.append({"role": "user", "content": user_message})
    session.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        messages = trim_messages(messages)
        response: LLMResponse = await _call_with_retry(
            provider.complete_with_tools,
            messages=messages,
            model=model,
            tools=tools,
            system=system,
            max_tokens=max_tokens,
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
    max_tokens: int = 4096,
) -> AsyncIterator[str | Usage]:
    messages = session.load()
    system = workspace.system_prompt()
    tools = registry.schemas()

    messages.append({"role": "user", "content": user_message})
    session.append({"role": "user", "content": user_message})

    total_usage = Usage()

    for _ in range(MAX_ITERATIONS):
        messages = trim_messages(messages)
        text_parts: list[str] = []
        final_response: LLMResponse | None = None

        for attempt in range(MAX_RETRIES):
            try:
                async for chunk in provider.stream_with_tools(
                    messages=messages,
                    model=model,
                    tools=tools,
                    system=system,
                    max_tokens=max_tokens,
                ):
                    if chunk.is_tool_use:
                        final_response = chunk
                    elif chunk.text:
                        text_parts.append(chunk.text)
                        yield chunk.text
                    if chunk.usage.input_tokens or chunk.usage.output_tokens:
                        total_usage.input_tokens += chunk.usage.input_tokens
                        total_usage.output_tokens += chunk.usage.output_tokens
                break  # success, exit retry loop
            except Exception as e:
                err = str(e).lower()
                retryable = (
                    "rate" in err
                    or "overloaded" in err
                    or "529" in err
                    or "429" in err
                )
                if not retryable or attempt == MAX_RETRIES - 1:
                    yield f"\nError: {e}"
                    return
                wait = 2 ** (attempt + 1)
                yield f"\n[retrying in {wait}s...]\n"
                await asyncio.sleep(wait)
                text_parts.clear()
                final_response = None

        if final_response is None or not final_response.is_tool_use:
            text = "".join(text_parts)
            text_msg = {"role": "assistant", "content": text}
            messages.append(text_msg)
            session.append(text_msg)
            yield total_usage
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

    yield total_usage
    yield "\nError: max iterations reached"
