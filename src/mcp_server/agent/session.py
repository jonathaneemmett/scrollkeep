from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class Session:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        messages: list[dict[str, Any]] = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                messages.append(json.loads(line))
        return messages

    def append(self, message: dict[str, Any]) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(message) + "\n")

    def undo(self) -> bool:
        """Remove the last user turn and all assistant/tool messages that followed it."""
        messages = self.load()
        if not messages:
            return False
        # Walk backwards to find the last user message
        last_user = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "user":
                last_user = i
                break
        if last_user == -1:
            return False
        # Keep everything before that user message
        messages = messages[:last_user]
        # Rewrite the file
        with open(self.path, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")
        return True

    def export_markdown(self) -> str:
        """Export the conversation as readable markdown."""
        messages = self.load()
        if not messages:
            return "*Empty session.*"
        lines: list[str] = []
        for msg in messages:
            role = msg["role"]
            if role == "user":
                lines.append(f"## You\n\n{msg['content']}\n")
            elif role == "assistant":
                text = msg.get("text") or msg.get("content") or ""
                if text:
                    lines.append(f"## Assistant\n\n{text}\n")
                if "tool_calls" in msg:
                    for tc in msg["tool_calls"]:
                        args = json.dumps(tc["arguments"], indent=2)
                        lines.append(f"**Tool call:** `{tc['name']}`\n```json\n{args}\n```\n")
            elif role == "tool_result":
                content = msg["content"]
                if content.startswith("image:"):
                    lines.append("*[image]*\n")
                else:
                    preview = content[:500]
                    if len(content) > 500:
                        preview += "..."
                    lines.append(f"**Result:**\n```\n{preview}\n```\n")
        return "\n".join(lines)

    @classmethod
    def create(cls, directory: Path) -> Session:
        directory.mkdir(parents=True, exist_ok=True)
        name = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S.jsonl")
        return cls(directory / name)

    @classmethod
    def latest(cls, directory: Path) -> Session | None:
        if not directory.exists():
            return None
        files = sorted(directory.glob("*.jsonl"))
        if not files:
            return None
        return cls(files[-1])
