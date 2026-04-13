from __future__ import annotations

import re
from typing import Any

# Tool calls matching these patterns are auto-approved.
# For shell_exec, the pattern must match the full command and disallows
# shell metacharacters that enable injection (|, ;, &, $, `, <, >, newline).
_SAFE_ARGS = r"(\s+[^|;&`$(><\n]+)?"
DEFAULT_RULES = [
    {"tool": "read_file"},
    {"tool": "list_memories"},
    {"tool": "search_memory"},
    {"tool": "web_search"},
    {"tool": "web_fetch"},
    {"tool": "shell_exec", "command":
        rf"^(ls|cat|head|tail|wc|echo|pwd|whoami|date|which|env|printenv){_SAFE_ARGS}$"},
]

def is_auto_approved(
    name: str,
    args: dict[str, Any],
    rules: list[dict[str, str]] | None = None,
) -> bool:
    if rules is None:
        rules = DEFAULT_RULES
    for rule in rules:
        if rule.get("tool") != name:
            continue
        # If rule only specifies tool name, it's a blanket approve
        arg_patterns = {k: v for k, v in rule.items() if k != "tool"}
        if not arg_patterns:
            return True
        # Check each arg pattern
        if all(
            re.search(pattern, str(args.get(key, "")))
            for key, pattern in arg_patterns.items()
        ):
            return True
    return False
