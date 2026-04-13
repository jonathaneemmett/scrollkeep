from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from mcp_server.tools.registry import registry

# Set by workspace at startup
_memory_dir: Path | None = None


def set_memory_dir(path: Path) -> None:
    global _memory_dir  # noqa: PLW0603
    _memory_dir = path
    path.mkdir(parents=True, exist_ok=True)


def _get_memory_dir() -> Path:
    if _memory_dir is None:
        raise RuntimeError("Memory directory not configured")
    return _memory_dir


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s_]+", "_", slug).strip("_")[:60]


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML-like frontmatter from a memory file."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


@registry.tool(
    "save_memory",
    "Save a memory with a title, content, and optional tags. "
    "Use this when the user asks you to remember something.",
)
async def save_memory(title: str, content: str, tags: str = "") -> str:
    d = _get_memory_dir()
    slug = _slugify(title)
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Find a filename that doesn't collide with a different title
    filename = f"{slug}.md"
    path = d / filename
    counter = 1
    while path.exists():
        existing = path.read_text()
        meta, _ = _parse_frontmatter(existing)
        if meta.get("title") == title:
            break  # same title — intentional overwrite/update
        filename = f"{slug}_{counter}.md"
        path = d / filename
        counter += 1

    frontmatter = f"---\ntitle: {title}\ntags: {tags}\ndate: {timestamp}\n---\n\n"
    path.write_text(frontmatter + content)
    return f"Saved memory: {title} ({filename})"


@registry.tool(
    "search_memory",
    "Search memories by keyword. Searches titles, tags, and content.",
)
async def search_memory(query: str) -> str:
    d = _get_memory_dir()
    if not d.exists():
        return "No memories found."
    results: list[str] = []
    query_lower = query.lower()
    for path in sorted(d.glob("*.md")):
        text = path.read_text()
        if query_lower in text.lower():
            meta, body = _parse_frontmatter(text)
            title = meta.get("title", path.stem)
            tags = meta.get("tags", "")
            preview = body[:100].replace("\n", " ")
            entry = f"- **{title}**"
            if tags:
                entry += f" [{tags}]"
            entry += f": {preview}"
            results.append(entry)
    if not results:
        return f"No memories matching '{query}'."
    return "\n".join(results)


@registry.tool("list_memories", "List all saved memories.")
async def list_memories() -> str:
    d = _get_memory_dir()
    if not d.exists():
        return "No memories found."
    files = sorted(d.glob("*.md"))
    if not files:
        return "No memories found."
    results: list[str] = []
    for path in files:
        text = path.read_text()
        meta, _ = _parse_frontmatter(text)
        title = meta.get("title", path.stem)
        tags = meta.get("tags", "")
        date = meta.get("date", "")
        entry = f"- **{title}**"
        if tags:
            entry += f" [{tags}]"
        if date:
            entry += f" ({date[:10]})"
        results.append(entry)
    return "\n".join(results)


@registry.tool(
    "delete_memory", "Delete a memory by its filename (without .md extension)."
)
async def delete_memory(name: str) -> str:
    d = _get_memory_dir()
    path = d / f"{name}.md"
    if not path.exists():
        return f"Memory not found: {name}"
    path.unlink()
    return f"Deleted memory: {name}"
