from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_skills(skills_dir: Path) -> list[str]:
    """Load all .py files from the skills directory.

    Each skill file should import and use `registry` to register tools:
        from mcp_server.tools.registry import registry

        @registry.tool("my_tool", "Does something cool")
        async def my_tool(arg: str) -> str:
            return f"Result: {arg}"

    Returns a list of loaded skill names.
    """
    if not skills_dir.exists():
        return []

    loaded: list[str] = []
    for path in sorted(skills_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = f"scrollkeep_skill_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            loaded.append(path.stem)
        except Exception as e:
            # Don't crash the whole app for a bad skill
            loaded.append(f"{path.stem} (ERROR: {e})")

    return loaded
