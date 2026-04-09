from __future__ import annotations

import abc
import logging
from typing import Any

from mcp_server.agent.loop import agent_loop_streaming
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.config import get_settings
from mcp_server.llm import get_provider
from mcp_server.llm.types import Usage
from mcp_server.tools import registry
from mcp_server.tools.delegate import configure_delegate
from mcp_server.tools.mcp_client import MCPClientManager
from mcp_server.tools.skills import load_skills

log = logging.getLogger(__name__)


class Channel(abc.ABC):
    """Base class for messaging channel integrations."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.provider = get_provider()
        self.model = self.settings.default_model
        self.workspace = Workspace(path=self.settings.workspace_dir)
        self._sessions: dict[str, Session] = {}
        self._mcp_manager = MCPClientManager()

    async def setup(self) -> None:
        """Configure delegate, load skills, connect MCP servers."""
        configure_delegate(
            self.provider,
            self.model,
            self.workspace,
            registry,
            max_tokens=self.settings.max_tokens,
        )
        loaded = load_skills(self.workspace.skills_dir)
        if loaded:
            log.info("Loaded skills: %s", ", ".join(loaded))

        mcp_config = self.workspace.root / "mcp_servers.json"
        try:
            await self._mcp_manager.connect_from_config(
                mcp_config, registry
            )
        except Exception as e:
            log.warning("MCP connection error: %s", e)

    def _get_session(self, chat_id: str) -> Session:
        """Get or create a session for the given chat ID."""

        if chat_id not in self._sessions:
            sessions_dir = self.workspace.root / "sessions" / f"{self.name}_{chat_id}"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            self._sessions[chat_id] = (
                Session.latest(sessions_dir) or Session.create(sessions_dir)
            )
        return self._sessions[chat_id]

    async def handle_message(self, chat_id: str, text: str) -> str:
        """Run the agent loop for an incoming message. Returns the full response."""
        session = self._get_session(chat_id)
        chunks: list[str] = []

        async for chunk in agent_loop_streaming(
            user_message=text,
            provider=self.provider,
            model=self.model,
            workspace=self.workspace,
            session=session,
            registry=registry,
            confirm=self._confirm_tool,
        ):
            if isinstance(chunk, Usage):
                continue
            if chunk.startswith("\n[tool:"):
                continue  # skip tool markers in channel output
            chunks.append(chunk)

        return "".join(chunks).strip() or "(no response)"

    async def _confirm_tool(self, name: str, args: dict[str, Any]) -> bool:
        """Auto-approve safe tools, deny dangerous ones."""
        from mcp_server.agent.approval import is_auto_approved
        return is_auto_approved(name, args)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Channel identifier, e.g. 'telegram', 'discord'."""
        ...

    @abc.abstractmethod
    async def start(self) -> None:
        """Begin listening for messages."""
        ...

    @abc.abstractmethod
    async def stop(self) -> None:
        """Graceful shutdown."""
        ...