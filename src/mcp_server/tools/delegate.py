from __future__ import annotations

from mcp_server.tools.registry import registry

# These get set by the CLI at startup
_provider: object | None = None
_model: str = ""
_workspace: object | None = None
_sub_registry: object | None = None


def configure_delegate(
    provider: object, model: str, workspace: object, sub_registry: object
) -> None:
    global _provider, _model, _workspace, _sub_registry  # noqa: PLW0603
    _provider = provider
    _model = model
    _workspace = workspace
    _sub_registry = sub_registry


@registry.tool(
    "delegate",
    "Delegate a subtask to a sub-agent. The sub-agent has access to "
    "all the same tools but runs independently with its own context. "
    "Use this for complex multi-step tasks you want to break down.",
)
async def delegate(task: str) -> str:
    if _provider is None or _workspace is None or _sub_registry is None:
        return "Error: delegate not configured"

    # Create a temporary in-memory session for the sub-agent
    import tempfile
    from pathlib import Path

    from mcp_server.agent.loop import agent_loop
    from mcp_server.agent.session import Session

    tmp = Path(tempfile.mkdtemp())
    session = Session.create(tmp)

    result = await agent_loop(
        user_message=task,
        provider=_provider,  # type: ignore[arg-type]
        model=_model,
        workspace=_workspace,  # type: ignore[arg-type]
        session=session,
        registry=_sub_registry,  # type: ignore[arg-type]
    )

    # Clean up temp session
    try:
        if session.path.exists():
            session.path.unlink()
        tmp.rmdir()
    except OSError:
        pass

    return result
