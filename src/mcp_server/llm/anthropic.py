from typing import Any

import anthropic
from anthropic.types import MessageParam, TextBlock, ToolUseBlock

from mcp_server.llm.types import LLMResponse, ToolCall, ToolSchema


class AnthropicProvider:
    def __init__(self, api_key: str) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
    ) -> str:
        response = await self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[MessageParam(**m) for m in messages],  # type: ignore[typeddict-item]
        )
        block = response.content[0]
        assert isinstance(block, TextBlock)
        return block.text

    async def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[ToolSchema],
        system: str = "",
    ) -> LLMResponse:
        anthropic_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in tools
        ]

        anthropic_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "tools": anthropic_tools,
        }
        if system:
            kwargs["system"] = system

        response = await self.client.messages.create(**kwargs)  # type: ignore[arg-type]

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return LLMResponse(
            text="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
        )

    @staticmethod
    def _convert_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert normalized messages to Anthropic format."""
        result: list[dict[str, Any]] = []
        for msg in messages:
            role = msg["role"]
            if role == "tool_result":
                result.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"],
                        }
                    ],
                })
            elif role == "assistant" and "tool_calls" in msg:
                content: list[dict[str, Any]] = []
                if msg.get("text"):
                    content.append({"type": "text", "text": msg["text"]})
                for tc in msg["tool_calls"]:
                    content.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"],
                    })
                result.append({"role": "assistant", "content": content})
            else:
                result.append({"role": role, "content": msg["content"]})
        return result  