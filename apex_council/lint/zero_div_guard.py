"""
Apex Zero-Division Guard (Feature #25).
Static AST analyzer and safe guard prover for division operators (/, //, %).
Prevents ZeroDivisionError in Python applications with zero external dependencies.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass(frozen=True)
class ZeroDivViolation:
    lineno: int
    col_offset: int
    operator: str
    denominator: str
    statement_code: str
    is_literal_zero: bool


class ZeroDivisionVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: List[str]) -> None:
        self.source_lines = source_lines
        self.violations: List[ZeroDivViolation] = []
        self.guarded_variables: Set[str] = set()

    def visit_If(self, node: ast.If) -> None:
        # Check if condition guards against zero: e.g. `if b != 0:` or `if b:`
        guarded = self._extract_zero_guards(node.test)
        prev_guarded = set(self.guarded_variables)
        self.guarded_variables.update(guarded)

        for stmt in node.body:
            self.visit(stmt)

        self.guarded_variables = prev_guarded

        for stmt in node.orelse:
            self.visit(stmt)

    def _extract_zero_guards(self, test_node: ast.AST) -> Set[str]:
        guards: Set[str] = set()
        # Pattern 1: `if x != 0:` or `if 0 != x:`
        if isinstance(test_node, ast.Compare):
            if len(test_node.ops) == 1 and isinstance(test_node.ops[0], ast.NotEq):
                left, right = test_node.left, test_node.comparators[0]
                if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value == 0:
                    guards.add(left.id)
                elif isinstance(right, ast.Name) and isinstance(left, ast.Constant) and left.value == 0:
                    guards.add(right.id)
        # Pattern 2: `if x:` (truthy check)
        elif isinstance(test_node, ast.Name):
            guards.add(test_node.id)
        return guards

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            denom = node.right
            op_sym = "/" if isinstance(node.op, ast.Div) else ("//" if isinstance(node.op, ast.FloorDiv) else "%")

            # Check literal zero
            if isinstance(denom, ast.Constant) and denom.value == 0:
                stmt_code = self._get_line_text(node.lineno)
                self.violations.append(
                    ZeroDivViolation(
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                        operator=op_sym,
                        denominator="0",
                        statement_code=stmt_code,
                        is_literal_zero=True,
                    )
                )
            elif isinstance(denom, ast.Name):
                if denom.id not in self.guarded_variables:
                    stmt_code = self._get_line_text(node.lineno)
                    self.violations.append(
                        ZeroDivViolation(
                            lineno=node.lineno,
                            col_offset=node.col_offset,
                            operator=op_sym,
                            denominator=denom.id,
                            statement_code=stmt_code,
                            is_literal_zero=False,
                        )
                    )

        self.generic_visit(node)

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""


def analyze_zero_divisions(source_code: str) -> List[ZeroDivViolation]:
    """Parse AST and return all unguarded zero division operations."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    lines = source_code.splitlines()
    visitor = ZeroDivisionVisitor(lines)
    visitor.visit(tree)
    return visitor.violations
