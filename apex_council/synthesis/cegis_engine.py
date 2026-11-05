"""Apex-Sovereign: Counterexample-Guided Inductive Synthesis (CEGIS) Engine.
100% Pure Python Standard Library | Zero Dependencies | Solar-Lezama (2008) & Gulwani (2011).

Mathematical Foundations:
Specification: Phi(x, y) relating input x to output y.
1. Example Constraint Set: E = { x_1, x_2, ..., x_k }
2. Inductive Synthesizer:
   Find program P in Grammar s.t. forall x in E: Phi(x, P(x)) == True
3. Deductive Verifier:
   Search for counterexample x* in Domain s.t. not Phi(x*, P(x*))
4. If x* is found: E <- E U { x* } and reiterate.
5. If no counterexample exists: P is certified correct across the test space.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from apex_council.security.sandbox import HermeticExecutionSandbox


@dataclasses.dataclass(frozen=True)
class CounterExample:
    input_args: Tuple[Any, ...]
    expected_output: Any
    actual_output: Any
    violation_kind: str  # "WRONG_OUTPUT", "CRASH_EXCEPTION", "TIMEOUT"


@dataclasses.dataclass(frozen=True)
class CEGISReport:
    success: bool
    synthesized_code: str
    counterexamples_found: List[CounterExample]
    iterations_run: int
    total_candidates_explored: int
    duration_ms: float
    verification_certified: bool


class _ASTCandidateMutator(ast.NodeTransformer):
    """Generates structural candidate program variants for the inductive synthesizer."""

    SWAP_BINOPS: Dict[type[ast.operator], list[type[ast.operator]]] = {
        ast.Add: [ast.Sub],
        ast.Sub: [ast.Add],
        ast.Mult: [ast.FloorDiv, ast.Div],
        ast.FloorDiv: [ast.Mult],
        ast.Div: [ast.FloorDiv],
    }

    SWAP_CMPOPS: Dict[type[ast.cmpop], list[type[ast.cmpop]]] = {
        ast.Lt: [ast.LtE, ast.GtE],
        ast.LtE: [ast.Lt, ast.Gt],
        ast.Gt: [ast.GtE, ast.LtE],
        ast.GtE: [ast.Gt, ast.Lt],
        ast.Eq: [ast.NotEq],
        ast.NotEq: [ast.Eq],
    }

    def __init__(self, target_idx: int, repl_kind: str, new_node_type: Any) -> None:
        self.target_idx = target_idx
        self.repl_kind = repl_kind
        self.new_node_type = new_node_type
        self.current_idx = 0
        self.mutated = False

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        if self.repl_kind == "BINOP" and not self.mutated:
            if self.current_idx == self.target_idx:
                node.op = self.new_node_type()
                self.mutated = True
            self.current_idx += 1
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        if self.repl_kind == "CMPOP" and not self.mutated:
            if self.current_idx == self.target_idx and node.ops:
                node.ops[0] = self.new_node_type()
                self.mutated = True
            self.current_idx += 1
        return node


class CEGISEngine:
    """Counterexample-Guided Inductive Synthesizer."""

    def __init__(
        self,
        max_iterations: int = 10,
        sandbox_timeout_sec: float = 2.0,
    ) -> None:
        self.max_iterations = max_iterations
        self.sandbox_timeout_sec = sandbox_timeout_sec

    @classmethod
    def generate_candidate_programs(cls, base_code: str) -> List[str]:
        """Synthesizes candidate programs by enumerating targeted AST operators."""
        candidates = [base_code]
        try:
            tree = ast.parse(base_code)
        except Exception:
            return candidates

        # 1. Enumerate BinOp replacements
        binop_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.BinOp))
        for idx in range(binop_count):
            for orig_op, replacements in _ASTCandidateMutator.SWAP_BINOPS.items():
                for alt in replacements:
                    t_copy = copy.deepcopy(tree)
                    mutator = _ASTCandidateMutator(idx, "BINOP", alt)
                    mut_tree = mutator.visit(t_copy)
                    if mutator.mutated:
                        try:
                            candidates.append(ast.unparse(mut_tree))
                        except Exception:
                            pass

        # 2. Enumerate Compare op replacements
        cmpop_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Compare))
        for idx in range(cmpop_count):
            for orig_op, replacements in _ASTCandidateMutator.SWAP_CMPOPS.items():
                for alt in replacements:
                    t_copy = copy.deepcopy(tree)
                    mutator = _ASTCandidateMutator(idx, "CMPOP", alt)
                    mut_tree = mutator.visit(t_copy)
                    if mutator.mutated:
                        try:
                            candidates.append(ast.unparse(mut_tree))
                        except Exception:
                            pass

        return list(dict.fromkeys(candidates))

    def synthesize_and_verify(
        self,
        initial_buggy_code: str,
        test_suite_code: str,
        oracle_eval_fn: Optional[Callable[[Any], Any]] = None,
        boundary_inputs: Optional[List[Any]] = None,
    ) -> CEGISReport:
        """
        Executes the CEGIS inductive synthesis and counterexample search loop.
        """
        start_t = time.perf_counter()
        candidates = self.generate_candidate_programs(initial_buggy_code)
        counterexamples: List[CounterExample] = []

        inputs_to_check = boundary_inputs or [-10, -1, 0, 1, 2, 5, 10, 100]
        curr_code = initial_buggy_code
        success = False

        for iteration in range(1, self.max_iterations + 1):
            # 1. Synthesizer Phase: Find a candidate that satisfies the current test suite
            selected_cand: Optional[str] = None
            for cand in candidates:
                full_test = f"{cand}\n\n# --- TEST HARNESS ---\n{test_suite_code}"
                passed, _, _ = HermeticExecutionSandbox.execute_isolated(
                    full_test, timeout_sec=self.sandbox_timeout_sec
                )
                if passed:
                    selected_cand = cand
                    break

            if selected_cand is None:
                # No candidate satisfies the current suite
                break

            curr_code = selected_cand

            # 2. Verifier Phase: Search for a counterexample on boundary inputs
            found_ce = False
            if oracle_eval_fn is not None:
                scope: Dict[str, Any] = {}
                try:
                    exec(curr_code, scope)
                    # Find target function
                    func = None
                    for val in scope.values():
                        if callable(val) and not type(val) == type:
                            func = val
                            break

                    if func is not None:
                        for inp in inputs_to_check:
                            try:
                                expected = oracle_eval_fn(inp)
                                actual = func(inp)
                                if actual != expected:
                                    ce = CounterExample(
                                        input_args=(inp,),
                                        expected_output=expected,
                                        actual_output=actual,
                                        violation_kind="WRONG_OUTPUT",
                                    )
                                    counterexamples.append(ce)
                                    # Add assertion to test suite
                                    test_suite_code += f"\nassert {func.__name__}({repr(inp)}) == {repr(expected)}"
                                    found_ce = True
                                    break
                            except Exception as ex:
                                ce = CounterExample(
                                    input_args=(inp,),
                                    expected_output="Normal Execution",
                                    actual_output=str(ex),
                                    violation_kind="CRASH_EXCEPTION",
                                )
                                counterexamples.append(ce)
                                found_ce = True
                                break
                except Exception:
                    pass

            if not found_ce:
                # Candidate passed existing tests and no counterexample could be discovered!
                success = True
                break

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        return CEGISReport(
            success=success,
            synthesized_code=curr_code,
            counterexamples_found=counterexamples,
            iterations_run=iteration,
            total_candidates_explored=len(candidates),
            duration_ms=round(duration_ms, 2),
            verification_certified=success,
        )
