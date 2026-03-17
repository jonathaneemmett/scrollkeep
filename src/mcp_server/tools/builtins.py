from __future__ import annotations

import asyncio
import base64
import mimetypes

from mcp_server.tools.registry import registry


@registry.tool("read_image", "read an image file and return it as a base64-encoded data.")
async def read_image(path:str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return f"Error: file '{path}' not found"
    mime, _ = mimetypes.guess_type(path)
    if mime not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        return f"Error: unsupported image type"
    encoded = base64.b64encode(data).decode("ascii")
    return f"image:{mime}:{encoded}"


@registry.tool("shell_exec", "Execute a shell command and return the output.")
async def shell_exec(command: str, timeout: int = 30) -> str:
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return "Error: command timed out"
    output = stdout.decode()
    if stderr: 
        output += "\n" + stderr.decode()
    return output.strip()

@registry.tool("read_file", "Read the contents of a file.")
async def read_file(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: file '{path}' not found"

@registry.tool("write_file", "Write content to a file.")
async def write_file(path: str, content: str) -> str: 
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} characters to '{path}'"

@registry.tool("edit_file", "Replace text in a file")
async def edit_file(path: str, old_text: str, new_text: str) -> str:
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    if old_text not in text:
        return "Error: old_text not found in file"
    text = text.replace(old_text, new_text, 1)
    with open(path, "w") as f:
        f.write(text)
    return f"Edited {path}"   