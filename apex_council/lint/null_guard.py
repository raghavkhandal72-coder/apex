"""
Apex Kotlin-Style Null/None Safety Prover (stdlib ast only).
Detects and auto-remediates Tony Hoare's "Billion Dollar Mistake" in Python:
AttributeError: 'NoneType' object has no attribute '...'
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set, Tuple


@dataclass(frozen=True)
class NullSafetyViolation:
    variable_name: str
    source_origin: str  # e.g. "dict.get()", "re.search()", "Optional[T]"
    lineno: int
    col_offset: int
    statement_code: str
    suggested_fix: str


class NullGuardAnalyzer(ast.NodeVisitor):
    def __init__(self, filename: str = "<source>"):
        self.filename = filename
        self.violations: List[NullSafetyViolation] = []
        self.nullable_vars: Set[str] = set()
        self.guarded_vars: Set[str] = set()
        self.var_origins: dict[str, str] = {}

    def _is_none_source(self, node: ast.AST) -> Optional[str]:
        """Detects if an expression produces a potentially None value."""
        if isinstance(node, ast.Constant) and node.value is None:
            return "explicit None assignment"

        if isinstance(node, ast.Call):
            # 1. d.get("key") without non-None default
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if len(node.args) == 1:
                    return ".get() lookup without default"
                elif len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value is None:
                    return ".get() with None default"

            # 2. re.search / re.match
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("search", "match"):
                return "re regex search (returns None on mismatch)"

            # 3. Known functions returning optional
            if isinstance(node.func, ast.Name) and node.func.id.startswith(("find_", "get_", "lookup_", "fetch_")):
                return f"{node.func.id}() lookup"

        return None

    def visit_Assign(self, node: ast.Assign):
        origin = self._is_none_source(node.value)
        if origin:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.nullable_vars.add(target.id)
                    self.var_origins[target.id] = origin
                    self.guarded_vars.discard(target.id)
        else:
            # Overwritten with non-None
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in self.nullable_vars:
                    self.nullable_vars.remove(target.id)
                    self.guarded_vars.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        # Check type annotation: Optional[T] or T | None
        is_optional = False
        if isinstance(node.annotation, ast.Subscript) and isinstance(node.annotation.value, ast.Name) and node.annotation.value.id == "Optional":
            is_optional = True
        elif isinstance(node.annotation, ast.BinOp) and isinstance(node.annotation.op, ast.BitOr):
            if (isinstance(node.annotation.right, ast.Constant) and node.annotation.right.value is None) or \
               (isinstance(node.annotation.right, ast.Name) and node.annotation.right.id == "None"):
                is_optional = True

        if is_optional and isinstance(node.target, ast.Name):
            self.nullable_vars.add(node.target.id)
            self.var_origins[node.target.id] = "Optional type annotation"
            self.guarded_vars.discard(node.target.id)

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Detect guards in condition: e.g. "if x is not None:" or "if x:"
        guarded_here: Set[str] = set()
        test = node.test

        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot):
            if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
                guarded_here.add(test.left.id)

        if isinstance(test, ast.Name):
            guarded_here.add(test.id)

        prev_guarded = set(self.guarded_vars)
        self.guarded_vars.update(guarded_here)

        for stmt in node.body:
            self.visit(stmt)

        self.guarded_vars = prev_guarded

        # Check early exit guard in body: e.g. "if x is None: return"
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Is):
            if isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
                if any(isinstance(b, (ast.Return, ast.Raise, ast.Break)) for b in node.body):
                    self.guarded_vars.add(test.left.id)

        for stmt in node.orelse:
            self.visit(stmt)

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if var_name in self.nullable_vars and var_name not in self.guarded_vars:
                origin = self.var_origins.get(var_name, "potential None source")
                fix = f"{var_name}.{node.attr} if {var_name} is not None else None"
                self.violations.append(
                    NullSafetyViolation(
                        variable_name=var_name,
                        source_origin=origin,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        statement_code=f"{var_name}.{node.attr}",
                        suggested_fix=fix,
                    )
                )
        self.generic_visit(node)


def analyze_null_safety(source_code: str, filename: str = "source.py") -> List[NullSafetyViolation]:
    """Analyzes source code for unguarded nullable dereferences."""
    try:
        tree = ast.parse(source_code, filename=filename)
    except SyntaxError:
        return []

    analyzer = NullGuardAnalyzer(filename=filename)
    analyzer.visit(tree)
    return analyzer.violations


def apply_null_fixes(source_code: str, violations: List[NullSafetyViolation]) -> str:
    """Applies Kotlin-style safe navigation codemods to source code."""
    lines = source_code.splitlines()
    for v in sorted(violations, key=lambda x: (x.lineno, x.col_offset), reverse=True):
        idx = v.lineno - 1
        if 0 <= idx < len(lines):
            lines[idx] = lines[idx].replace(v.statement_code, f"({v.suggested_fix})")
    return "\n".join(lines)
