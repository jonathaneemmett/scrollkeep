from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

from mcp_server.agent.loop import agent_loop_streaming
from mcp_server.llm.types import Usage
from mcp_server.agent.session import Session
from mcp_server.agent.workspace import Workspace
from mcp_server.config import get_settings
from mcp_server.llm import get_provider
from mcp_server.tools import registry
from mcp_server.tools.delegate import configure_delegate
from mcp_server.tools.mcp_client import MCPClientManager
from mcp_server.tools.skills import load_skills
from mcp_server.agent.templates import list_templates, load_template
from importlib.metadata import version

console = Console()

# Cost per 1M tokens: (input, output)
COST_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-opus-4-20250514": (15.0, 75.0),
    "claude-haiku-3-20250307": (0.25, 1.25),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "o3-mini": (1.10, 4.40),
}


def _format_usage(usage: Usage, model: str) -> str:
    total_tokens = usage.input_tokens + usage.output_tokens
    parts = [f"{total_tokens:,} tokens (in: {usage.input_tokens:,}, out: {usage.output_tokens:,})"]
    cost_rates = COST_PER_MILLION.get(model)
    if cost_rates:
        cost = (usage.input_tokens * cost_rates[0] + usage.output_tokens * cost_rates[1]) / 1_000_000
        parts.append(f"~${cost:.4f}")
    return " | ".join(parts)


def _format_tool_summary(name: str, args: dict[str, Any]) -> str:
    path = args.get("path") or args.get("file_path") or ""
    content = args.get("content") or args.get("new_string") or ""

    if name in ("write_file", "create_file"):
        detail = f"to {path}" if path else ""
        if content:
            detail += f" ({len(content):,} chars)"
        return f"Write {detail}".strip()

    if name in ("edit_file", "edit"):
        old = args.get("old_string", "")
        detail = f"in {path}" if path else ""
        if old:
            detail += f" ({len(old):,} → {len(content):,} chars)"
        return f"Edit {detail}".strip()

    if name in ("read_file",):
        detail = f"from {path}" if path else ""
        offset = args.get("offset")
        limit = args.get("limit")
        if offset and limit:
            detail = f"lines {offset}-{offset + limit - 1} of {path}"
        return f"Read {detail}".strip()

    if name in ("shell_exec", "shell"):
        cmd = args.get("command", "")
        if len(cmd) > 80:
            cmd = cmd[:77] + "…"
        return f"Shell: {cmd}"

    if name in ("web_search",):
        return f'Search for "{args.get("query", "")}"'

    if name in ("web_fetch",):
        return f'Fetch {args.get("url", "")}'

    if name in ("delegate",):
        task = args.get("task", "")
        if len(task) > 80:
            task = task[:77] + "…"
        return f"Delegate: {task}"

    # Fallback: tool name + short arg summary
    parts = []
    for k, v in args.items():
        sv = str(v)
        if len(sv) > 60:
            sv = sv[:57] + "…"
        parts.append(f"{k}={sv}")
    detail = ", ".join(parts)
    return f"{name}({detail})" if detail else name


async def repl(
    model: str | None = None,
    provider_name: str | None = None,
    new_session: bool = False,
    max_tokens: int | None = None,
) -> None:
    settings = get_settings()
    provider = get_provider(provider_name)
    active_model = model or settings.default_model
    active_max_tokens = max_tokens or settings.max_tokens
    workspace = Workspace(path=settings.workspace_dir)
    sessions_dir = workspace.root / "sessions"

    if new_session:
        session = Session.create(sessions_dir)
    else:
        session = Session.latest(sessions_dir) or Session.create(sessions_dir)

    # Configure delegate tool
    configure_delegate(provider, active_model, workspace, registry, max_tokens=active_max_tokens)

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
    command_completer = WordCompleter(["/new", "/clear", "/undo", "/export", "/sessions", "/templates", "/template", "/help", "exit", "quit"], sentence=True)
    prompt_session = PromptSession(history=FileHistory(str(history_path)), completer=command_completer)

    console.print("[bold]Scrollkeep ready.[/bold] Type /help for commands.\n")

    try:
        while True:
            try:
                user_input = (await prompt_session.prompt_async(HTML("<b><ansibrightcyan>&gt;</ansibrightcyan></b> "))).strip()
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
            if user_input.lower() == "/clear":
                session = Session.create(sessions_dir)
                print("\033[2J\033[H", end="", flush=True)
                console.print("[bold]Scrollkeep ready.[/bold] Type /help for commands.\n")
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

            active_spinner: list[Status | None] = [None]
            spinner_running: list[bool] = [False]

            async def _confirm_tool(name: str, args: dict[str, Any]) -> bool:
                from mcp_server.agent.approval import is_auto_approved
                if is_auto_approved(name, args):
                    return True

                if active_spinner[0] and spinner_running[0]:
                    active_spinner[0].stop()
                    spinner_running[0] = False

                console.print(f"  [bold]{_format_tool_summary(name, args)}[/bold]")
                try:
                    answer = (await prompt_session.prompt_async(HTML("  Allow? [Y/n] "))).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    return False
                finally:
                    if active_spinner[0]:
                        active_spinner[0].start()
                        spinner_running[0] = True
                return answer in ("", "y", "yes")

            buffer: list[str] = []
            turn_usage: Usage | None = None
            spinner = Status("Thinking…", console=console, spinner="dots")
            active_spinner[0] = spinner
            spinner.start()
            spinner_running[0] = True

            async for chunk in agent_loop_streaming(
                user_message=user_input,
                provider=provider,
                model=active_model,
                workspace=workspace,
                session=session,
                registry=registry,
                confirm=_confirm_tool,
            ):
                if isinstance(chunk, Usage):
                    turn_usage = chunk
                    continue
                if chunk.startswith("\n[tool:"):
                    spinner.stop()
                    spinner_running[0] = False
                    if buffer:
                        console.print(Markdown("".join(buffer)))
                        buffer.clear()
                    console.print(f"[yellow]{chunk.strip()}[/yellow]")
                    spinner = Status(f"{chunk.strip().strip('[]')} running…", console=console, spinner="dots")
                    active_spinner[0] = spinner
                    spinner.start()
                    spinner_running[0] = True
                else:
                    buffer.append(chunk)

            spinner.stop()
            spinner_running[0] = False
            active_spinner[0] = None
            if buffer:
                console.print(Markdown("".join(buffer)))
            if turn_usage and (turn_usage.input_tokens or turn_usage.output_tokens):
                console.print(f"[dim]{_format_usage(turn_usage, active_model)}[/dim]")
            print()
    finally:
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
    parser.add_argument("--version", "-V", action="version", version=f"scrollkeep {version('mcp-server')}")
    parser.add_argument(
        "command", nargs="?", default=None, help="Subcommand (e.g. update)"
    )
    parser.add_argument("--model", "-m", help="Override the default model")
    parser.add_argument("--provider", "-p", help="Override the default provider")
    parser.add_argument(
        "--new", "-n", action="store_true", help="Start a new session"
    )
    parser.add_argument("--max-tokens", type=int, help="Max response tokens")

    args = parser.parse_args()

    if args.command == "update":
        _update()
        return

    if args.command == "gmail-auth":
        from mcp_server.tools.gmail import run_oath_flow
        asyncio.run(run_oath_flow())
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
        "  /clear                     Clear screen and context\n"
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
