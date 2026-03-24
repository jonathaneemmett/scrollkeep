from __future__ import annotations

from pathlib import Path

from mcp_server.tools.memory import set_memory_dir

DEFAULT_SOUL = """\
You are Scrollkeep, a personal AI assistant running locally on the user's machine.
Be concise and helpful.

## Tools
You have these tools available:
- shell_exec: Run shell commands
- read_file: Read file contents
- write_file: Write content to a file
- edit_file: Replace text in a file
- save_memory: Save a memory with title, content, and tags
- search_memory: Search memories by keyword
- list_memories: List all saved memories
- delete_memory: Delete a memory by name
- web_search: Search the web using DuckDuckGo
- web_fetch: Fetch and read a URL
- delegate: Delegate a subtask to a sub-agent

## Memory
You have a structured memory system. When the user asks you to remember something, \
use save_memory with a descriptive title and relevant tags. When they ask you to \
recall something, use search_memory or list_memories. Your saved memories are \
summarized below in the system prompt automatically.
"""


class Workspace:
    def __init__(self, path: str = "~/.scrollkeep") -> None:
        self.root = Path(path).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()
        set_memory_dir(self.memory_dir)

    def _ensure_defaults(self) -> None:
        soul = self.root / "SOUL.md"
        if not soul.exists():
            soul.write_text(DEFAULT_SOUL)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)

    def system_prompt(self) -> str:
        parts: list[str] = []
        soul = self.root / "SOUL.md"
        if soul.exists():
            parts.append(soul.read_text())
        # Include memory summaries
        memory_summary = self._memory_summary()
        if memory_summary:
            parts.append("# Remembered Notes\n" + memory_summary)
        return "\n\n".join(parts)

    def _memory_summary(self) -> str:
        if not self.memory_dir.exists():
            return ""
        files = sorted(self.memory_dir.glob("*.md"))
        if not files:
            return ""
        lines: list[str] = []
        for path in files:
            text = path.read_text()
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    meta: dict[str, str] = {}
                    for line in parts[1].strip().splitlines():
                        if ":" in line:
                            key, _, value = line.partition(":")
                            meta[key.strip()] = value.strip()
                    title = meta.get("title", path.stem)
                    body = parts[2].strip()[:200]
                    lines.append(f"- **{title}**: {body}")
            else:
                lines.append(f"- {path.stem}: {text[:200]}")
        return "\n".join(lines)

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def memory_path(self) -> Path:
        """Kept for backwards compat."""
        return self.memory_dir
    
    @property
    def credentials_dir(self) -> Path:
        return self.root / "credentials"
