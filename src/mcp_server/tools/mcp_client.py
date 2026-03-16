from __future__ import annotations

import json
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_server.llm.types import ToolSchema
from mcp_server.tools.registry import ToolRegistry


class MCPClientManager:
    """Connects to external MCP servers and registers their tools."""

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()

    async def connect_from_config(
        self, config_path: Path, registry: ToolRegistry
    ) -> None:
        if not config_path.exists():
            return
        config = json.loads(config_path.read_text())
        for name, server_def in config.items():
            await self._connect_server(name, server_def, registry)

    async def _connect_server(
        self, name: str, server_def: dict[str, Any], registry: ToolRegistry
    ) -> None:
        params = StdioServerParameters(
            command=server_def["command"],
            args=server_def.get("args", []),
            env=server_def.get("env"),
        )
        transport = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        read_stream, write_stream = transport
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()
        self._sessions[name] = session

        # Fetch tools and register them
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            tool_name = f"{name}__{tool.name}"
            schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}

            # Register a proxy function for this tool
            async def _proxy(
                _session: ClientSession = session,
                _tool_name: str = tool.name,
                **kwargs: Any,
            ) -> str:
                result = await _session.call_tool(_tool_name, kwargs)
                parts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        parts.append(content.text)
                    else:
                        parts.append(str(content))
                return "\n".join(parts)

            registry._tools[tool_name] = _proxy
            registry._schemas[tool_name] = ToolSchema(
                name=tool_name,
                description=tool.description or f"MCP tool: {tool.name}",
                parameters=schema,
            )

    async def close(self) -> None:
        await self._exit_stack.aclose()
