from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools.memory import (
    delete_memory,
    list_memories,
    save_memory,
    search_memory,
    set_memory_dir,
)


@pytest.fixture(autouse=True)
def memory_dir(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    set_memory_dir(d)
    return d


@pytest.mark.asyncio
async def test_save_and_search(memory_dir: Path) -> None:
    result = await save_memory(
        title="Favorite Color", content="Blue", tags="preferences"
    )
    assert "Saved" in result
    assert (memory_dir / "favorite_color.md").exists()

    search_result = await search_memory(query="blue")
    assert "Favorite Color" in search_result


@pytest.mark.asyncio
async def test_list_memories(memory_dir: Path) -> None:
    await save_memory(title="Note One", content="First note", tags="test")
    await save_memory(title="Note Two", content="Second note", tags="test")

    result = await list_memories()
    assert "Note One" in result
    assert "Note Two" in result


@pytest.mark.asyncio
async def test_search_no_results() -> None:
    result = await search_memory(query="nonexistent")
    assert "No memories" in result


@pytest.mark.asyncio
async def test_delete_memory(memory_dir: Path) -> None:
    await save_memory(title="To Delete", content="Gone soon")
    result = await delete_memory(name="to_delete")
    assert "Deleted" in result
    assert not (memory_dir / "to_delete.md").exists()


@pytest.mark.asyncio
async def test_delete_nonexistent() -> None:
    result = await delete_memory(name="nope")
    assert "not found" in result


@pytest.mark.asyncio
async def test_list_empty() -> None:
    result = await list_memories()
    assert "No memories" in result
