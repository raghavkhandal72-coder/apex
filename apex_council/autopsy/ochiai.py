#!/usr/bin/env python3
"""
Apex-Sovereign: Ochiai Spectrum-Based Fault Localization (SBFL) Engine
100% Pure Python Standard Library | Zero External Dependencies | Zero Mocks
"""

from __future__ import annotations

import ast
import dataclasses
import math
import sys
import types
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class LineSpectrumRank:
    lineno: int
    ochiai_score: float
    tarantula_score: float
    ef: int  # Failed tests executing this line
    nf: int  # Failed tests NOT executing this line
    ep: int  # Passed tests executing this line
    np: int  # Passed tests NOT executing this line
    enclosing_scope: str
    ast_node_type: str
    source_line: str


@dataclasses.dataclass(frozen=True)
class FaultLocalizationReport:
    total_tests: int
    passed_tests: int
    failed_tests: int
    ranked_lines: List[LineSpectrumRank]
    failing_test_errors: Dict[str, str]


@dataclasses.dataclass
class SuspiciousStatement:
    file_path: str
    line_number: int
    suspiciousness: float
    failed_executions: int  # ef: failed tests executing line
    passed_executions: int  # ep: passed tests executing line
    source_code: str = ""


class _ASTLineScopeMapper(ast.NodeVisitor):
    """Maps every source line number to its enclosing class/function scope and AST statement kind."""

    def __init__(self) -> None:
        self.scope_stack: List[str] = ["<module>"]
        self.line_to_scope: Dict[int, str] = {}
        self.line_to_node_type: Dict[int, str] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope_stack.append(node.name)
        self._record(node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope_stack.append(node.name)
        self._record(node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scope_stack.append(node.name)
        self._record(node)
        self.generic_visit(node)
        self.scope_stack.pop()

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.stmt):
            self._record(node)
        super().generic_visit(node)

    def _record(self, node: ast.AST) -> None:
        lineno = getattr(node, "lineno", None)
        end_lineno = getattr(node, "end_lineno", lineno)
        if lineno is not None and end_lineno is not None:
            scope_str = ".".join(self.scope_stack[1:]) if len(self.scope_stack) > 1 else "<module>"
            for ln in range(lineno, end_lineno + 1):
                self.line_to_scope[ln] = scope_str
                if ln == lineno:
                    self.line_to_node_type[ln] = type(node).__name__


class OchiaiFaultLocalizer:
    """
    Executes granular unit tests under `sys.settrace` to record line coverage spectra
    and ranks suspicious lines using the Ochiai and Tarantula mathematical formulas:
        Ochiai(s) = ef(s) / sqrt((ef(s) + nf(s)) * (ef(s) + ep(s)))
    """

    def __init__(self) -> None:
        self.passing_runs: List[Set[Tuple[str, int]]] = []
        self.failing_runs: List[Set[Tuple[str, int]]] = []
        self.source_cache: Dict[str, List[str]] = {}

    @staticmethod
    def split_test_suite(test_code: str) -> List[Tuple[str, str]]:
        """
        Automatically decomposes a test script into granular test cases:
        - If `def test_*()` functions exist, each function becomes an isolated test run.
        - Otherwise, each top-level `assert` statement becomes an isolated test run
          while preserving shared setup statements.
        """
        tree = ast.parse(test_code)
        setup_nodes: List[ast.stmt] = []
        test_funcs: List[ast.FunctionDef] = []
        top_asserts: List[Tuple[int, ast.Assert]] = []

        for idx, stmt in enumerate(tree.body):
            if isinstance(stmt, ast.FunctionDef) and stmt.name.startswith("test_"):
                test_funcs.append(stmt)
            elif isinstance(stmt, ast.Assert):
                top_asserts.append((idx + 1, stmt))
            else:
                setup_nodes.append(stmt)

        setup_src = "\n".join(ast.unparse(n) for n in setup_nodes)
        granular_tests: List[Tuple[str, str]] = []

        if test_funcs:
            for fn in test_funcs:
                fn_src = ast.unparse(fn)
                harness = f"{setup_src}\n{fn_src}\n{fn.name}()\n"
                granular_tests.append((fn.name, harness))
        elif top_asserts:
            for idx, assert_stmt in top_asserts:
                assert_src = ast.unparse(assert_stmt)
                harness = f"{setup_src}\n{assert_src}\n"
                granular_tests.append((f"assert_line_{assert_stmt.lineno or idx}", harness))
        else:
            granular_tests.append(("test_main", test_code))

        return granular_tests

    def localize(
        self,
        source_code: str,
        test_code: str,
        top_k: int = 10,
        target_filename: str = "<apex_ochiai_target>",
    ) -> FaultLocalizationReport:
        source_lines = source_code.splitlines()
        max_source_line = len(source_lines)

        mapper = _ASTLineScopeMapper()
        mapper.visit(ast.parse(source_code))

        granular_tests = self.split_test_suite(test_code)
        passed_count = 0
        failed_count = 0

        # Line -> (ef, ep) counters
        ef_counts: Dict[int, int] = {ln: 0 for ln in range(1, max_source_line + 1)}
        ep_counts: Dict[int, int] = {ln: 0 for ln in range(1, max_source_line + 1)}
        failing_errors: Dict[str, str] = {}

        for test_name, single_test_src in granular_tests:
            executed_lines, passed, err_msg = self._run_single_test_spectrum(
                source_code, single_test_src, max_source_line, target_filename=target_filename
            )
            if passed:
                passed_count += 1
                for ln in executed_lines:
                    ep_counts[ln] = ep_counts.get(ln, 0) + 1
            else:
                failed_count += 1
                failing_errors[test_name] = err_msg
                for ln in executed_lines:
                    ef_counts[ln] = ef_counts.get(ln, 0) + 1

        ranked: List[LineSpectrumRank] = []
        for ln in range(1, max_source_line + 1):
            raw_line = source_lines[ln - 1].strip()
            if not raw_line or raw_line.startswith("#"):
                continue

            ef = ef_counts.get(ln, 0)
            ep = ep_counts.get(ln, 0)
            if ef == 0 and ep == 0:
                continue

            nf = failed_count - ef
            np_val = passed_count - ep

            # Ochiai Formula: ef / sqrt((ef + nf) * (ef + ep))
            denom = math.sqrt((ef + nf) * (ef + ep))
            ochiai = round(ef / denom, 4) if denom > 0.0 else 0.0

            # Tarantula Formula for secondary tie-breaking
            fail_ratio = (ef / failed_count) if failed_count > 0 else 0.0
            pass_ratio = (ep / passed_count) if passed_count > 0 else 0.0
            t_denom = fail_ratio + pass_ratio
            tarantula = round(fail_ratio / t_denom, 4) if t_denom > 0.0 else 0.0

            node_type = mapper.line_to_node_type.get(ln, "Expression")
            ranked.append(
                LineSpectrumRank(
                    lineno=ln,
                    ochiai_score=ochiai,
                    tarantula_score=tarantula,
                    ef=ef,
                    nf=nf,
                    ep=ep,
                    np=np_val,
                    enclosing_scope=mapper.line_to_scope.get(ln, "<module>"),
                    ast_node_type=node_type,
                    source_line=raw_line,
                )
            )

        # Sort by highest Ochiai score, then prefer executable body statements over FunctionDef headers
        ranked.sort(
            key=lambda item: (
                item.ochiai_score,
                item.tarantula_score,
                0 if item.ast_node_type in ("FunctionDef", "AsyncFunctionDef", "ClassDef") else 1,
                item.lineno,
            ),
            reverse=True,
        )

        return FaultLocalizationReport(
            total_tests=len(granular_tests),
            passed_tests=passed_count,
            failed_tests=failed_count,
            ranked_lines=ranked[:top_k],
            failing_test_errors=failing_errors,
        )

    @staticmethod
    def _run_single_test_spectrum(
        source_code: str,
        single_test_src: str,
        max_source_line: int,
        target_filename: str = "<apex_ochiai_target>",
    ) -> Tuple[Set[int], bool, str]:
        import os
        full_script = f"{source_code}\n\n{single_test_src}\n"
        compiled = compile(full_script, target_filename, "exec")
        covered_lines: Set[int] = set()
        target_base = os.path.basename(target_filename)
        target_abs = os.path.abspath(target_filename)

        def line_tracer(frame: types.FrameType, event: str, arg: Any) -> Callable[..., Any]:
            if event == "line":
                fname = frame.f_code.co_filename
                if (
                    fname == target_filename
                    or fname == "<apex_ochiai_target>"
                    or os.path.abspath(fname) == target_abs
                    or os.path.normcase(os.path.basename(fname)) == os.path.normcase(target_base)
                ):
                    if 1 <= frame.f_lineno <= max_source_line:
                        covered_lines.add(frame.f_lineno)
            return line_tracer

        env: Dict[str, Any] = {"__name__": "__apex_ochiai__"}
        sys.settrace(line_tracer)
        try:
            exec(compiled, env, env)
            sys.settrace(None)
            return covered_lines, True, ""
        except Exception as exc:
            sys.settrace(None)
            return covered_lines, False, f"{type(exc).__name__}: {exc}"

    def trace_execution(self, source_code: str, test_code: str, module_name: str = "solution") -> bool:
        """Compatibility method for legacy callers."""
        report = self.localize(source_code, test_code, target_filename=module_name)
        self.source_cache[module_name] = source_code.splitlines()
        failing_lines = set()
        passing_lines = set()
        for r in report.ranked_lines:
            if r.ef > 0:
                failing_lines.add((module_name, r.lineno))
            if r.ep > 0:
                passing_lines.add((module_name, r.lineno))
        if failing_lines:
            self.failing_runs.append(failing_lines)
        if passing_lines:
            self.passing_runs.append(passing_lines)
        return report.failed_tests == 0

    def rank_suspicious_statements(self) -> List[SuspiciousStatement]:
        """Compatibility method returning legacy SuspiciousStatement instances."""
        if not self.failing_runs:
            return []
        total_failed = len(self.failing_runs)
        total_passed = len(self.passing_runs)
        all_statements: Set[Tuple[str, int]] = set()
        for run in self.failing_runs:
            all_statements.update(run)
        for run in self.passing_runs:
            all_statements.update(run)

        ranked: List[SuspiciousStatement] = []
        for f_path, l_num in all_statements:
            ef = sum(1 for run in self.failing_runs if (f_path, l_num) in run)
            nf = total_failed - ef
            ep = sum(1 for run in self.passing_runs if (f_path, l_num) in run)
            denom = math.sqrt((ef + nf) * (ef + ep))
            ochiai = (ef / denom) if denom > 0 else 0.0

            src_line = ""
            if f_path in self.source_cache:
                lines = self.source_cache[f_path]
                if 1 <= l_num <= len(lines):
                    src_line = lines[l_num - 1]

            ranked.append(
                SuspiciousStatement(
                    file_path=f_path,
                    line_number=l_num,
                    suspiciousness=ochiai,
                    failed_executions=ef,
                    passed_executions=ep,
                    source_code=src_line,
                )
            )
        ranked.sort(key=lambda s: (s.suspiciousness, s.failed_executions), reverse=True)
        return ranked


if __name__ == "__main__":
    sample_buggy_module = """
def calculate_billing_tier(usage_gb, is_enterprise):
    if usage_gb < 0:
        raise ValueError("Usage cannot be negative")
    if is_enterprise:
        if usage_gb > 1000:
            return usage_gb * 2.0  # BUG ON LINE 7: Should be usage_gb * 0.85 discount rate
        return usage_gb * 1.0
    if usage_gb > 100:
        return usage_gb * 1.5
    return usage_gb * 1.25
""".strip()

    sample_test_suite = """
def test_negative_guard():
    try:
        calculate_billing_tier(-5, False)
        assert False
    except ValueError:
        assert True

def test_standard_low_tier():
    assert calculate_billing_tier(50, False) == 62.5

def test_standard_high_tier():
    assert calculate_billing_tier(200, False) == 300.0

def test_enterprise_normal_tier():
    assert calculate_billing_tier(500, True) == 500.0

def test_enterprise_bulk_discount_1():
    assert calculate_billing_tier(2000, True) == 1700.0

def test_enterprise_bulk_discount_2():
    assert calculate_billing_tier(1500, True) == 1275.0
""".strip()

    localizer = OchiaiFaultLocalizer()
    report = localizer.localize(sample_buggy_module, sample_test_suite, top_k=6)

    print("=" * 88)
    print(" APEX-SOVEREIGN: OCHIAI SPECTRUM-BASED FAULT LOCALIZATION (LIVE VERIFICATION)")
    print("=" * 88)
    print(
        f" Tests Executed: {report.total_tests} | Passed: {report.passed_tests} | Failed: {report.failed_tests}\n"
    )
    print(f" {'RANK':<5} {'LINE':<5} {'OCHIAI':<8} {'TARANTULA':<10} {'(ef,nf,ep,np)':<15} {'AST NODE':<13} {'SOURCE CODE'}")
    print("-" * 88)

    for rank_idx, item in enumerate(report.ranked_lines, start=1):
        spectrum_tuple = f"({item.ef},{item.nf},{item.ep},{item.np})"
        print(
            f" #{rank_idx:<4} L{item.lineno:<4} {item.ochiai_score:<8.4f} {item.tarantula_score:<10.4f} "
            f"{spectrum_tuple:<15} {item.ast_node_type:<13} {item.source_line}"
        )

    top_hit = report.ranked_lines[0]
    assert top_hit.lineno == 6, f"Expected buggy line 6 to rank #1, got line {top_hit.lineno}"
    assert top_hit.ochiai_score == 1.0, f"Expected Ochiai score 1.0, got {top_hit.ochiai_score}"
    print("\n[SUCCESS] Exact buggy line L6 isolated at Rank #1 with Ochiai Score = 1.0000.")
