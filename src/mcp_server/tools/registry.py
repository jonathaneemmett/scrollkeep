from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

from mcp_server.llm.types import ToolSchema

# Python type → JSON Schema type
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}
        self._schemas: dict[str, ToolSchema] = {}

    def tool(
        self, name: str, description: str
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = fn
            self._schemas[name] = _build_schema(name, description, fn)
            return fn

        return decorator

    def schemas(self) -> list[ToolSchema]:
        return list(self._schemas.values())

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        if name not in self._tools:
            return f"Error: unknown tool '{name}'"
        fn = self._tools[name]
        try:
            result = fn(**args)
            if inspect.isawaitable(result):
                result = await result
            return str(result)
        except Exception as e:
            return f"Error: {e}"


def _build_schema(
    name: str, description: str, fn: Callable[..., Any]
) -> ToolSchema:
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        param_type = hints.get(param_name, str)
        json_type = _TYPE_MAP.get(param_type, "string")
        properties[param_name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return ToolSchema(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
        },
    )


registry = ToolRegistry()
