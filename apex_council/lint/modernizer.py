"""
Apex Modernizer: Zero-dependency Python 3.10+ / 3.12+ AST and token codemod.
Upgrades legacy typing (Union, Optional, List, Dict) to native PEP 604 unions (A | B)
and PEP 585 generics (list[T], dict[K, V]) with zero external dependencies.
"""

from __future__ import annotations

import ast
import difflib
import os
import re
from typing import Any, Dict, List, Tuple


# Regex patterns for safe lexical transformations
RE_TYPING_UNION = re.compile(r"\bUnion\s*\[\s*([^\[\]]+?)\s*\]")
RE_TYPING_OPTIONAL = re.compile(r"\bOptional\s*\[\s*([^\[\]]+?)\s*\]")
RE_TYPING_LIST = re.compile(r"\bList\s*\[")
RE_TYPING_DICT = re.compile(r"\bDict\s*\[")
RE_TYPING_SET = re.compile(r"\bSet\s*\[")
RE_TYPING_TUPLE = re.compile(r"\bTuple\s*\[")


def modernize_code(source: str) -> Tuple[str, List[str]]:
    """Transform Python source code to modern Python 3.10+ syntax.
    
    Returns (modernized_source, applied_changes)
    """
    changes: List[str] = []
    lines = source.splitlines(keepends=True)
    new_code = source

    # 1. Transform Optional[T] -> T | None
    def replace_optional(match: re.Match[str]) -> str:
        inner = match.group(1).strip()
        changes.append(f"Optional[{inner}] -> {inner} | None")
        return f"{inner} | None"

    prev = new_code
    new_code = RE_TYPING_OPTIONAL.sub(replace_optional, new_code)

    # 2. Transform Union[A, B] -> A | B (iterative for nested unions)
    def replace_union(match: re.Match[str]) -> str:
        inner = match.group(1)
        # Split args respecting commas
        args = [arg.strip() for arg in inner.split(",") if arg.strip()]
        new_expr = " | ".join(args)
        changes.append(f"Union[{inner}] -> {new_expr}")
        return new_expr

    while True:
        subbed = RE_TYPING_UNION.sub(replace_union, new_code)
        if subbed == new_code:
            break
        new_code = subbed

    # 3. Transform List -> list, Dict -> dict, Set -> set, Tuple -> tuple
    if RE_TYPING_LIST.search(new_code):
        new_code = RE_TYPING_LIST.sub("list[", new_code)
        changes.append("List[T] -> list[T]")

    if RE_TYPING_DICT.search(new_code):
        new_code = RE_TYPING_DICT.sub("dict[", new_code)
        changes.append("Dict[K, V] -> dict[K, V]")

    if RE_TYPING_SET.search(new_code):
        new_code = RE_TYPING_SET.sub("set[", new_code)
        changes.append("Set[T] -> set[T]")

    if RE_TYPING_TUPLE.search(new_code):
        new_code = RE_TYPING_TUPLE.sub("tuple[", new_code)
        changes.append("Tuple[T] -> tuple[T]")

    # 4. Clean unused typing imports if modified
    if changes:
        new_code = _cleanup_unused_typing_imports(new_code)

    # Validate that modernized code is valid Python AST
    try:
        ast.parse(new_code)
    except SyntaxError:
        # If transformation produced invalid syntax, revert safely
        return source, []

    return new_code, changes


def _cleanup_unused_typing_imports(source: str) -> str:
    """Remove modernized symbols from 'from typing import ...' lines if no longer present."""
    modernized_symbols = {"Union", "Optional", "List", "Dict", "Set", "Tuple"}
    lines = source.splitlines(keepends=True)
    out_lines: List[str] = []

    for line in lines:
        if line.strip().startswith("from typing import"):
            # Extract symbols
            prefix, _, symbols_part = line.partition("from typing import")
            symbols = [s.strip() for s in symbols_part.split(",") if s.strip()]
            remaining: List[str] = []
            for s in symbols:
                # Check if symbol still appears in the rest of source outside import
                pattern = rf"\b{re.escape(s)}\b"
                # Count occurrences in source
                count = len(re.findall(pattern, source))
                # If only present once (which is this import line), omit it
                if count > 1 or s not in modernized_symbols:
                    remaining.append(s)

            if remaining:
                out_lines.append(f"{prefix}from typing import {', '.join(remaining)}\n")
            else:
                # Omit empty import line entirely
                pass
        else:
            out_lines.append(line)

    return "".join(out_lines)


def modernize_file(filepath: str, write: bool = False) -> Dict[str, Any]:
    """Scan and modernize a file. If write=True, creates .bak and writes changes."""
    abs_path = os.path.abspath(filepath)
    if not os.path.exists(abs_path):
        return {"file": filepath, "success": False, "error": "File not found"}

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            original = f.read()
    except Exception as e:
        return {"file": filepath, "success": False, "error": str(e)}

    updated, changes = modernize_code(original)

    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
        )
    )
    diff_text = "".join(diff_lines)

    if write and changes:
        bak_file = f"{abs_path}.bak"
        with open(bak_file, "w", encoding="utf-8") as bf:
            bf.write(original)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(updated)

    return {
        "file": filepath,
        "success": True,
        "changed": bool(changes),
        "changes": changes,
        "diff": diff_text,
        "written": write and bool(changes),
    }
