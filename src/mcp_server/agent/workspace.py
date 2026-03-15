from __future__ import annotations

from pathlib import Path

DEFAULT_SOUL = """You are Scrollkeep, a personal AI assistant.
You can run shell commands, read and write files, and remember things.
Be concise and helpful.
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
            parts.append(soul.read_text())
        memory = self.root / "MEMORY.md"
        if memory.exists() and memory.read_text().strip():
            parts.append("# Memory\n" + memory.read_text())
        return "\n\n".join(parts)

    @property
    def memory_path(self) -> Path:
        return self.root / "MEMORY.md"
