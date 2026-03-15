from __future__ import annotations

from pathlib import Path

from mcp_server.agent.session import Session


def test_create_and_load(tmp_path: Path) -> None:
    session = Session.create(tmp_path / "sessions")
    assert session.path.exists() is False  # not created until first append

    session.append({"role": "user", "content": "hi"})
    assert session.path.exists()

    messages = session.load()
    assert len(messages) == 1
    assert messages[0]["content"] == "hi"


def test_append_multiple(tmp_path: Path) -> None:
    session = Session.create(tmp_path / "sessions")
    session.append({"role": "user", "content": "one"})
    session.append({"role": "assistant", "content": "two"})

    messages = session.load()
    assert len(messages) == 2
    assert messages[0]["content"] == "one"
    assert messages[1]["content"] == "two"


def test_load_empty(tmp_path: Path) -> None:
    session = Session(tmp_path / "nonexistent.jsonl")
    assert session.load() == []


def test_latest_returns_none_when_empty(tmp_path: Path) -> None:
    assert Session.latest(tmp_path / "nope") is None


def test_latest_returns_most_recent(tmp_path: Path) -> None:
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "20260101_000000.jsonl").write_text('{"role":"user","content":"old"}\n')
    (d / "20260102_000000.jsonl").write_text('{"role":"user","content":"new"}\n')

    session = Session.latest(d)
    assert session is not None
    messages = session.load()
    assert messages[0]["content"] == "new"
