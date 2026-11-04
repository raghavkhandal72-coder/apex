"""AST Symbol, Call-Graph, Def-Use Chain & Exception Propagation extractor.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Symbol:
    name: str
    kind: str  # 'class', 'function', 'method', 'constant'
    line_number: int
    signature: str = ""
    docstring: str = ""


@dataclass
class DefUseRecord:
    variable: str
    def_line: int
    use_lines: List[int] = field(default_factory=list)


@dataclass
class ExceptionFlow:
    raised_exceptions: List[Tuple[str, int]] = field(default_factory=list)  # (exc_name, line)
    handled_exceptions: List[Tuple[str, int]] = field(default_factory=list)  # (exc_name, line)


@dataclass
class FileSymbols:
    filepath: str
    definitions: List[Symbol] = field(default_factory=list)
    references: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)
    call_graph: Dict[str, List[str]] = field(default_factory=dict)  # caller_symbol -> [callee_symbols]
    def_use_chains: List[DefUseRecord] = field(default_factory=list)
    exception_flow: ExceptionFlow = field(default_factory=ExceptionFlow)

    @property
    def defined_names(self) -> Set[str]:
        return {s.name for s in self.definitions}


class SymbolParser:
    """Extracts symbols, caller-callee relationships, def-use chains, and exception propagation."""

    @staticmethod
    def parse_python_source(source_code: str, filepath: str = "") -> FileSymbols:
        file_syms = FileSymbols(filepath=filepath)
        try:
            tree = ast.parse(source_code)
        except Exception:
            return file_syms

        current_caller: Optional[str] = None
        current_class: Optional[str] = None
        var_defs: Dict[str, DefUseRecord] = {}

        class AdvancedVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                super().__init__()

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
                nonlocal current_class
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
                prev_class = current_class
                current_class = node.name
                self.generic_visit(node)
                current_class = prev_class

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._handle_function(node, is_async=False)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._handle_function(node, is_async=True)

            def _handle_function(self, node: ast.AST, is_async: bool) -> None:
                nonlocal current_caller
                fn_node: ast.FunctionDef = node  # type: ignore[assignment]
                doc = ast.get_docstring(fn_node) or ""
                doc_summary = doc.strip().splitlines()[0] if doc else ""
                prefix = "async def " if is_async else "def "

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

                kind = "method" if current_class else "function"
                full_name = f"{current_class}.{fn_node.name}" if current_class else fn_node.name

                file_syms.definitions.append(
                    Symbol(
                        name=fn_node.name,
                        kind=kind,
                        line_number=fn_node.lineno,
                        signature=sig,
                        docstring=doc_summary,
                    )
                )

                prev_caller = current_caller
                current_caller = full_name
                if full_name not in file_syms.call_graph:
                    file_syms.call_graph[full_name] = []

                self.generic_visit(node)
                current_caller = prev_caller

            def visit_Call(self, node: ast.Call) -> None:
                callee_name = ""
                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee_name = node.func.attr

                if callee_name:
                    file_syms.references.add(callee_name)
                    if current_caller:
                        file_syms.call_graph[current_caller].append(callee_name)

                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_defs[target.id] = DefUseRecord(variable=target.id, def_line=node.lineno)
                self.generic_visit(node)

            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):
                    file_syms.references.add(node.id)
                    if node.id in var_defs:
                        var_defs[node.id].use_lines.append(getattr(node, "lineno", 0))
                self.generic_visit(node)

            def visit_Raise(self, node: ast.Raise) -> None:
                exc_name = "Exception"
                if node.exc:
                    if isinstance(node.exc, ast.Name):
                        exc_name = node.exc.id
                    elif isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                        exc_name = node.exc.func.id
                file_syms.exception_flow.raised_exceptions.append((exc_name, node.lineno))
                self.generic_visit(node)

            def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
                handled_name = "Exception"
                if node.type:
                    if isinstance(node.type, ast.Name):
                        handled_name = node.type.id
                    elif hasattr(ast, "unparse"):
                        handled_name = ast.unparse(node.type)
                file_syms.exception_flow.handled_exceptions.append((handled_name, node.lineno))
                self.generic_visit(node)

        visitor = AdvancedVisitor()
        visitor.visit(tree)
        file_syms.def_use_chains = list(var_defs.values())
        return file_syms

    @staticmethod
    def parse_generic_source(source_code: str, filepath: str = "") -> FileSymbols:
        """Heuristic regex parser for non-Python files (JS, TS, Go, Rust, Java)."""
        file_syms = FileSymbols(filepath=filepath)
        lines = source_code.splitlines()

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
