from __future__ import annotations

from pathlib import Path


def load_template(templates_dir: Path, name: str, **kwargs: str) -> str | None:
    """Load a template by name and fill in {placeholders}."""
    path = templates_dir / f"{name}.md"
    if not path.exists():
        return None
    text = path.read_text()
    if kwargs:
        text = text.format(**kwargs)
    return text


def list_templates(templates_dir: Path) -> list[str]:
    """Return names of all available templates."""
    if not templates_dir.exists():
        return []
    return sorted(p.stem for p in templates_dir.glob("*.md"))
