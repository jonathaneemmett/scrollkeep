from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools.builtins import edit_file, read_file, shell_exec, write_file
from mcp_server.tools.registry import ToolRegistry


@pytest.fixture
def fresh_registry() -> ToolRegistry:
    return ToolRegistry()


def test_schema_generation(fresh_registry: ToolRegistry) -> None:
    @fresh_registry.tool("greet", "Say hello")
    async def greet(name: str, loud: bool = False) -> str:
        return f"Hello {name}!"

    schemas = fresh_registry.schemas()
    assert len(schemas) == 1
    s = schemas[0]
    assert s["name"] == "greet"
    assert s["description"] == "Say hello"
    assert s["parameters"]["properties"]["name"]["type"] == "string"
    assert s["parameters"]["properties"]["loud"]["type"] == "boolean"
    assert s["parameters"]["required"] == ["name"]


@pytest.mark.asyncio
async def test_execute_dispatches(fresh_registry: ToolRegistry) -> None:
    @fresh_registry.tool("add", "Add numbers")
    async def add(a: int, b: int) -> str:
        return str(a + b)

    result = await fresh_registry.execute("add", {"a": 1, "b": 2})
    assert result == "3"


@pytest.mark.asyncio
async def test_execute_unknown_tool(fresh_registry: ToolRegistry) -> None:
    result = await fresh_registry.execute("nope", {})
    assert "unknown tool" in result


@pytest.mark.asyncio
async def test_execute_catches_errors(fresh_registry: ToolRegistry) -> None:
    @fresh_registry.tool("fail", "Always fails")
    async def fail() -> str:
        raise RuntimeError("boom")

    result = await fresh_registry.execute("fail", {})
    assert "boom" in result


@pytest.mark.asyncio
async def test_shell_exec() -> None:
    result = await shell_exec(command="echo hello")
    assert "hello" in result


@pytest.mark.asyncio
async def test_read_file(tmp_path: Path) -> None:
    p = tmp_path / "test.txt"
    p.write_text("contents")
    result = await read_file(path=str(p))
    assert result == "contents"


@pytest.mark.asyncio
async def test_read_file_not_found() -> None:
    result = await read_file(path="/nonexistent/file.txt")
    assert "not found" in result


@pytest.mark.asyncio
async def test_write_file(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"
    result = await write_file(path=str(p), content="hello")
    assert "Wrote" in result
    assert p.read_text() == "hello"


@pytest.mark.asyncio
async def test_edit_file(tmp_path: Path) -> None:
    p = tmp_path / "edit.txt"
    p.write_text("foo bar baz")
    result = await edit_file(
        path=str(p), old_text="bar", new_text="qux"
    )
    assert "Edited" in result
    assert p.read_text() == "foo qux baz"


@pytest.mark.asyncio
async def test_edit_file_not_found() -> None:
    result = await edit_file(
        path="/nonexistent/file.txt", old_text="a", new_text="b"
    )
    assert "not found" in result
