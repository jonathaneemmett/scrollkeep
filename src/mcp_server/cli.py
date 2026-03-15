from __future__ import annotations

import asyncio
import sys

from mcp_server.agent.loop import agent_loop
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.config import get_settings
from mcp_server.llm import get_provider
from mcp_server.tools import registry


async def repl() -> None:
    settings = get_settings()
    provider = get_provider()
    workspace = Workspace(path=settings.workspace_dir)
    sessions_dir = workspace.root / "sessions"

    session = Session.latest(sessions_dir) or Session.create(sessions_dir)

    print("Scrollkeep ready, Type 'exit' or 'quit' to leave.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Bye!")
            break

        response = await agent_loop(
            user_message=user_input,
            provider=provider,
            model=settings.default_model,
            workspace=workspace,
            session=session,
            registry=registry,
        )
        print(f"agent> {response}\n")

def main() -> None:
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        print("\nBye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
