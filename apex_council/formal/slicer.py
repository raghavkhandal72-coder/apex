"""
Apex Slicer: Backward and Forward Program Slicing on Python AST (Weiser 1981).
Extracts minimal data-flow and control-flow slices for debugging and fault localization.
Pure Python standard library only (pip = 0).
"""

from __future__ import annotations

import ast
import re
from typing import Dict, List, Optional, Set, Tuple


class VariableVisitor(ast.NodeVisitor):
    """Collects loaded (used) and stored (defined) variable names in an AST subtree."""

    def __init__(self) -> None:
        self.loads: Set[str] = set()
        self.stores: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.loads.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Del)):
            self.stores.add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self.stores.add(node.arg)
        self.generic_visit(node)


def extract_shallow_def_use(node: ast.AST) -> Tuple[Set[str], Set[str]]:
    """Extract defs and uses for a statement without recursing into nested statement blocks."""
    defs: Set[str] = set()
    uses: Set[str] = set()
    visitor = VariableVisitor()

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        defs.add(node.name)
        for arg in node.args.args + node.args.kwonlyargs:
            defs.add(arg.arg)
        if node.args.vararg:
            defs.add(node.args.vararg.arg)
        if node.args.kwarg:
            defs.add(node.args.kwarg.arg)
        for dec in node.decorator_list:
            visitor.visit(dec)
        uses.update(visitor.loads)
        return defs, uses

    if isinstance(node, ast.ClassDef):
        defs.add(node.name)
        for base in node.bases:
            visitor.visit(base)
        uses.update(visitor.loads)
        return defs, uses

    if isinstance(node, (ast.If, ast.While)):
        visitor.visit(node.test)
        uses.update(visitor.loads)
        return defs, uses

    if isinstance(node, (ast.For, ast.AsyncFor)):
        visitor.visit(node.target)
        defs.update(visitor.stores)
        v_uses = VariableVisitor()
        v_uses.visit(node.iter)
        uses.update(v_uses.loads)
        return defs, uses

    if isinstance(node, ast.Assign):
        for target in node.targets:
            v_def = VariableVisitor()
            v_def.visit(target)
            defs.update(v_def.stores)
        v_val = VariableVisitor()
        v_val.visit(node.value)
        uses.update(v_val.loads)
        return defs, uses

    if isinstance(node, ast.AugAssign):
        v_def = VariableVisitor()
        v_def.visit(node.target)
        defs.update(v_def.stores)
        uses.update(v_def.stores)
        v_val = VariableVisitor()
        v_val.visit(node.value)
        uses.update(v_val.loads)
        return defs, uses

    if isinstance(node, ast.AnnAssign):
        v_def = VariableVisitor()
        v_def.visit(node.target)
        defs.update(v_def.stores)
        if node.value:
            v_val = VariableVisitor()
            v_val.visit(node.value)
            uses.update(v_val.loads)
        return defs, uses

    if isinstance(node, ast.Return):
        if node.value:
            visitor.visit(node.value)
            uses.update(visitor.loads)
        return defs, uses

    # Generic fallback: visit non-statement fields
    for field, value in ast.iter_fields(node):
        if field in ("body", "orelse", "finalbody"):
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST) and not isinstance(item, ast.stmt):
                    visitor.visit(item)
        elif isinstance(value, ast.AST) and not isinstance(value, ast.stmt):
            visitor.visit(value)

    defs.update(visitor.stores)
    uses.update(visitor.loads)
    return defs, uses


class StatementInfo:
    def __init__(self, lineno: int, node: ast.AST, enclosing_control: Optional[int] = None) -> None:
        self.lineno = lineno
        self.node = node
        self.enclosing_control = enclosing_control
        self.defs, self.uses = extract_shallow_def_use(node)


def build_statement_map(tree: ast.AST) -> Dict[int, StatementInfo]:
    """Traverse AST and associate line numbers with Def-Use sets and enclosing control statements."""
    stmt_map: Dict[int, StatementInfo] = {}

    def traverse(node: ast.AST, current_control: Optional[int]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                lineno = getattr(child, "lineno", None)
                if lineno is not None and lineno not in stmt_map:
                    stmt_map[lineno] = StatementInfo(lineno, child, current_control)

                new_control = lineno if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)) else current_control
                traverse(child, new_control)
            else:
                traverse(child, current_control)

    traverse(tree, None)
    return stmt_map


def compute_backward_slice(
    source_code: str,
    target_line: int,
    variables: Optional[Set[str]] = None,
) -> Tuple[List[int], List[str]]:
    """Compute the backward slice of source_code at target_line.
    
    Returns:
        (slice_line_numbers, slice_source_lines)
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return [target_line], [f"# Syntax error parsing source: {e}"]

    source_lines = source_code.splitlines()
    stmt_map = build_statement_map(tree)

    # If variables not explicitly provided, collect all variables used on target_line
    active_vars: Set[str] = set()
    if variables:
        active_vars.update(variables)
    else:
        if target_line in stmt_map:
            active_vars.update(stmt_map[target_line].uses)
            active_vars.update(stmt_map[target_line].defs)
        else:
            # Fallback regex word token search on line text
            if 1 <= target_line <= len(source_lines):
                line_text = source_lines[target_line - 1]
                words = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", line_text))
                active_vars.update(words)

    slice_lines: Set[int] = {target_line}
    changed = True

    # Iterative fixed-point data-flow and control-flow slice propagation
    while changed:
        changed = False
        # Iterate statements in reverse order before target_line
        for lineno in sorted([l for l in stmt_map.keys() if l <= max(slice_lines)], reverse=True):
            info = stmt_map[lineno]
            # Does this statement define any currently active variable?
            if info.defs.intersection(active_vars) or lineno in slice_lines:
                if lineno not in slice_lines:
                    slice_lines.add(lineno)
                    changed = True

                # Add variables used by this statement to active_vars
                new_uses = info.uses - active_vars
                if new_uses:
                    active_vars.update(new_uses)
                    changed = True

                # Propagate enclosing control dependencies
                if info.enclosing_control is not None and info.enclosing_control not in slice_lines:
                    slice_lines.add(info.enclosing_control)
                    changed = True

    sorted_lines = sorted(list(slice_lines))
    # Extract corresponding lines from original source
    sliced_code = [
        source_lines[l - 1] for l in sorted_lines if 1 <= l <= len(source_lines)
    ]
    return sorted_lines, sliced_code


def format_slice_report(
    filename: str,
    target_line: int,
    slice_lines: List[int],
    source_code: str,
) -> str:
    """Format slice result with side-by-side terminal representation."""
    orig_lines = source_code.splitlines()
    total_lines = len(orig_lines)
    reduction = 100.0 * (1.0 - (len(slice_lines) / max(total_lines, 1)))

    output = [
        f"APEX SLICE  ->  {filename}:{target_line}",
        "─" * 64,
        f"Total statements: {total_lines}  |  Slice statements: {len(slice_lines)} ({reduction:.1f}% reduction)",
        "─" * 64,
    ]

    for idx, line in enumerate(orig_lines, start=1):
        if idx in slice_lines:
            marker = ">>>" if idx == target_line else "  *"
            output.append(f"{marker} L{idx:03d}: {line}")
        else:
            output.append(f"    L{idx:03d}: [dim]{line}[/dim]" if False else f"    L{idx:03d}: ·")

    output.append("─" * 64)
    output.append(f"Isolated {len(slice_lines)} causal lines influencing L{target_line}.\n")
    return "\n".join(output)
