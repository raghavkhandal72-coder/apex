#!/usr/bin/env python3
"""
Apex-Sovereign: Surgical AST Symbol Navigator
Inspired by AutoCodeRover (ICSE 2024)
100% Pure Python Standard Library | Zero Dependencies

Provides precise programmatic code navigation across classes, methods, functions,
parameters, docstrings, and call hierarchies directly via Python's AST parser.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import pathlib
from typing import Dict, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class SymbolMetadata:
    name: str
    kind: str  # "class", "function", "method", "async_function"
    file_path: str
    lineno: int
    end_lineno: int
    docstring: Optional[str]
    parameters: List[str]
    parent_class: Optional[str]
    source_code: str


@dataclasses.dataclass(frozen=True)
class CallHierarchy:
    symbol: str
    callees: List[str]
    callers: List[str]


class ASTSymbolNavigator:
    """
    Indexes and navigates Python source files programmatically using standard `ast`.
    Enables sub-millisecond retrieval of symbol definitions, bodies, and call edges.
    """

    def __init__(self, root_dir: Optional[str | pathlib.Path] = None) -> None:
        self.root_dir = pathlib.Path(root_dir).resolve() if root_dir else None
        self._symbols: Dict[str, List[SymbolMetadata]] = {}  # key: symbol_name
        self._file_symbols: Dict[str, List[SymbolMetadata]] = {}  # key: normalized file path
        self._file_lines: Dict[str, List[str]] = {}
        self._call_graph: Dict[str, Set[str]] = {}  # caller -> set of callees

        if self.root_dir and self.root_dir.exists():
            self.index_directory(self.root_dir)

    def index_source(self, file_path: str, source_code: str) -> List[SymbolMetadata]:
        """Indexes symbols within a single source code string."""
        norm_path = os.path.normpath(file_path).replace("\\", "/")
        lines = source_code.splitlines(keepends=True)
        self._file_lines[norm_path] = lines

        try:
            tree = ast.parse(source_code, filename=norm_path)
        except SyntaxError:
            return []

        entries: List[SymbolMetadata] = []
        self._traverse_node(tree, norm_path, lines, None, entries)

        self._file_symbols[norm_path] = entries
        for sym in entries:
            self._symbols.setdefault(sym.name, []).append(sym)
            if sym.parent_class:
                qualified = f"{sym.parent_class}.{sym.name}"
                self._symbols.setdefault(qualified, []).append(sym)

        return entries

    def index_file(self, file_path: str | pathlib.Path) -> List[SymbolMetadata]:
        """Reads and indexes a single Python file from disk."""
        p = pathlib.Path(file_path).resolve()
        if not p.exists() or p.suffix != ".py":
            return []
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
            return self.index_source(str(p), code)
        except OSError:
            return []

    def index_directory(self, root_dir: str | pathlib.Path, max_files: int = 500) -> int:
        """Recursively indexes all Python files under a directory."""
        root = pathlib.Path(root_dir).resolve()
        count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune hidden and virtual environment directories
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".") and d not in {"venv", ".venv", "site-packages", "__pycache__", "build", "dist"}
            ]
            for f in filenames:
                if f.endswith(".py"):
                    full_p = os.path.join(dirpath, f)
                    self.index_file(full_p)
                    count += 1
                    if count >= max_files:
                        return count
        return count

    def _traverse_node(
        self,
        node: ast.AST,
        file_path: str,
        lines: List[str],
        parent_class: Optional[str],
        out_entries: List[SymbolMetadata],
    ) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                doc = ast.get_docstring(child)
                src = self._extract_slice(lines, child.lineno, child.end_lineno or child.lineno)
                meta = SymbolMetadata(
                    name=child.name,
                    kind="class",
                    file_path=file_path,
                    lineno=child.lineno,
                    end_lineno=child.end_lineno or child.lineno,
                    docstring=doc,
                    parameters=[],
                    parent_class=parent_class,
                    source_code=src,
                )
                out_entries.append(meta)
                # Recurse into class body
                self._traverse_node(child, file_path, lines, child.name, out_entries)

            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "method" if parent_class else ("async_function" if isinstance(child, ast.AsyncFunctionDef) else "function")
                doc = ast.get_docstring(child)
                params = [arg.arg for arg in child.args.args]
                src = self._extract_slice(lines, child.lineno, child.end_lineno or child.lineno)
                meta = SymbolMetadata(
                    name=child.name,
                    kind=kind,
                    file_path=file_path,
                    lineno=child.lineno,
                    end_lineno=child.end_lineno or child.lineno,
                    docstring=doc,
                    parameters=params,
                    parent_class=parent_class,
                    source_code=src,
                )
                out_entries.append(meta)

                # Record callees inside this function
                caller_key = f"{parent_class}.{child.name}" if parent_class else child.name
                callees = self._extract_callees(child)
                self._call_graph[caller_key] = callees

                # Nested functions
                self._traverse_node(child, file_path, lines, parent_class, out_entries)

    def _extract_slice(self, lines: List[str], start_line: int, end_line: int) -> str:
        """Extracts 1-indexed line range safely."""
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        return "".join(lines[start_idx:end_idx])

    def _extract_callees(self, func_node: ast.AST) -> Set[str]:
        callees: Set[str] = set()
        for sub in ast.walk(func_node):
            if isinstance(sub, ast.Call):
                if isinstance(sub.func, ast.Name):
                    callees.add(sub.func.id)
                elif isinstance(sub.func, ast.Attribute):
                    callees.add(sub.func.attr)
        return callees

    def search_class(self, class_name: str) -> List[SymbolMetadata]:
        """Finds all class definitions matching class_name."""
        matches = self._symbols.get(class_name, [])
        return [m for m in matches if m.kind == "class"]

    def search_method(self, method_name: str, class_name: Optional[str] = None) -> List[SymbolMetadata]:
        """Finds methods by name, optionally filtered by parent class."""
        if class_name:
            qualified = f"{class_name}.{method_name}"
            return self._symbols.get(qualified, [])
        matches = self._symbols.get(method_name, [])
        return [m for m in matches if m.kind == "method"]

    def search_function(self, func_name: str) -> List[SymbolMetadata]:
        """Finds top-level functions matching func_name."""
        matches = self._symbols.get(func_name, [])
        return [m for m in matches if m.kind in {"function", "async_function"}]

    def get_symbol_source(self, symbol_name: str) -> Optional[str]:
        """Returns the source code of the first matching symbol."""
        entries = self._symbols.get(symbol_name)
        if entries:
            return entries[0].source_code
        return None

    def get_call_hierarchy(self, symbol_name: str) -> CallHierarchy:
        """Computes callers and callees for a given symbol."""
        callees = sorted(list(self._call_graph.get(symbol_name, set())))
        callers: List[str] = []
        for caller, called_set in self._call_graph.items():
            if symbol_name in called_set or any(symbol_name == c for c in called_set):
                callers.append(caller)
        return CallHierarchy(symbol=symbol_name, callees=callees, callers=sorted(callers))

    def get_surrounding_context(self, file_path: str, target_line: int, window: int = 5) -> str:
        """Retrieves lines surrounding a target line in a given file."""
        norm_path = os.path.normpath(file_path).replace("\\", "/")
        lines = self._file_lines.get(norm_path)
        if not lines:
            # Try to read directly
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                self._file_lines[norm_path] = lines
            except OSError:
                return f"[Error: Cannot read {file_path}]"

        start_idx = max(0, target_line - 1 - window)
        end_idx = min(len(lines), target_line + window)

        numbered_lines = []
        for i in range(start_idx, end_idx):
            prefix = "-> " if (i + 1) == target_line else "   "
            numbered_lines.append(f"{prefix}{i + 1:4d} | {lines[i]}")
        return "".join(numbered_lines)
