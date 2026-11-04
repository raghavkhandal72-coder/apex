from __future__ import annotations

from pathlib import Path
from typing import Optional


CONTEXT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
]


def load_project_context(root_dir: Path | str = ".") -> Optional[str]:
    """Scans for agent rule files (AGENTS.md, CLAUDE.md, .cursorrules)

    and extracts repository conventions to ground the Council.
    """
    root = Path(root_dir).resolve()

    found_rules = []
    for filename in CONTEXT_FILES:
        target = root / filename
        if target.exists() and target.is_file():
            try:
                content = target.read_text(encoding="utf-8", errors="ignore").strip()
                if content:
                    found_rules.append(f"### Guidelines from {filename}:\n{content[:1500]}")
            except Exception:
                pass

    if not found_rules:
        return None

    return (
        "Repository Architecture & Codebase Guidelines:\n"
        + "\n\n".join(found_rules)
        + "\n\nEnsure all code submissions strictly adhere to the above conventions."
    )
