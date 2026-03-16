import json
from collections.abc import AsyncIterator
from typing import Any

import openai

from mcp_server.llm.types import LLMResponse, ToolCall, ToolSchema


class OpenAIProvider:
    def __init__(self, api_key: str) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self, messages: list[dict[str, str]], model: str = "gpt-4o"
    ) -> str:
        response = await self._client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
        )
        content = response.choices[0].message.content
        if content is None:
            return ""
        return content

    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

        openai_messages = self._convert_messages(messages, system)

        response = await self._client.chat.completions.create(
            model=model,
            messages=openai_messages,  # type: ignore[arg-type]
            tools=openai_tools,  # type: ignore[arg-type]
        )

        choice = response.choices[0].message

        text = choice.content
        tool_calls: list[ToolCall] = []

        if choice.tool_calls:
            for tc in choice.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,  # type: ignore[union-attr]
                        arguments=json.loads(tc.function.arguments),  # type: ignore[union-attr]
                    )
                )

        return LLMResponse(text=text, tool_calls=tool_calls)

    async def stream_with_tools(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[ToolSchema],
        system: str = "",
    ) -> AsyncIterator[LLMResponse]:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tools
        ]

        openai_messages = self._convert_messages(messages, system)

        stream = await self._client.chat.completions.create(
            model=model,
            messages=openai_messages,  # type: ignore[arg-type]
            tools=openai_tools,  # type: ignore[arg-type]
            stream=True,
        )

        text_parts: list[str] = []
        tool_calls_by_index: dict[int, dict[str, Any]] = {}

        async for chunk in stream:  # type: ignore[union-attr]
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            if delta.content:
                text_parts.append(delta.content)
                yield LLMResponse(text=delta.content)

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_calls_by_index:
                        tool_calls_by_index[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    entry = tool_calls_by_index[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["arguments"] += tc_delta.function.arguments

        if tool_calls_by_index:
            tool_calls = [
                ToolCall(
                    id=entry["id"],
                    name=entry["name"],
                    arguments=json.loads(entry["arguments"] or "{}"),
                )
                for entry in tool_calls_by_index.values()
            ]
            yield LLMResponse(
                text="\n".join(text_parts) if text_parts else None,
                tool_calls=tool_calls,
            )

    @staticmethod
    def _convert_messages(
        messages: list[dict[str, Any]], system: str
    ) -> list[dict[str, Any]]:
        """Convert normalized messages to OpenAI format."""
        result: list[dict[str, Any]] = []
        if system:
            result.append({"role": "system", "content": system})

        for msg in messages:
            role = msg["role"]
            if role == "tool_result":
                result.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": msg["content"],
                })
            elif role == "assistant" and "tool_calls" in msg:
                openai_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.get("text"),
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in msg["tool_calls"]
                    ],
                }
                result.append(openai_msg)
            else:
                result.append({"role": role, "content": msg["content"]})
        return result
