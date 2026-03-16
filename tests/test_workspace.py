from __future__ import annotations

from pathlib import Path

from mcp_server.agent.workspace import Workspace


def test_creates_default_files(tmp_path: Path) -> None:
    ws = Workspace(path=str(tmp_path / "ws"))
    assert (ws.root / "SOUL.md").exists()
    assert ws.memory_dir.exists()


def test_does_not_overwrite_existing(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "SOUL.md").write_text("custom soul")
    ws = Workspace(path=str(root))
    assert (ws.root / "SOUL.md").read_text() == "custom soul"


def test_system_prompt_includes_soul(tmp_path: Path) -> None:
    ws = Workspace(path=str(tmp_path / "ws"))
    prompt = ws.system_prompt()
    assert "Scrollkeep" in prompt


def test_system_prompt_includes_memories(tmp_path: Path) -> None:
    ws = Workspace(path=str(tmp_path / "ws"))
    mem = ws.memory_dir / "test.md"
    mem.write_text(
        "---\ntitle: favorite color\ntags: prefs\n"
        "date: 2026-01-01\n---\n\nblue"
    )
    prompt = ws.system_prompt()
    assert "favorite color" in prompt
    assert "blue" in prompt


def test_system_prompt_skips_empty_memory(tmp_path: Path) -> None:
    ws = Workspace(path=str(tmp_path / "ws"))
    prompt = ws.system_prompt()
    assert "# Remembered Notes" not in prompt


def test_memory_dir(tmp_path: Path) -> None:
    ws = Workspace(path=str(tmp_path / "ws"))
    assert ws.memory_dir == ws.root / "memory"
    assert ws.memory_dir.is_dir()
