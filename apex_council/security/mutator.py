"""Zero-Dependency Bare-Metal AST Mutation Testing Gate.
100% Pure Python Standard Library | Red-Team Breaker | Autonomous SDET Gate.

Validates that developer or speculator unit tests actually test logical invariants
rather than asserting trivialities (e.g. `assert True`). Guarantees test suite rigor
by injecting precise single-operator AST mutants (arithmetic, comparisons, boolean logic,
constants) and evaluating survival in the hermetic sandbox.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from apex_council.security.sandbox import HermeticExecutionSandbox


@dataclasses.dataclass(frozen=True)
class MutantSiteSpec:
    site_id: int
    op_category: str  # "BIN_OP", "COMPARE_OP", "BOOL_OP", "BOOLEAN_FLIP", "CONSTANT_SWAP"
    original_op: str
    replacement_op: str
    lineno: int
    col_offset: int


@dataclasses.dataclass
class MutantEvaluationResult:
    site_spec: MutantSiteSpec
    mutated_code: str
    killed: bool
    timed_out: bool = False
    failure_output: str = ""
    execution_time_ms: float = 0.0
    opcode_count: int = 0


@dataclasses.dataclass
class MutationGateReport:
    total_sites: int
    evaluated_mutants: int
    killed_mutants: int
    survived_mutants: int
    timed_out_mutants: int
    mutation_score: float  # 0.0 to 100.0%
    is_airtight: bool      # True if mutation_score >= required_threshold
    results: List[MutantEvaluationResult] = dataclasses.field(default_factory=list)

    @property
    def surviving_mutants(self) -> List[MutantEvaluationResult]:
        return [r for r in self.results if not r.killed and not r.timed_out]


# --- Backward Compatible Dataclasses ---
@dataclasses.dataclass
class Mutant:
    id: int
    operator_type: str
    original_op: str
    mutated_op: str
    lineno: int
    mutated_code: str
    killed: bool = False
    failure_output: str = ""


@dataclasses.dataclass
class MutationReport:
    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    mutation_score: float
    is_airtight: bool
    mutants: List[Mutant]


# --- Operator Inversion Maps ---
BIN_OP_MUTATIONS: Dict[type[ast.operator], type[ast.operator]] = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.FloorDiv,
    ast.FloorDiv: ast.Mult,
    ast.Mod: ast.Mult,
    ast.Pow: ast.Mult,
    ast.BitAnd: ast.BitOr,
    ast.BitOr: ast.BitAnd,
    ast.BitXor: ast.BitAnd,
}

COMPARE_OP_MUTATIONS: Dict[type[ast.cmpop], type[ast.cmpop]] = {
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

BOOL_OP_MUTATIONS: Dict[type[ast.boolop], type[ast.boolop]] = {
    ast.And: ast.Or,
    ast.Or: ast.And,
}


class _MutationSiteEnumerator(ast.NodeVisitor):
    """Scans an AST and enumerates every deterministic mutation site."""

    def __init__(self) -> None:
        self.sites: List[MutantSiteSpec] = []
        self._current_site_id: int = 0

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.generic_visit(node)
        op_cls = type(node.op)
        if op_cls in BIN_OP_MUTATIONS:
            replacement_cls = BIN_OP_MUTATIONS[op_cls]
            self.sites.append(
                MutantSiteSpec(
                    site_id=self._current_site_id,
                    op_category="BIN_OP",
                    original_op=op_cls.__name__,
                    replacement_op=replacement_cls.__name__,
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            )
            self._current_site_id += 1

    def visit_Compare(self, node: ast.Compare) -> None:
        self.generic_visit(node)
        for op in node.ops:
            op_cls = type(op)
            if op_cls in COMPARE_OP_MUTATIONS:
                replacement_cls = COMPARE_OP_MUTATIONS[op_cls]
                self.sites.append(
                    MutantSiteSpec(
                        site_id=self._current_site_id,
                        op_category="COMPARE_OP",
                        original_op=op_cls.__name__,
                        replacement_op=replacement_cls.__name__,
                        lineno=getattr(node, "lineno", 1),
                        col_offset=getattr(node, "col_offset", 0),
                    )
                )
                self._current_site_id += 1

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.generic_visit(node)
        op_cls = type(node.op)
        if op_cls in BOOL_OP_MUTATIONS:
            replacement_cls = BOOL_OP_MUTATIONS[op_cls]
            self.sites.append(
                MutantSiteSpec(
                    site_id=self._current_site_id,
                    op_category="BOOL_OP",
                    original_op=op_cls.__name__,
                    replacement_op=replacement_cls.__name__,
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            )
            self._current_site_id += 1

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, bool):
            self.sites.append(
                MutantSiteSpec(
                    site_id=self._current_site_id,
                    op_category="BOOLEAN_FLIP",
                    original_op=str(node.value),
                    replacement_op=str(not node.value),
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            )
            self._current_site_id += 1


class _SingleSiteASTMutator(ast.NodeTransformer):
    """Mutates exactly one target site index identified by MutantSiteSpec."""

    def __init__(self, target_site_id: int) -> None:
        self.target_site_id = target_site_id
        self._curr_site_id = 0
        self.applied_spec: Optional[MutantSiteSpec] = None

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        op_cls = type(node.op)
        if op_cls in BIN_OP_MUTATIONS:
            if self._curr_site_id == self.target_site_id:
                repl_cls = BIN_OP_MUTATIONS[op_cls]
                node.op = repl_cls()
                self.applied_spec = MutantSiteSpec(
                    site_id=self.target_site_id,
                    op_category="BIN_OP",
                    original_op=op_cls.__name__,
                    replacement_op=repl_cls.__name__,
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            self._curr_site_id += 1
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        new_ops = []
        for op in node.ops:
            op_cls = type(op)
            if op_cls in COMPARE_OP_MUTATIONS:
                if self._curr_site_id == self.target_site_id:
                    repl_cls = COMPARE_OP_MUTATIONS[op_cls]
                    new_ops.append(repl_cls())
                    self.applied_spec = MutantSiteSpec(
                        site_id=self.target_site_id,
                        op_category="COMPARE_OP",
                        original_op=op_cls.__name__,
                        replacement_op=repl_cls.__name__,
                        lineno=getattr(node, "lineno", 1),
                        col_offset=getattr(node, "col_offset", 0),
                    )
                else:
                    new_ops.append(op)
                self._curr_site_id += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        op_cls = type(node.op)
        if op_cls in BOOL_OP_MUTATIONS:
            if self._curr_site_id == self.target_site_id:
                repl_cls = BOOL_OP_MUTATIONS[op_cls]
                node.op = repl_cls()
                self.applied_spec = MutantSiteSpec(
                    site_id=self.target_site_id,
                    op_category="BOOL_OP",
                    original_op=op_cls.__name__,
                    replacement_op=repl_cls.__name__,
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            self._curr_site_id += 1
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, bool):
            if self._curr_site_id == self.target_site_id:
                orig_val = node.value
                node.value = not orig_val
                self.applied_spec = MutantSiteSpec(
                    site_id=self.target_site_id,
                    op_category="BOOLEAN_FLIP",
                    original_op=str(orig_val),
                    replacement_op=str(node.value),
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                )
            self._curr_site_id += 1
        return node


class ASTMutationTestingGate:
    """Bare-Metal AST Mutation Testing Gatekeeper and SDET Test Suite Verifier."""

    @classmethod
    def enumerate_mutation_sites(cls, source_code: str) -> List[MutantSiteSpec]:
        """Discovers all deterministic mutation sites in the given source code."""
        try:
            tree = ast.parse(source_code)
        except Exception:
            return []
        enumerator = _MutationSiteEnumerator()
        enumerator.visit(tree)
        return enumerator.sites

    @classmethod
    def synthesize_mutant(cls, source_code: str, site_id: int) -> Optional[Tuple[str, MutantSiteSpec]]:
        """Applies a single-site mutation and returns (mutated_source, site_spec)."""
        try:
            tree = ast.parse(source_code)
            mutator = _SingleSiteASTMutator(target_site_id=site_id)
            mutated_tree = mutator.visit(tree)
            ast.fix_missing_locations(mutated_tree)
            if mutator.applied_spec is None:
                return None
            mutated_code = ast.unparse(mutated_tree)
            return mutated_code, mutator.applied_spec
        except Exception:
            return None

    @classmethod
    def evaluate_test_rigor(
        cls,
        source_code: str,
        test_harness: str,
        required_kill_score: float = 90.0,
        max_mutants: int = 25,
        timeout_sec: float = 2.0,
    ) -> MutationGateReport:
        """
        Executes zero-dependency mutation testing against test_harness in isolated sandbox.
        A mutant is KILLED if test_harness fails or crashes.
        A mutant SURVIVES if test_harness passes without error (indicating weak test coverage).
        """
        sites = cls.enumerate_mutation_sites(source_code)
        if not sites:
            # Code is trivial or has no mutable operators
            return MutationGateReport(
                total_sites=0,
                evaluated_mutants=0,
                killed_mutants=0,
                survived_mutants=0,
                timed_out_mutants=0,
                mutation_score=100.0,
                is_airtight=True,
                results=[],
            )

        selected_sites = sites[:max_mutants]
        results: List[MutantEvaluationResult] = []
        killed_count = 0
        timed_out_count = 0

        for site in selected_sites:
            synth = cls.synthesize_mutant(source_code, site.site_id)
            if synth is None:
                continue
            mutated_code, applied_spec = synth

            combined_payload = (
                f"{mutated_code}\n\n"
                f"# --- APEX SOVEREIGN MUTATION HARNESS ---\n"
                f"{test_harness}"
            )

            start_t = time.perf_counter()
            passed, duration_ms, output = HermeticExecutionSandbox.execute_isolated(
                combined_payload,
                timeout_sec=timeout_sec,
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            timed_out = "Sandbox Timeout" in output or "timed out" in output.lower()
            if timed_out:
                # Infinite loop or timeout mutation is considered killed by safety watchdog
                timed_out_count += 1
                killed_count += 1
                results.append(
                    MutantEvaluationResult(
                        site_spec=applied_spec,
                        mutated_code=mutated_code,
                        killed=True,
                        timed_out=True,
                        failure_output="Watchdog: Execution timed out / infinite loop killed",
                        execution_time_ms=elapsed_ms,
                    )
                )
            elif not passed:
                # Test failed or raised AssertionError/Exception -> Mutant killed!
                killed_count += 1
                results.append(
                    MutantEvaluationResult(
                        site_spec=applied_spec,
                        mutated_code=mutated_code,
                        killed=True,
                        timed_out=False,
                        failure_output=output[:160],
                        execution_time_ms=elapsed_ms,
                    )
                )
            else:
                # Test unexpectedly PASSED -> Mutant SURVIVED!
                results.append(
                    MutantEvaluationResult(
                        site_spec=applied_spec,
                        mutated_code=mutated_code,
                        killed=False,
                        timed_out=False,
                        failure_output="MUTANT SURVIVED: Test suite passed on corrupted logic",
                        execution_time_ms=elapsed_ms,
                    )
                )

        eval_total = len(results)
        survived_count = eval_total - killed_count
        score = (killed_count / eval_total * 100.0) if eval_total > 0 else 100.0
        is_airtight = score >= required_kill_score

        return MutationGateReport(
            total_sites=len(sites),
            evaluated_mutants=eval_total,
            killed_mutants=killed_count,
            survived_mutants=survived_count,
            timed_out_mutants=timed_out_count,
            mutation_score=round(score, 1),
            is_airtight=is_airtight,
            results=results,
        )


# --- Backward Compatibility Wrapper ---
class ASTMutator(ast.NodeTransformer):
    """Backward-compatible ASTMutator matching original API."""

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
    """Legacy interface maintained for backward compatibility across test suites."""

    @classmethod
    def count_possible_mutations(cls, code: str) -> int:
        return len(ASTMutationTestingGate.enumerate_mutation_sites(code))

    @classmethod
    def generate_mutants(cls, code: str, max_mutants: int = 20) -> List[Mutant]:
        sites = ASTMutationTestingGate.enumerate_mutation_sites(code)
        limit = min(len(sites), max_mutants)
        mutants: List[Mutant] = []

        for idx in range(limit):
            synth = ASTMutationTestingGate.synthesize_mutant(code, sites[idx].site_id)
            if synth is not None:
                mutated_code, spec = synth
                mutants.append(
                    Mutant(
                        id=spec.site_id + 1,
                        operator_type=spec.op_category,
                        original_op=spec.original_op,
                        mutated_op=spec.replacement_op,
                        lineno=spec.lineno,
                        mutated_code=mutated_code,
                    )
                )
        return mutants

    @classmethod
    def evaluate_test_suite_rigor(
        cls,
        code: str,
        test_harness: str,
        max_mutants: int = 15,
        required_kill_score: float = 90.0,
    ) -> MutationReport:
        gate_report = ASTMutationTestingGate.evaluate_test_rigor(
            source_code=code,
            test_harness=test_harness,
            required_kill_score=required_kill_score,
            max_mutants=max_mutants,
        )

        legacy_mutants = [
            Mutant(
                id=r.site_spec.site_id + 1,
                operator_type=r.site_spec.op_category,
                original_op=r.site_spec.original_op,
                mutated_op=r.site_spec.replacement_op,
                lineno=r.site_spec.lineno,
                mutated_code=r.mutated_code,
                killed=r.killed,
                failure_output=r.failure_output,
            )
            for r in gate_report.results
        ]

        return MutationReport(
            total_mutants=gate_report.evaluated_mutants,
            killed_mutants=gate_report.killed_mutants,
            survived_mutants=gate_report.survived_mutants,
            mutation_score=gate_report.mutation_score,
            is_airtight=gate_report.is_airtight,
            mutants=legacy_mutants,
        )


if __name__ == "__main__":
    print("=" * 70)
    print("Apex-Sovereign: Bare-Metal AST Mutation Testing Gate Self-Verification")
    print("=" * 70)

    # 1. Strong Test Suite Verification
    code_strong = "def multiply(a, b):\n    return a * b\n"
    test_strong = "assert multiply(2, 3) == 6\nassert multiply(4, 5) == 20\nassert multiply(10, 0) == 0\n"
    gate_rep_strong = ASTMutationTestingGate.evaluate_test_rigor(code_strong, test_strong)
    print(f"[TEST 1 - STRONG] Sites: {gate_rep_strong.total_sites} | Score: {gate_rep_strong.mutation_score}% | Airtight: {gate_rep_strong.is_airtight}")
    assert gate_rep_strong.is_airtight, "Strong test suite must achieve >= 90% kill score"
    assert gate_rep_strong.killed_mutants == gate_rep_strong.evaluated_mutants

    # 2. Weak Test Suite Catches Survivor
    code_weak = "def compute(a, b):\n    return a + b\n"
    test_weak = "res = compute(5, 5)\nassert isinstance(res, int)\n"
    gate_rep_weak = ASTMutationTestingGate.evaluate_test_rigor(code_weak, test_weak)
    print(f"[TEST 2 - WEAK]   Sites: {gate_rep_weak.total_sites} | Score: {gate_rep_weak.mutation_score}% | Airtight: {gate_rep_weak.is_airtight}")
    assert not gate_rep_weak.is_airtight, "Weak test suite must fail airtight check"
    assert gate_rep_weak.survived_mutants > 0

    print("=" * 70)
    print("ALL MUTATION TESTING GATE CHECKS PASSED - 100% GREEN")
    print("=" * 70)
