"""Zero-Dependency AST Mutation Testing Engine.
Mutates binary, boolean, and comparison operators to verify test suite rigor.
Guarantees Mutation Kill Score >= 90% before Gatekeeper approval.
Pure Python standard library implementation.
"""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from apex_council.security.sandbox import HermeticExecutionSandbox


@dataclass
class Mutant:
    id: int
    operator_type: str
    original_op: str
    mutated_op: str
    lineno: int
    mutated_code: str
    killed: bool = False
    failure_output: str = ""


@dataclass
class MutationReport:
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    mutation_score: float  # Percentage (0 - 100%)
    is_airtight: bool  # True if mutation_score >= 90.0%
    mutants: List[Mutant]


class ASTMutator(ast.NodeTransformer):
    """Generates precise single-operator mutants across an AST tree."""

    BIN_OP_MAP = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.FloorDiv,
        ast.FloorDiv: ast.Mult,
        ast.Mod: ast.Mult,
    }

    COMPARE_OP_MAP = {
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.GtE,
        ast.LtE: ast.Gt,
        ast.Gt: ast.LtE,
        ast.GtE: ast.Lt,
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
    }

    def __init__(self, target_mutation_index: int) -> None:
        self.target_mutation_index = target_mutation_index
        self.current_index = 0
        self.applied_mutant: Optional[Dict[str, Any]] = None

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        op_type = type(node.op)
        if op_type in self.BIN_OP_MAP:
            if self.current_index == self.target_mutation_index:
                new_op_cls = self.BIN_OP_MAP[op_type]
                orig_name = op_type.__name__
                mut_name = new_op_cls.__name__
                node.op = new_op_cls()
                self.applied_mutant = {
                    "type": "BIN_OP",
                    "orig": orig_name,
                    "mut": mut_name,
                    "lineno": getattr(node, "lineno", 1),
                }
            self.current_index += 1
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        new_ops = []
        for op in node.ops:
            op_type = type(op)
            if op_type in self.COMPARE_OP_MAP:
                if self.current_index == self.target_mutation_index:
                    new_op_cls = self.COMPARE_OP_MAP[op_type]
                    orig_name = op_type.__name__
                    mut_name = new_op_cls.__name__
                    new_ops.append(new_op_cls())
                    self.applied_mutant = {
                        "type": "COMPARE_OP",
                        "orig": orig_name,
                        "mut": mut_name,
                        "lineno": getattr(node, "lineno", 1),
                    }
                else:
                    new_ops.append(op)
                self.current_index += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool):
            if self.current_index == self.target_mutation_index:
                orig_val = node.value
                node.value = not node.value
                self.applied_mutant = {
                    "type": "BOOLEAN_FLIP",
                    "orig": str(orig_val),
                    "mut": str(node.value),
                    "lineno": getattr(node, "lineno", 1),
                }
            self.current_index += 1
        return node


class ASTMutationEngine:
    """Evaluates test suite strength by injecting mutants into candidate code."""

    @classmethod
    def count_possible_mutations(cls, code: str) -> int:
        try:
            tree = ast.parse(code)
        except Exception:
            return 0
        mutator = ASTMutator(target_mutation_index=-1)
        mutator.visit(tree)
        return mutator.current_index

    @classmethod
    def generate_mutants(cls, code: str, max_mutants: int = 20) -> List[Mutant]:
        total_possible = cls.count_possible_mutations(code)
        limit = min(total_possible, max_mutants)
        mutants: List[Mutant] = []

        for idx in range(limit):
            try:
                tree = ast.parse(code)
                mutator = ASTMutator(target_mutation_index=idx)
                mutated_tree = mutator.visit(tree)
                ast.fix_missing_locations(mutated_tree)
                mutated_code = ast.unparse(mutated_tree) if hasattr(ast, "unparse") else code
                if mutator.applied_mutant:
                    info = mutator.applied_mutant
                    mutants.append(
                        Mutant(
                            id=idx + 1,
                            operator_type=info["type"],
                            original_op=info["orig"],
                            mutated_op=info["mut"],
                            lineno=info["lineno"],
                            mutated_code=mutated_code,
                        )
                    )
            except Exception:
                continue

        return mutants

    @classmethod
    def evaluate_test_suite_rigor(
        cls,
        code: str,
        test_harness: str,
        max_mutants: int = 15,
        required_kill_score: float = 90.0,
    ) -> MutationReport:
        mutants = cls.generate_mutants(code, max_mutants=max_mutants)
        if not mutants:
            # No mutable operators found (trivial code)
            return MutationReport(0, 0, 0, 100.0, True, [])

        killed_count = 0
        for m in mutants:
            combined = f"{m.mutated_code}\n\n# --- MUTATION TEST HARNESS ---\n{test_harness}"
            passed, duration_ms, output = HermeticExecutionSandbox.execute_isolated(combined, timeout_sec=2.0)
            
            # If the test fails, the mutant was successfully caught and killed!
            if not passed:
                m.killed = True
                m.failure_output = output[:100]
                killed_count += 1
            else:
                m.killed = False

        survived_count = len(mutants) - killed_count
        score = (killed_count / len(mutants)) * 100.0

        return MutationReport(
            total_mutants=len(mutants),
            killed_mutants=killed_count,
            survived_mutants=survived_count,
            mutation_score=round(score, 1),
            is_airtight=score >= required_kill_score,
            mutants=mutants,
        )
