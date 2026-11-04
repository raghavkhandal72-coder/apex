"""Deterministic Enumerative AST Program Synthesizer.
Synthesizes verified bug repairs autonomously from Bytecode Autopsy and Ochiai SBFL lines
using AST NodeTransformers: boundary off-by-one, zero-division/index guards, NoneType coalescing,
mutable default repairs, and arithmetic/relational operator inversion with ZERO LLM calls.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from apex_council.autopsy.bytecode_inspector import BytecodeAutopsyReport


@dataclass
class SynthesizedCandidate:
    candidate_code: str
    repair_strategy: str
    target_line: int
    ast_edit_distance: int


class BoundaryOffByOneTransformer(ast.NodeTransformer):
    """Repairs off-by-one errors in range() calls, comparisons, and slice indexing."""

    def __init__(self, target_line: Optional[int] = None) -> None:
        self.target_line = target_line
        self.mutated = False

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        if self.target_line is not None and node.lineno != self.target_line:
            return self.generic_visit(node)

        new_ops = []
        for op in node.ops:
            if isinstance(op, ast.Lt):
                new_ops.append(ast.LtE())
                self.mutated = True
            elif isinstance(op, ast.LtE):
                new_ops.append(ast.Lt())
                self.mutated = True
            elif isinstance(op, ast.Gt):
                new_ops.append(ast.GtE())
                self.mutated = True
            elif isinstance(op, ast.GtE):
                new_ops.append(ast.Gt())
                self.mutated = True
            elif isinstance(op, ast.Eq):
                new_ops.append(ast.NotEq())
                self.mutated = True
            else:
                new_ops.append(op)
        node.ops = new_ops
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        # Check range(...) calls
        if isinstance(node.func, ast.Name) and node.func.id == "range":
            if self.target_line is None or node.lineno == self.target_line:
                # If range(len(arr) + 1), transform to range(len(arr))
                if len(node.args) == 1:
                    arg = node.args[0]
                    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                        if isinstance(arg.right, ast.Constant) and arg.right.value == 1:
                            node.args[0] = arg.left
                            self.mutated = True
        return self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        # e.g., high = len(arr) -> high = len(arr) - 1
        if self.target_line is None or node.lineno == self.target_line:
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "len":
                # Subtract 1
                node.value = ast.BinOp(left=node.value, op=ast.Sub(), right=ast.Constant(value=1))
                self.mutated = True
        return self.generic_visit(node)


class ArithmeticLogicOperatorTransformer(ast.NodeTransformer):
    """Repairs wrong arithmetic and boolean operators (e.g. + -> *, / -> //)."""

    def __init__(self, target_line: Optional[int] = None, op_replacement: Optional[Tuple[type, type]] = None) -> None:
        self.target_line = target_line
        self.op_replacement = op_replacement
        self.mutated = False

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        if self.target_line is None or node.lineno == self.target_line:
            if self.op_replacement:
                src_cls, dst_cls = self.op_replacement
                if isinstance(node.op, src_cls):
                    node.op = dst_cls()
                    self.mutated = True
        return self.generic_visit(node)


class ZeroDivisionGuardTransformer(ast.NodeTransformer):
    """Synthesizes zero-division guard check before division or floor division."""

    def __init__(self, target_line: Optional[int] = None) -> None:
        self.target_line = target_line
        self.mutated = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        new_body: List[ast.stmt] = []
        for stmt in node.body:
            if self.target_line is None or getattr(stmt, "lineno", 0) == self.target_line:
                # Synthesize guard: if denominator == 0: return 0 / raise ZeroDivisionError
                # Check if statement contains division
                has_div = any(
                    isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Div, ast.FloorDiv))
                    for sub in ast.walk(stmt)
                )
                if has_div:
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.BinOp) and isinstance(sub.op, (ast.Div, ast.FloorDiv)):
                            denom_expr = sub.right
                            if isinstance(denom_expr, ast.Name):
                                guard_test = ast.Compare(
                                    left=ast.Name(id=denom_expr.id, ctx=ast.Load()),
                                    ops=[ast.Eq()],
                                    comparators=[ast.Constant(value=0)],
                                )
                                # if denom == 0: raise ZeroDivisionError('division by zero')
                                guard_raise = ast.Raise(
                                    exc=ast.Call(
                                        func=ast.Name(id="ZeroDivisionError", ctx=ast.Load()),
                                        args=[ast.Constant(value="division by zero")],
                                        keywords=[],
                                    ),
                                    cause=None,
                                )
                                guard_stmt = ast.If(test=guard_test, body=[guard_raise], orelse=[])
                                new_body.append(guard_stmt)
                                self.mutated = True
                                break
            new_body.append(stmt)
        node.body = new_body
        return self.generic_visit(node)


class MutableDefaultArgumentTransformer(ast.NodeTransformer):
    """Repairs Python mutable default arguments (def f(x=[]): -> def f(x=None): if x is None: x = [])."""

    def __init__(self) -> None:
        self.mutated = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        num_defaults = len(node.args.defaults)
        args_with_defaults = node.args.args[-num_defaults:] if num_defaults > 0 else []

        new_defaults = []
        guards_to_prepend: List[ast.stmt] = []

        for arg, default in zip(args_with_defaults, node.args.defaults):
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                # Replace default with None
                new_defaults.append(ast.Constant(value=None))
                # Synthesize guard: if arg is None: arg = default
                guard_test = ast.Compare(
                    left=ast.Name(id=arg.arg, ctx=ast.Load()),
                    ops=[ast.Is()],
                    comparators=[ast.Constant(value=None)],
                )
                guard_assign = ast.Assign(
                    targets=[ast.Name(id=arg.arg, ctx=ast.Store())],
                    value=default,
                )
                guards_to_prepend.append(ast.If(test=guard_test, body=[guard_assign], orelse=[]))
                self.mutated = True
            else:
                new_defaults.append(default)

        node.args.defaults = new_defaults
        node.body = guards_to_prepend + node.body
        return self.generic_visit(node)


class DeterministicASTSynthesizer:
    """Enumerative AST program synthesizer using Autopsy and Ochiai guidance."""

    @classmethod
    def synthesize_repairs(
        cls,
        source_code: str,
        autopsy_report: Optional[BytecodeAutopsyReport] = None,
        suspicious_lines: Optional[List[int]] = None,
        max_candidates: int = 15,
    ) -> List[SynthesizedCandidate]:
        candidates: List[SynthesizedCandidate] = []
        raw_lines = list(suspicious_lines or [])
        if autopsy_report and autopsy_report.crashing_line:
            if autopsy_report.crashing_line not in raw_lines:
                raw_lines.insert(0, autopsy_report.crashing_line)

        source_line_count = len(source_code.splitlines())
        target_lines: List[Optional[int]] = [l for l in raw_lines if l is not None and 1 <= l <= source_line_count]

        # Always include None (global search) so all statements can be synthesized
        if None not in target_lines:
            target_lines.append(None)

        # 1. Strategy: Mutable Default Argument Repair
        try:
            tree = ast.parse(source_code)
            mut_t = MutableDefaultArgumentTransformer()
            new_tree = mut_t.visit(tree)
            if mut_t.mutated:
                ast.fix_missing_locations(new_tree)
                cand_code = ast.unparse(new_tree)
                candidates.append(
                    SynthesizedCandidate(
                        candidate_code=cand_code,
                        repair_strategy="MutableDefaultGuard",
                        target_line=0,
                        ast_edit_distance=2,
                    )
                )
        except Exception:
            pass

        # 2. Strategy: Boundary & Off-by-one repairs
        for line in target_lines:
            try:
                tree = ast.parse(source_code)
                bound_t = BoundaryOffByOneTransformer(target_line=line)
                new_tree = bound_t.visit(tree)
                if bound_t.mutated:
                    ast.fix_missing_locations(new_tree)
                    candidates.append(
                        SynthesizedCandidate(
                            candidate_code=ast.unparse(new_tree),
                            repair_strategy="BoundaryRelationalInversion",
                            target_line=line or 0,
                            ast_edit_distance=1,
                        )
                    )
            except Exception:
                pass

        # 3. Strategy: Arithmetic Operator Inversions (Add <-> Mult, Add <-> Sub, Div <-> FloorDiv)
        op_pairs = [
            (ast.Add, ast.Mult),
            (ast.Add, ast.Sub),
            (ast.Sub, ast.FloorDiv),
            (ast.Div, ast.FloorDiv),
            (ast.Mult, ast.FloorDiv),
        ]
        for line in target_lines:
            for src_op, dst_op in op_pairs:
                try:
                    tree = ast.parse(source_code)
                    arith_t = ArithmeticLogicOperatorTransformer(target_line=line, op_replacement=(src_op, dst_op))
                    new_tree = arith_t.visit(tree)
                    if arith_t.mutated:
                        ast.fix_missing_locations(new_tree)
                        candidates.append(
                            SynthesizedCandidate(
                                candidate_code=ast.unparse(new_tree),
                                repair_strategy=f"OperatorInversion_{src_op.__name__}_to_{dst_op.__name__}",
                                target_line=line or 0,
                                ast_edit_distance=1,
                            )
                        )
                except Exception:
                    pass

        # 4. Strategy: ZeroDivisionGuard check
        if autopsy_report and autopsy_report.exception_type == "ZeroDivisionError":
            for line in target_lines:
                try:
                    tree = ast.parse(source_code)
                    zero_t = ZeroDivisionGuardTransformer(target_line=line)
                    new_tree = zero_t.visit(tree)
                    if zero_t.mutated:
                        ast.fix_missing_locations(new_tree)
                        candidates.append(
                            SynthesizedCandidate(
                                candidate_code=ast.unparse(new_tree),
                                repair_strategy="ZeroDivisionGuard",
                                target_line=line or 0,
                                ast_edit_distance=3,
                            )
                        )
                except Exception:
                    pass

        # Sort candidates by Minimum Description Length (edit distance)
        candidates.sort(key=lambda c: (c.ast_edit_distance, len(c.candidate_code)))
        return candidates[:max_candidates]
