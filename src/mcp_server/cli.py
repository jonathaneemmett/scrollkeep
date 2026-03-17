from __future__ import annotations

import argparse
import asyncio
import readline
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
from mcp_server.agent.templates import list_templates, load_template

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

    # Input history
    history_path = workspace.root / "input_history"
    if history_path.exists():
        readline.read_history_file(str(history_path))
    readline.set_history_length(1000)

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
            if user_input.lower() == "/undo":
                if session.undo():
                    console.print("[dim]Last turn undone.[/dim]\n")
                else:
                    console.print("[dim]Nothing to undo.[/dim]\n")
                continue
            if user_input.lower().startswith("/export"):
                parts = user_input.split(maxsplit=1)
                md = session.export_markdown()
                if len(parts) > 1:
                    out_path = parts[1]
                    with open(out_path, "w") as f:
                        f.write(md)
                    console.print(f"[dim]Exported to {out_path}[/dim]\n")
                else:
                    console.print(Markdown(md))
                    print()
                continue
            if user_input.lower() == "/templates":
                names = list_templates(workspace.templates_dir)
                if names:
                    console.print("[bold]Templates:[/bold]")
                    for name in names:
                        console.print(f"  {name}")
                else:
                    console.print("[dim]No templates found.[/dim]")
                print()
                continue
            if user_input.lower().startswith("/template "):
                parts = user_input.split(maxsplit=1)[1].split()
                tpl_name = parts[0]
                kwargs = {}
                for part in parts[1:]:
                    if "=" in part:
                        k, _, v = part.partition("=")
                        kwargs[k] = v
                text = load_template(workspace.templates_dir, tpl_name, **kwargs)
                if text is None:
                    console.print(f"[red]Template '{tpl_name}' not found.[/red]\n")
                    continue
                user_input = text
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
        readline.write_history_file(str(history_path))
        await mcp_manager.close()


def _update() -> None:
    import shutil
    import subprocess

    console.print("[bold]Updating Scrollkeep...[/bold]")
    pipx = shutil.which("pipx")
    if pipx:
        result = subprocess.run(
            [pipx, "reinstall", "mcp-server"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            console.print("[green]Updated successfully.[/green]")
        else:
            console.print(f"[red]Update failed:[/red]\n{result.stderr}")
    else:
        console.print(
            "[red]pipx not found.[/red] "
            "Run: pip install pipx && pipx reinstall mcp-server"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrollkeep AI assistant")
    parser.add_argument(
        "command", nargs="?", default=None, help="Subcommand (e.g. update)"
    )
    parser.add_argument("--model", "-m", help="Override the default model")
    parser.add_argument("--provider", "-p", help="Override the default provider")
    parser.add_argument(
        "--new", "-n", action="store_true", help="Start a new session"
    )
    args = parser.parse_args()

    if args.command == "update":
        _update()
        return

    if args.command is not None:
        console.print(f"[red]Unknown command: {args.command}[/red]")
        sys.exit(1)

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
    from mcp_server.agent.approval import is_auto_approved
    if is_auto_approved(name, args):
        return True
    
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
        "  /new                       Start a new session\n"
        "  /undo                      Undo the last turn\n"
        "  /export [path]             Export session to markdown\n"
        "  /template <name> [k=v ...] Use a prompt template\n"
        "  /templates                 List available templates\n"
        "  /sessions                  List all sessions\n"
        "  /help                      Show this help\n"
        "  exit                       Quit\n"
    )


if __name__ == "__main__":
    main()
