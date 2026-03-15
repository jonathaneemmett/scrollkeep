from __future__ import annotations

from pathlib import Path

DEFAULT_SOUL = """\
You are Scrollkeep, a personal AI assistant running locally on the user's machine.
Be concise and helpful.

## Tools
You have these tools available:
- shell_exec: Run shell commands
- read_file: Read file contents
- write_file: Write content to a file
- edit_file: Replace text in a file

## Memory
You have persistent memory stored at {memory_path}.
When the user asks you to remember something, use the edit_file or write_file tool \
to append it to your memory file. When they ask you to recall something, read that file.
Your memory file contents are included in your system prompt automatically, \
so you can see what you've previously remembered.
"""


class Workspace:
    def __init__(self, path: str = "~/.scrollkeep") -> None:
        self.root = Path(path).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        soul = self.root / "SOUL.md"
        if not soul.exists():
            soul.write_text(DEFAULT_SOUL)
        memory = self.root / "MEMORY.md"
        if not memory.exists():
            memory.write_text("")

    def system_prompt(self) -> str:
        parts: list[str] = []
        soul = self.root / "SOUL.md"
        if soul.exists():
            parts.append(
                soul.read_text().replace("{memory_path}", str(self.memory_path))
            )
        memory = self.root / "MEMORY.md"
        if memory.exists() and memory.read_text().strip():
            parts.append("# Remembered Notes\n" + memory.read_text())
        return "\n\n".join(parts)

    @property
    def memory_path(self) -> Path:
        return self.root / "MEMORY.md"
