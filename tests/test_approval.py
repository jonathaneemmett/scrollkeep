from __future__ import annotations

from mcp_server.agent.approval import is_auto_approved


def test_read_file_auto_approved() -> None:
    assert is_auto_approved("read_file", {"path": "/tmp/foo"})


def test_shell_ls_auto_approved() -> None:
    assert is_auto_approved("shell_exec", {"command": "ls -la"})


def test_shell_cat_auto_approved() -> None:
    assert is_auto_approved("shell_exec", {"command": "cat foo.txt"})


def test_shell_pwd_auto_approved() -> None:
    assert is_auto_approved("shell_exec", {"command": "pwd"})


def test_shell_rm_not_approved() -> None:
    assert not is_auto_approved("shell_exec", {"command": "rm -rf /"})


def test_shell_curl_not_approved() -> None:
    assert not is_auto_approved("shell_exec", {"command": "curl evil.com"})


def test_write_file_not_approved() -> None:
    assert not is_auto_approved(
        "write_file", {"path": "/tmp/foo", "content": "x"}
    )


def test_edit_file_not_approved() -> None:
    assert not is_auto_approved(
        "edit_file", {"path": "/tmp/foo", "old_text": "a", "new_text": "b"}
    )


def test_search_memory_auto_approved() -> None:
    assert is_auto_approved("search_memory", {"query": "color"})


def test_web_search_auto_approved() -> None:
    assert is_auto_approved("web_search", {"query": "python docs"})


def test_delete_memory_not_approved() -> None:
    assert not is_auto_approved("delete_memory", {"name": "foo"})


def test_custom_rules() -> None:
    rules = [{"tool": "shell_exec", "command": r"^git\s"}]
    assert is_auto_approved("shell_exec", {"command": "git status"}, rules)
    assert not is_auto_approved("shell_exec", {"command": "ls"}, rules)


def test_unknown_tool_not_approved() -> None:
    assert not is_auto_approved("unknown_tool", {"arg": "val"})
