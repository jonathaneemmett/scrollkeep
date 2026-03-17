from __future__ import annotations

import asyncio

from mcp_server.tools.registry import registry 

async def _run_git(*args: str) -> str:
    """Run a git command and return its output"""
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode()
    if stderr:
        output += "\n" + stderr.decode()
    return output.strip()

@registry.tool("git_status", "Show the working tree status of the current git repository")
async def git_status() -> str:
    return await _run_git("status")

@registry.tool("git_diff", "Show changes in the working tree. Pass 'staged' to see staged changes only.")
async def git_diff(target:str = "") -> str:
    args = ["diff"]
    if target == "staged":
        args.append("--cached")
    elif target:
        args.append(target)
    return await _run_git(*args)

@registry.tool("git_log", "Show recent commit history.")
async def git_log(count: int = 10) -> str:
    return await _run_git("log", "--oneline", f"-{count}")

@registry.tool("git_commit", "Stage and commit changes.")
async def git_commit(message:str, files: str = ".") -> str:
    add_result = await _run_git("add", *files.split())
    if add_result.startswith("Error"):
        return add_result
    return await _run_git("commit", "-m", message)