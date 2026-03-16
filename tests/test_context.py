from __future__ import annotations

from mcp_server.agent.context import estimate_tokens, trim_messages


def test_estimate_tokens() -> None:
    assert estimate_tokens("hello world") > 0
    assert estimate_tokens("a" * 400) == 100


def test_trim_no_op_when_under_budget() -> None:
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    result = trim_messages(messages, max_tokens=100_000)
    assert result == messages


def test_trim_drops_old_messages() -> None:
    messages = [
        {"role": "user", "content": "first"},
    ]
    for i in range(50):
        messages.append({
            "role": "assistant",
            "content": "x" * 10_000,
        })
    messages.append({"role": "user", "content": "latest"})

    result = trim_messages(messages, max_tokens=10_000, reserve=1_000)
    assert result[0]["content"] == "first"
    assert result[-1]["content"] == "latest"
    assert len(result) < len(messages)


def test_trim_preserves_recent() -> None:
    messages = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "x" * 40_000},
        {"role": "user", "content": "middle"},
        {"role": "assistant", "content": "short"},
        {"role": "user", "content": "recent"},
    ]
    result = trim_messages(messages, max_tokens=5_000, reserve=1_000)
    assert result[-1]["content"] == "recent"


def test_trim_keeps_first_message() -> None:
    messages = [
        {"role": "user", "content": "important first"},
        {"role": "assistant", "content": "x" * 40_000},
        {"role": "user", "content": "recent"},
    ]
    result = trim_messages(messages, max_tokens=5_000, reserve=1_000)
    assert result[0]["content"] == "important first"


def test_trim_small_list_unchanged() -> None:
    messages = [
        {"role": "user", "content": "x" * 100_000},
        {"role": "assistant", "content": "x" * 100_000},
    ]
    result = trim_messages(messages, max_tokens=1_000, reserve=100)
    assert len(result) == 2  # too few to trim
