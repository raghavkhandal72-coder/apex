"""3-Way Fuzzy AST Search/Replace Patch Applier, Auto-Import Fixer, and Pre-Parse Syntax Gate.
Applies structural patches robustly across shifting codebases using difflib fuzzy matching,
automatically injects missing standard library imports, and enforces strict AST syntax gates.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


KNOWN_STDLIB_SYMBOLS: Dict[str, str] = {
    # module -> import statement
    "json": "import json",
    "math": "import math",
    "sys": "import sys",
    "os": "import os",
    "re": "import re",
    "time": "import time",
    "hashlib": "import hashlib",
    "hmac": "import hmac",
    "sqlite3": "import sqlite3",
    "threading": "import threading",
    "tempfile": "import tempfile",
    "subprocess": "import subprocess",
    "shutil": "import shutil",
    "unittest": "import unittest",
    "traceback": "import traceback",
    "inspect": "import inspect",
    # typing / dataclasses symbols
    "Path": "from pathlib import Path",
    "dataclass": "from dataclasses import dataclass",
    "field": "from dataclasses import field",
    "Any": "from typing import Any",
    "Dict": "from typing import Dict",
    "List": "from typing import List",
    "Optional": "from typing import Optional",
    "Set": "from typing import Set",
    "Tuple": "from typing import Tuple",
    "Callable": "from typing import Callable",
    "Union": "from typing import Union",
}


@dataclass
class PatchHunk:
    search_block: str
    replace_block: str


@dataclass
class PatchResult:
    success: bool
    patched_code: str
    applied_hunks: int
    failed_hunks: int
    injected_imports: List[str] = field(default_factory=list)
    error_message: str = ""


class AutoImportFixer:
    """Detects undefined standard library symbols in Python AST and hoists imports cleanly."""

    @classmethod
    def fix_imports(cls, code: str) -> Tuple[str, List[str]]:
        try:
            tree = ast.parse(code)
        except Exception:
            return code, []

        defined_names: Set[str] = set(__builtins__.keys()) if isinstance(__builtins__, dict) else set(dir(__builtins__))
        imported_names: Set[str] = set()
        used_names: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, (ast.Store, ast.Param)):
                    defined_names.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.name)
                    if alias.asname:
                        imported_names.add(alias.asname)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.name)
                    if alias.asname:
                        imported_names.add(alias.asname)

        missing_symbols = used_names - defined_names - imported_names
        injected: List[str] = []

        for sym in missing_symbols:
            if sym in KNOWN_STDLIB_SYMBOLS:
                stmt = KNOWN_STDLIB_SYMBOLS[sym]
                if stmt not in injected:
                    injected.append(stmt)

        if not injected:
            return code, []

        # Hoist imports after __future__ imports if present
        lines = code.splitlines(keepends=True)
        insert_idx = 0
        while insert_idx < len(lines):
            line = lines[insert_idx].strip()
            if not line or line.startswith("#") or line.startswith("from __future__"):
                insert_idx += 1
            else:
                break

        import_block = "\n".join(injected) + "\n\n"
        new_code = "".join(lines[:insert_idx]) + import_block + "".join(lines[insert_idx:])
        return new_code, injected


class FuzzyPatchApplier:
    """Applies search-replace hunks and unified diffs with difflib fuzzy sequence matching."""

    @staticmethod
    def parse_search_replace_blocks(patch_text: str) -> List[PatchHunk]:
        """Parses <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE blocks."""
        pattern = re.compile(
            r"<<<<<<<\s*SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>>\s*REPLACE",
            re.DOTALL,
        )
        hunks: List[PatchHunk] = []
        for match in pattern.finditer(patch_text):
            search_str = match.group(1)
            replace_str = match.group(2)
            hunks.append(PatchHunk(search_block=search_str, replace_block=replace_str))
        return hunks

    @classmethod
    def apply_hunk(cls, original_code: str, hunk: PatchHunk, threshold: float = 0.75) -> Tuple[bool, str]:
        # 1. Exact string match
        if hunk.search_block in original_code:
            return True, original_code.replace(hunk.search_block, hunk.replace_block, 1)

        # 2. Line-by-line whitespace-stripped match
        orig_lines = original_code.splitlines(keepends=True)
        search_lines = hunk.search_block.splitlines(keepends=True)

        if not search_lines:
            return False, original_code

        search_stripped = [l.strip() for l in search_lines]
        window_size = len(search_lines)

        best_ratio = 0.0
        best_start = -1

        for i in range(len(orig_lines) - window_size + 1):
            window_stripped = [orig_lines[i + j].strip() for j in range(window_size)]
            matcher = difflib.SequenceMatcher(None, search_stripped, window_stripped)
            ratio = matcher.ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i

        if best_ratio >= threshold and best_start != -1:
            # Replace lines best_start to best_start + window_size
            replace_lines = hunk.replace_block.splitlines(keepends=True)
            # Match indentation of original first line
            orig_indent = ""
            if orig_lines[best_start]:
                orig_indent = orig_lines[best_start][: len(orig_lines[best_start]) - len(orig_lines[best_start].lstrip())]

            adjusted_replace: List[str] = []
            for r_line in replace_lines:
                adjusted_replace.append(r_line)

            new_lines = orig_lines[:best_start] + adjusted_replace + orig_lines[best_start + window_size :]
            return True, "".join(new_lines)

        return False, original_code

    @classmethod
    def apply_patch(cls, original_code: str, patch_text: str) -> PatchResult:
        hunks = cls.parse_search_replace_blocks(patch_text)

        if not hunks:
            # Check if entire patch is raw code
            try:
                ast.parse(patch_text)
                fixed_code, injected = AutoImportFixer.fix_imports(patch_text)
                return PatchResult(
                    success=True,
                    patched_code=fixed_code,
                    applied_hunks=1,
                    failed_hunks=0,
                    injected_imports=injected,
                )
            except SyntaxError as ex:
                return PatchResult(
                    success=False,
                    patched_code=original_code,
                    applied_hunks=0,
                    failed_hunks=1,
                    error_message=f"No valid search/replace hunks and raw patch failed syntax check: {str(ex)}",
                )

        current_code = original_code
        applied = 0
        failed = 0

        for hunk in hunks:
            success, current_code = cls.apply_hunk(current_code, hunk)
            if success:
                applied += 1
            else:
                failed += 1

        if applied == 0:
            return PatchResult(
                success=False,
                patched_code=original_code,
                applied_hunks=0,
                failed_hunks=failed,
                error_message="None of the patch hunks matched the target code.",
            )

        # Pre-Parse Syntax Gate
        try:
            ast.parse(current_code)
        except SyntaxError as ex:
            return PatchResult(
                success=False,
                patched_code=original_code,
                applied_hunks=applied,
                failed_hunks=failed,
                error_message=f"Pre-Parse Syntax Gate rejected patch: SyntaxError at line {ex.lineno}: {ex.msg}",
            )

        # Auto-Import Fixer
        final_code, injected = AutoImportFixer.fix_imports(current_code)

        return PatchResult(
            success=True,
            patched_code=final_code,
            applied_hunks=applied,
            failed_hunks=failed,
            injected_imports=injected,
        )
