"""Apex: Counterexample-Guided Inductive Synthesis (CEGIS) Engine.
100% Pure Python Standard Library | Zero Dependencies | Solar-Lezama (2008) & Gulwani (2011).

Mathematical Foundations:
Specification: Phi(x, y) relating input x to output y.
1. Active Constraint Set: E = { test_1 }
2. Inductive Synthesizer:
   Find candidate program P in Grammar s.t. forall t in E: eval(P, t) == Pass
3. Deductive Verifier:
   Search for counterexample t* in Verifier Test Pool / Boundary Domain s.t. eval(P, t*) != Pass
4. If t* found:
   E <- E U { t* }, record round log, and reiterate synthesizer.
5. If no counterexample exists:
   P is certified correct across the verified bounded domain.
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
    input_desc: str
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
    round_logs: List[str] = dataclasses.field(default_factory=list)


class _ASTCandidateMutator:
    """Targeted AST operator and boundary constant replacement maps for inductive program repair."""

    SWAP_BINOPS: Dict[type[ast.operator], list[type[ast.operator]]] = {
        ast.Add: [ast.Sub],
        ast.Sub: [ast.Add],
        ast.Mult: [ast.FloorDiv, ast.Div],
        ast.FloorDiv: [ast.Mult],
        ast.Div: [ast.Mult],
        ast.BitAnd: [ast.BitOr],
        ast.BitOr: [ast.BitAnd],
    }

    SWAP_CMPOPS: Dict[type[ast.cmpop], list[type[ast.cmpop]]] = {
        ast.Lt: [ast.NotEq, ast.LtE],
        ast.LtE: [ast.NotEq, ast.Lt, ast.Eq],
        ast.Gt: [ast.NotEq, ast.GtE],
        ast.GtE: [ast.NotEq, ast.Gt, ast.Eq],
        ast.Eq: [ast.NotEq, ast.LtE, ast.GtE],
        ast.NotEq: [ast.Eq],
        ast.In: [ast.NotIn],
        ast.NotIn: [ast.In],
        ast.Is: [ast.IsNot],
        ast.IsNot: [ast.Is],
    }

    SWAP_BOOLOPS: Dict[type[ast.boolop], list[type[ast.boolop]]] = {
        ast.And: [ast.Or],
        ast.Or: [ast.And],
    }

    @staticmethod
    def get_constant_mutations(val: int) -> list[int]:
        """Generates off-by-one and boundary sentinel replacements for an integer constant."""
        replacements = [val + 1, val - 1]
        if val != 0 and 0 not in replacements:
            replacements.append(0)
        if val != -1 and -1 not in replacements:
            replacements.append(-1)
        return replacements


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
        """Synthesizes candidate programs by targeted AST mutations, prioritizing minimal edits."""
        candidates: List[str] = []
        try:
            tree = ast.parse(base_code)
        except Exception:
            return [base_code]

        # 1. Compare operators (loop boundaries and condition checks)
        cmp_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Compare) and n.ops]
        for node in cmp_nodes:
            current_op = type(node.ops[0])
            replacements = _ASTCandidateMutator.SWAP_CMPOPS.get(current_op, [])
            for new_op in replacements:
                t_copy = copy.deepcopy(tree)
                for n in ast.walk(t_copy):
                    if (
                        isinstance(n, ast.Compare)
                        and n.ops
                        and type(n.ops[0]) == current_op
                        and getattr(n, "lineno", -1) == getattr(node, "lineno", -1)
                        and getattr(n, "col_offset", -1) == getattr(node, "col_offset", -1)
                    ):
                        n.ops[0] = new_op()
                        try:
                            candidates.append(ast.unparse(t_copy))
                        except Exception:
                            pass
                        break

        # 2. BinOp operators (arithmetic and step mutations)
        binop_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp)]
        for node in binop_nodes:
            current_op = type(node.op)
            replacements = _ASTCandidateMutator.SWAP_BINOPS.get(current_op, [])
            for new_op in replacements:
                t_copy = copy.deepcopy(tree)
                for n in ast.walk(t_copy):
                    if (
                        isinstance(n, ast.BinOp)
                        and type(n.op) == current_op
                        and getattr(n, "lineno", -1) == getattr(node, "lineno", -1)
                        and getattr(n, "col_offset", -1) == getattr(node, "col_offset", -1)
                    ):
                        n.op = new_op()
                        try:
                            candidates.append(ast.unparse(t_copy))
                        except Exception:
                            pass
                        break

        # 3. BoolOp operators (boolean logic: and <-> or)
        boolop_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.BoolOp)]
        for node in boolop_nodes:
            current_op = type(node.op)
            replacements = _ASTCandidateMutator.SWAP_BOOLOPS.get(current_op, [])
            for new_op in replacements:
                t_copy = copy.deepcopy(tree)
                for n in ast.walk(t_copy):
                    if (
                        isinstance(n, ast.BoolOp)
                        and type(n.op) == current_op
                        and getattr(n, "lineno", -1) == getattr(node, "lineno", -1)
                        and getattr(n, "col_offset", -1) == getattr(node, "col_offset", -1)
                    ):
                        n.op = new_op()
                        try:
                            candidates.append(ast.unparse(t_copy))
                        except Exception:
                            pass
                        break

        # 4. Constant integer boundary replacements (off-by-one: +1/-1 and boundary sentinels: 0, -1)
        const_nodes = [
            n for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool)
        ]
        for node in const_nodes:
            current_val = node.value
            replacements = _ASTCandidateMutator.get_constant_mutations(current_val)
            for new_val in replacements:
                t_copy = copy.deepcopy(tree)
                for n in ast.walk(t_copy):
                    if (
                        isinstance(n, ast.Constant)
                        and n.value == current_val
                        and not isinstance(n.value, bool)
                        and getattr(n, "lineno", -1) == getattr(node, "lineno", -1)
                        and getattr(n, "col_offset", -1) == getattr(node, "col_offset", -1)
                    ):
                        n.value = new_val
                        try:
                            candidates.append(ast.unparse(t_copy))
                        except Exception:
                            pass
                        break

        # Remove duplicates while preserving exploration order
        deduped = []
        seen = set()
        for c in candidates:
            if c not in seen and c != base_code:
                seen.add(c)
                deduped.append(c)

        return deduped

    @classmethod
    def generate_hidden_invariant_probes(cls, code: str) -> List[str]:
        """Synthesizes hidden boundary & property invariant probes to challenge candidate repairs."""
        probes: List[str] = []
        try:
            tree = ast.parse(code)
        except Exception:
            return probes

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                fn_name = node.name
                args = [a.arg for a in node.args.args]

                # Case 1: Search algorithms taking (arr, target) or (nums, target)
                if ("arr" in args or "nums" in args) and "target" in args:
                    probes.extend([
                        f"assert {fn_name}([], 42) == -1",
                        f"assert {fn_name}([10], 10) == 0",
                        f"assert {fn_name}([10], 20) == -1",
                        f"assert {fn_name}([1, 2], 1) == 0",
                        f"assert {fn_name}([1, 2], 2) == 1",
                        f"assert {fn_name}([1, 2], 3) == -1",
                        f"assert {fn_name}([1, 3, 5, 7, 9], 1) == 0",
                        f"assert {fn_name}([1, 3, 5, 7, 9], 9) == 4",
                        f"assert {fn_name}([1, 3, 5, 7, 9], 0) == -1",
                        f"assert {fn_name}([1, 3, 5, 7, 9], 10) == -1",
                    ])
                # Case 2: Arithmetic binary operators with (a, b) or (x, y)
                elif len(args) == 2 and args in (["a", "b"], ["x", "y"]):
                    probes.extend([
                        f"assert {fn_name}(0, 0) == 0",
                        f"assert {fn_name}(1, 0) == 1",
                        f"assert {fn_name}(0, 1) == 1",
                        f"assert {fn_name}(-5, 5) == 0",
                    ])
                # Case 3: 1-argument boolean predicate / condition checks
                elif len(args) == 1 and (
                    fn_name.startswith(("is_", "has_", "can_", "check_"))
                    or (isinstance(node.returns, ast.Name) and node.returns.id == "bool")
                ):
                    arg_name = args[0]
                    first_arg = node.args.args[0]
                    is_str = arg_name in ("s", "text", "string", "st") or (
                        first_arg.annotation
                        and isinstance(first_arg.annotation, ast.Name)
                        and first_arg.annotation.id == "str"
                    )
                    if is_str:
                        probes.extend([
                            f'assert {fn_name}("") is True',
                            f'assert {fn_name}("a") is True',
                            f'assert {fn_name}("aba") is True',
                            f'assert {fn_name}("ab") is False',
                        ])
                    else:
                        probes.extend([
                            f"assert {fn_name}(0) is False",
                            f"assert {fn_name}(1) is True",
                            f"assert {fn_name}(-1) is False",
                        ])

        return probes

    def synthesize_and_verify(
        self,
        initial_buggy_code: str,
        test_suite_code: str,
        oracle_eval_fn: Optional[Callable[[Any], Any]] = None,
        boundary_inputs: Optional[List[Any]] = None,
        generate_hidden_probes: bool = True,
    ) -> CEGISReport:
        """Executes the CEGIS inductive synthesis and counterexample search loop."""
        start_t = time.perf_counter()
        candidates = self.generate_candidate_programs(initial_buggy_code)
        counterexamples: List[CounterExample] = []
        round_logs: List[str] = []

        # Parse test suite into individual test assertions / statements
        test_units: List[str] = []
        try:
            tree = ast.parse(test_suite_code)
            for node in tree.body:
                if isinstance(node, (ast.Assert, ast.Expr, ast.FunctionDef)):
                    test_units.append(ast.unparse(node))
        except Exception:
            test_units = [line.strip() for line in test_suite_code.splitlines() if line.strip() and not line.strip().startswith("#")]

        if not test_units:
            test_units = [test_suite_code]

        # Generate automated hidden invariant probes from AST structure
        hidden_probes: List[str] = []
        if generate_hidden_probes and not oracle_eval_fn:
            hidden_probes = self.generate_hidden_invariant_probes(initial_buggy_code)

        # Active constraint set E starts with minimal initial constraints
        active_constraints: List[str] = [test_units[0]]
        # Verifier pool contains remaining user tests + hidden invariant probes
        unverified_pool: List[str] = list(test_units[1:]) + list(hidden_probes)

        curr_code = initial_buggy_code
        success = False
        iteration = 0

        for iteration in range(1, self.max_iterations + 1):
            # 1. SYNTHESIZER: Find candidate P that passes all active constraints in E
            selected_cand: Optional[str] = None
            for cand in candidates:
                constraint_suite = "\n".join(active_constraints)
                harness = f"{cand}\n\n# --- ACTIVE CONSTRAINTS (E) ---\n{constraint_suite}"
                passed, _, _ = HermeticExecutionSandbox.execute_isolated(
                    harness, timeout_sec=self.sandbox_timeout_sec
                )
                if passed:
                    selected_cand = cand
                    break

            if selected_cand is None:
                round_logs.append(
                    f"Round {iteration}: Synthesizer exhausted candidate space ({len(candidates)} candidates) "
                    f"without satisfying active constraint set E ({len(active_constraints)} constraints)."
                )
                break

            curr_code = selected_cand

            # 2. VERIFIER: Search for counterexamples across remaining user tests and hidden probes
            found_ce: Optional[str] = None
            actual_error: str = ""

            for unit in list(unverified_pool):
                test_harness = f"{curr_code}\n\n# --- VERIFIER PROBE ---\n{unit}"
                passed, _, out = HermeticExecutionSandbox.execute_isolated(
                    test_harness, timeout_sec=self.sandbox_timeout_sec
                )
                if not passed:
                    found_ce = unit
                    actual_error = out.strip().splitlines()[-1] if out.strip() else "AssertionError"
                    break

            # 3. VERIFIER ORACLE / BOUNDARY CHECK (if custom oracle provided)
            if found_ce is None and oracle_eval_fn and boundary_inputs:
                scope: Dict[str, Any] = {}
                try:
                    exec(compile(curr_code, "<candidate>", "exec"), scope)
                    fn_name = next((k for k, v in scope.items() if callable(v)), None)
                    if fn_name:
                        for b_in in boundary_inputs:
                            actual = scope[fn_name](b_in)
                            expected = oracle_eval_fn(b_in)
                            if actual != expected:
                                found_ce = f"assert {fn_name}({b_in!r}) == {expected!r}"
                                actual_error = f"Returned {actual!r} instead of {expected!r}"
                                break
                except Exception as ex:
                    found_ce = f"# Oracle crash probe: {ex}"
                    actual_error = str(ex)

            if found_ce is not None:
                # Counterexample discovered by Verifier! Add to active constraints E and reiterate
                ce = CounterExample(
                    input_desc=found_ce,
                    expected_output="Assertion / Invariant satisfied",
                    actual_output=actual_error,
                    violation_kind="WRONG_OUTPUT" if "Assertion" in actual_error else "CRASH_EXCEPTION",
                )
                counterexamples.append(ce)
                active_constraints.append(found_ce)
                if found_ce in unverified_pool:
                    unverified_pool.remove(found_ce)
                round_logs.append(
                    f"Round {iteration}: Candidate passed active constraints ({len(active_constraints)-1}), "
                    f"but Verifier found Counterexample: `{found_ce}` ({actual_error}). Added to constraint set E."
                )
                continue

            # 4. CERTIFICATION: Candidate passed all constraints and all hidden verifier probes!
            total_verified = len(test_units) + len(hidden_probes)
            round_logs.append(
                f"Round {iteration}: Candidate satisfied all {len(active_constraints)} constraints in E and passed "
                f"all {total_verified} verifier assertions ({len(hidden_probes)} automated hidden probes). "
                f"Zero counterexamples found across domain."
            )
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
            round_logs=round_logs,
        )
