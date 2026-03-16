from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from mcp_server.agent.loop import agent_loop_streaming
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.config import get_settings
from mcp_server.llm import get_provider
from mcp_server.tools import registry
from mcp_server.tools.delegate import configure_delegate
from mcp_server.tools.mcp_client import MCPClientManager
from mcp_server.tools.skills import load_skills

console = Console()


async def repl(
    model: str | None = None,
    provider_name: str | None = None,
    new_session: bool = False,
) -> None:
    settings = get_settings()
    provider = get_provider(provider_name)
    active_model = model or settings.default_model
    workspace = Workspace(path=settings.workspace_dir)
    sessions_dir = workspace.root / "sessions"

    if new_session:
        session = Session.create(sessions_dir)
    else:
        session = Session.latest(sessions_dir) or Session.create(sessions_dir)

    # Configure delegate tool
    configure_delegate(provider, active_model, workspace, registry)

    # Load user skills
    loaded = load_skills(workspace.skills_dir)
    if loaded:
        console.print(f"[dim]Loaded skills: {', '.join(loaded)}[/dim]")

    # Connect to external MCP servers
    mcp_manager = MCPClientManager()
    mcp_config = workspace.root / "mcp_servers.json"
    try:
        await mcp_manager.connect_from_config(mcp_config, registry)
    except Exception as e:
        console.print(f"[red]Warning: MCP connection error: {e}[/red]")

    console.print("[bold]Scrollkeep ready.[/bold] Type /help for commands.\n")

    try:
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
                console.print(
                    f"Started new session: [dim]{session.path.stem}[/dim]\n"
                )
                continue
            if user_input.lower() == "/sessions":
                _list_sessions(sessions_dir)
                continue
            if user_input.lower() == "/help":
                _print_help()
                continue

            buffer: list[str] = []
            async for chunk in agent_loop_streaming(
                user_message=user_input,
                provider=provider,
                model=active_model,
                workspace=workspace,
                session=session,
                registry=registry,
                confirm=_confirm_tool,
            ):
                if chunk.startswith("\n[tool:"):
                    if buffer:
                        console.print(Markdown("".join(buffer)))
                        buffer.clear()
                    console.print(f"[yellow]{chunk.strip()}[/yellow]")
                else:
                    buffer.append(chunk)

            if buffer:
                console.print(Markdown("".join(buffer)))
            print()
    finally:
        await mcp_manager.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrollkeep AI assistant")
    parser.add_argument("--model", "-m", help="Override the default model")
    parser.add_argument("--provider", "-p", help="Override the default provider")
    parser.add_argument(
        "--new", "-n", action="store_true", help="Start a new session"
    )
    args = parser.parse_args()

    try:
        asyncio.run(
            repl(
                model=args.model,
                provider_name=args.provider,
                new_session=args.new,
            )
        )
    except KeyboardInterrupt:
        print("\nBye!")
        sys.exit(0)


async def _confirm_tool(name: str, args: dict[str, Any]) -> bool:
    summary = f"  {name}({', '.join(f'{k}={v!r}' for k, v in args.items())})"
    console.print(f"[dim]{summary}[/dim]")
    try:
        answer = input("  Allow? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("", "y", "yes")


def _list_sessions(sessions_dir: object) -> None:
    from pathlib import Path

    d = Path(str(sessions_dir))
    if not d.exists():
        console.print("[dim]No sessions found.[/dim]")
        return
    files = sorted(d.glob("*.jsonl"))
    if not files:
        console.print("[dim]No sessions found.[/dim]")
        return
    console.print("[bold]Sessions:[/bold]")
    for f in files:
        lines = sum(1 for _ in f.read_text().splitlines() if _.strip())
        console.print(f"  [dim]{f.stem}[/dim]  ({lines} messages)")
    print()


def _print_help() -> None:
    console.print(
        "\n[bold]Commands:[/bold]\n"
        "  /new       Start a new session\n"
        "  /sessions  List all sessions\n"
        "  /help      Show this help\n"
        "  exit       Quit\n"
    )


if __name__ == "__main__":
    main()
