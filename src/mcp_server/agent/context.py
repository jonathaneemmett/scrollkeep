from __future__ import annotations

from typing import Any


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4

def _message_tokens(msg: dict[str, Any]) -> int:
    """Estimate tokens in a single message."""
    total = 0
    content = msg.get("content", "")
    if isinstance(content, str):
        total += estimate_tokens(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                total += estimate_tokens(str(block))
    if "tool_calls" in msg:
        total += estimate_tokens(str(msg["tool_calls"]))
    return total + 4 # overhead per message

def trim_messages(
    messages: list[dict[str, Any]],
    max_tokens: int = 100_000,
    reserve: int = 8_000,
    system_prompt: str = "",
) -> list[dict[str, Any]]:
    """Trim oldest messages to fit within token budget.

    Keeps the first message (initial context) and as many recent
    messages as fit within max_tokens - reserve - system_prompt tokens.
    """
    budget = max_tokens - reserve - estimate_tokens(system_prompt)
    total = sum(_message_tokens(m) for m in messages)
    if total <= budget:
        return messages

    if len(messages) <= 2:
        return messages

    # keep first message + trim from the front of the rest
    first = messages[0]
    rest = messages[1:]
    budget -= _message_tokens(first)

    # Walk backwards, keeping recent messages
    kept: list[dict[str, Any]] = []
    used = 0
    for msg in reversed(rest):
        cost = _message_tokens(msg)
        if used + cost > budget:
            break
        kept.append(msg)
        used += cost

    kept.reverse()
    return [first] + kept
