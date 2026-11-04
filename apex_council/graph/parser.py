"""AST and heuristic symbol parser for Python and multi-language repositories.
Extracts definitions, references, and import relationships without external dependencies.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class Symbol:
    name: str
    kind: str  # 'class', 'function', 'method', 'constant'
    line_number: int
    signature: str = ""
    docstring: str = ""


@dataclass
class FileSymbols:
    filepath: str
    definitions: List[Symbol] = field(default_factory=list)
    references: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)

    @property
    def defined_names(self) -> Set[str]:
        return {s.name for s in self.definitions}


class SymbolParser:
    """Parses code files to discover definitions and cross-file references."""

    @staticmethod
    def parse_python_source(source_code: str, filepath: str = "") -> FileSymbols:
        """Extracts classes, functions, signatures, docstrings, imports, and references using AST."""
        file_syms = FileSymbols(filepath=filepath)
        try:
            tree = ast.parse(source_code)
        except Exception:
            return file_syms

        class DefinitionVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.current_class: Optional[str] = None

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    file_syms.imports.add(alias.name)
                    file_syms.references.add(alias.asname or alias.name)
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                module = node.module or ""
                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    file_syms.imports.add(full_name)
                    file_syms.references.add(alias.asname or alias.name)
                self.generic_visit(node)

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                doc = ast.get_docstring(node) or ""
                doc_summary = doc.strip().splitlines()[0] if doc else ""
                bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
                sig = f"class {node.name}({', '.join(bases)}):" if bases else f"class {node.name}:"
                
                file_syms.definitions.append(
                    Symbol(
                        name=node.name,
                        kind="class",
                        line_number=node.lineno,
                        signature=sig,
                        docstring=doc_summary,
                    )
                )
                prev_class = self.current_class
                self.current_class = node.name
                self.generic_visit(node)
                self.current_class = prev_class

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._handle_func(node, is_async=False)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._handle_func(node, is_async=True)

            def _handle_func(self, node: ast.AST, is_async: bool) -> None:
                fn_node = node  # type: ignore[assignment]
                doc = ast.get_docstring(fn_node) or ""
                doc_summary = doc.strip().splitlines()[0] if doc else ""
                prefix = "async def " if is_async else "def "
                
                # Format arguments
                args_list = []
                for a in fn_node.args.args:
                    arg_str = a.arg
                    if a.annotation and hasattr(ast, "unparse"):
                        arg_str += f": {ast.unparse(a.annotation)}"
                    args_list.append(arg_str)
                ret_str = ""
                if fn_node.returns and hasattr(ast, "unparse"):
                    ret_str = f" -> {ast.unparse(fn_node.returns)}"
                sig = f"{prefix}{fn_node.name}({', '.join(args_list)}){ret_str}"

                kind = "method" if self.current_class else "function"
                file_syms.definitions.append(
                    Symbol(
                        name=fn_node.name,
                        kind=kind,
                        line_number=fn_node.lineno,
                        signature=sig,
                        docstring=doc_summary,
                    )
                )
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    file_syms.references.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute) -> None:
                file_syms.references.add(node.attr)
                self.generic_visit(node)

        visitor = DefinitionVisitor()
        visitor.visit(tree)
        return file_syms

    @staticmethod
    def parse_generic_source(source_code: str, filepath: str = "") -> FileSymbols:
        """Heuristic regex parser for non-Python files (JS, TS, Go, Rust, Java)."""
        file_syms = FileSymbols(filepath=filepath)
        lines = source_code.splitlines()

        # Regex patterns
        class_pattern = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:class|struct|interface|type)\s+([A-Za-z0-9_]+)")
        func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|def|fn|func)\s+([A-Za-z0-9_]+)\s*\(")
        import_pattern = re.compile(r"""(?:import|require|from)\s+['"]([^'"]+)['"]""")

        for line_num, line in enumerate(lines, start=1):
            c_match = class_pattern.match(line)
            if c_match:
                name = c_match.group(1)
                file_syms.definitions.append(Symbol(name=name, kind="class", line_number=line_num, signature=line.strip()))
                continue

            f_match = func_pattern.match(line)
            if f_match:
                name = f_match.group(1)
                file_syms.definitions.append(Symbol(name=name, kind="function", line_number=line_num, signature=line.strip()))
                continue

            for imp in import_pattern.findall(line):
                file_syms.imports.add(imp)

            # Collect identifier references
            words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", line)
            for w in words:
                file_syms.references.add(w)

        return file_syms

    @classmethod
    def parse_file(cls, path: Path | str) -> FileSymbols:
        p = Path(path)
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return FileSymbols(filepath=str(p))

        if p.suffix == ".py":
            return cls.parse_python_source(content, filepath=str(p))
        else:
            return cls.parse_generic_source(content, filepath=str(p))
