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
