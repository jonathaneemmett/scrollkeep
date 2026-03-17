from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


class ToolSchema(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    @property
    def is_tool_use(self) -> bool:
        return len(self.tool_calls) > 0

@dataclass
class ToolResult:
    tool_call_id: str
    content: str
