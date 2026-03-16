from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp_server.agent.loop import agent_loop_streaming
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

    print("Scrollkeep ready, Type /help for commands.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user_input:
            continue

        # CLI Commands
        if user_input.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        if user_input.lower() == "/new":
            session = Session.create(sessions_dir)
            print(f"Started new session: {session.path.stem}\n")
            continue
        if user_input.lower() == "/sessions":
            _list_sessions(sessions_dir)
            continue
        if user_input.lower() == "/help":
            _print_help()
            continue

        async for chunk in agent_loop_streaming(
            user_message=user_input,
            provider=provider,
            model=settings.default_model,
            workspace=workspace,
            session=session,
            registry=registry,
            confirm=_confirm_tool,
        ):
            print(chunk, end="", flush=True)
        print("\n")

def main() -> None:
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        print("\nBye!")
        sys.exit(0)

async def _confirm_tool(name: str, args: dict[str, Any]) -> bool:
    summary = f"  {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"
    print(summary)
    try:
        answer = input("  Allow? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("", "y", "yes")


def _list_sessions(sessions_dir: object) -> None:
    from pathlib import Path

    d = Path(str(sessions_dir))
    if not d.exists():
        print("No sessions found.")
        return
    files = sorted(d.glob("*.jsonl"))
    if not files:
        print("No sessions found.")
        return
    for f in files:
        lines = sum(1 for _ in f.read_text().splitlines() if _.strip())
        print(f"{f.stem}: ({lines} messages)")
    print()

def _print_help() -> None:
    print(
        "\nCommands:\n"
        "/new - Start a new session\n"
        "/sessions - List all sessions\n"
        "/help - Show this help message\n"
        "exit, quit - Exit the CLI\n"
    )

if __name__ == "__main__":
    main()
