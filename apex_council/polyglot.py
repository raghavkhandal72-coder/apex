from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, Tuple


class Language(str, Enum):
    PYTHON = "Python"
    TYPESCRIPT = "TypeScript"
    JAVASCRIPT = "JavaScript"
    GO = "Go"
    RUST = "Rust"
    SHELL = "Shell/Bash"
    SQL = "SQL"
    UNKNOWN = "General"


EXT_TO_LANG: Dict[str, Language] = {
    ".py": Language.PYTHON,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".cjs": Language.JAVASCRIPT,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".sh": Language.SHELL,
    ".bash": Language.SHELL,
    ".sql": Language.SQL,
}


def detect_language(file_path: Path | str) -> Language:
    """Detects programming language from file extension."""
    suffix = Path(file_path).suffix.lower()
    return EXT_TO_LANG.get(suffix, Language.UNKNOWN)


def get_language_prompt_guidelines(lang: Language) -> str:
    """Returns idiomatic production guidelines for the detected language."""
    guidelines = {
        Language.PYTHON: "Adhere to PEP 8, strict type hints, and exception safety.",
        Language.TYPESCRIPT: "Adhere to strict TypeScript mode, no 'any', Zod input schemas, and async/await.",
        Language.JAVASCRIPT: "Use modern ES2024+ syntax, strict equality, and explicit error handling.",
        Language.GO: "Use idiomatic Go conventions, explicit error returns (no panics), and goroutine safe channels.",
        Language.RUST: "Ensure memory safety, exhaustive pattern matching with Result/Option, and clean lifetimes.",
        Language.SHELL: "Use 'set -euo pipefail', quote all variables, and avoid eval.",
        Language.SQL: "Ensure parameterized queries, indexed joins, and defense against SQL injection.",
        Language.UNKNOWN: "Write clean, modular, and defensive production code.",
    }
    return guidelines.get(lang, guidelines[Language.UNKNOWN])
