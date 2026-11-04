"""Apex-Sovereign: Unified Spectrum-Based Fault Localization (SBFL) Triad Engine.
100% Pure Python Standard Library | Zero External Dependencies | Zero Mocks.

Mathematical Foundations:
1. Ochiai Metric (Abreu et al., 2007; adapted from molecular biology):
   Ochiai(s) = e_f / sqrt((e_f + n_f) * (e_f + e_p))
2. Tarantula Metric (Jones & Harrold, 2005):
   Tarantula(s) = (e_f / (e_f + n_f)) / ((e_f / (e_f + n_f)) + (e_p / (e_p + n_p)))
3. Wong-II / DStar (D*) Metric (Wong et al., IEEE Trans. Reliability, 2014):
   DStar(s) = (e_f ^ star) / (e_p + n_f)  [Default star = 2.0]
4. Unified Ensemble Score:
   Ensemble(s) = w_dstar * DStar_norm(s) + w_ochiai * Ochiai(s) + w_tarantula * Tarantula(s)
"""

from __future__ import annotations

import ast
import dataclasses
import math
import sys
import types
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class SBFLSpectrumMetric:
    lineno: int
    ochiai: float
    tarantula: float
    dstar: float
    ensemble: float
    ef: int  # Failing tests executing this line
    nf: int  # Failing tests NOT executing this line
    ep: int  # Passing tests executing this line
    np: int  # Passing tests NOT executing this line
    enclosing_scope: str
    ast_node_type: str
    source_line: str


@dataclasses.dataclass(frozen=True)
class SBFLTriadReport:
    total_tests: int
    passed_tests: int
    failed_tests: int
    star_exponent: float
    ranked_lines: List[SBFLSpectrumMetric]
    top_suspicious_line: Optional[int]
    consensus_confidence: float  # 0.0 to 1.0


class _ScopeAndNodeVisitor(ast.NodeVisitor):
    """Maps line numbers to AST node types and enclosing function/class scopes."""

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


class SBFLTriadEngine:
    """Unified Fault Localizer computing the triad of Ochiai, Tarantula, and DStar."""

    def __init__(
        self,
        star_exponent: float = 2.0,
        w_dstar: float = 0.50,
        w_ochiai: float = 0.35,
        w_tarantula: float = 0.15,
    ) -> None:
        self.star_exponent = star_exponent
        self.w_dstar = w_dstar
        self.w_ochiai = w_ochiai
        self.w_tarantula = w_tarantula

    @classmethod
    def compute_ochiai(cls, ef: int, nf: int, ep: int, np: int) -> float:
        """Ochiai(s) = ef / sqrt((ef + nf) * (ef + ep))"""
        total_failing = ef + nf
        executed = ef + ep
        denom = math.sqrt(total_failing * executed)
        return (ef / denom) if denom > 0.0 else 0.0

    @classmethod
    def compute_tarantula(cls, ef: int, nf: int, ep: int, np: int) -> float:
        """Tarantula(s) = (ef / (ef + nf)) / ((ef / (ef + nf)) + (ep / (ep + np)))"""
        total_failing = ef + nf
        total_passing = ep + np
        fail_ratio = (ef / total_failing) if total_failing > 0 else 0.0
        pass_ratio = (ep / total_passing) if total_passing > 0 else 0.0
        denom = fail_ratio + pass_ratio
        return (fail_ratio / denom) if denom > 0.0 else 0.0

    @classmethod
    def compute_dstar(cls, ef: int, nf: int, ep: int, np: int, star: float = 2.0) -> float:
        """DStar(s) = (ef ^ star) / (ep + nf)"""
        denom = ep + nf
        if denom == 0:
            return float(ef**star) if ef > 0 else 0.0
        return float(ef**star) / float(denom)

    def localize(
        self,
        source_code: str,
        test_code: str,
        target_filename: str = "<apex_target>",
    ) -> SBFLTriadReport:
        """
        Executes individual assertion tests under line tracing,
        accumulates execution spectra, and returns multi-formula ranking.
        """
        source_lines = source_code.splitlines()

        # Build AST line scope map
        visitor = _ScopeAndNodeVisitor()
        try:
            tree = ast.parse(source_code, filename=target_filename)
            visitor.visit(tree)
        except SyntaxError:
            pass

        # Split test harness into individual executable units
        test_units: List[str] = []
        try:
            test_tree = ast.parse(test_code, filename="<tests>")
            for node in test_tree.body:
                if isinstance(node, (ast.Assert, ast.Expr, ast.FunctionDef)):
                    test_units.append(ast.unparse(node))
        except Exception:
            test_units = [line.strip() for line in test_code.splitlines() if line.strip() and not line.strip().startswith("#")]

        if not test_units:
            test_units = [test_code]

        passing_spectra: List[Set[int]] = []
        failing_spectra: List[Set[int]] = []

        for unit in test_units:
            covered_lines, passed = self._trace_unit(source_code, unit, target_filename)
            if passed:
                passing_spectra.append(covered_lines)
            else:
                failing_spectra.append(covered_lines)

        total_p = len(passing_spectra)
        total_f = len(failing_spectra)
        all_executed_lines: Set[int] = set()
        for s in passing_spectra:
            all_executed_lines.update(s)
        for s in failing_spectra:
            all_executed_lines.update(s)

        raw_metrics: List[Dict[str, Any]] = []
        max_dstar = 1e-7

        for ln in all_executed_lines:
            ef = sum(1 for s in failing_spectra if ln in s)
            nf = total_f - ef
            ep = sum(1 for s in passing_spectra if ln in s)
            np = total_p - ep

            ochiai = self.compute_ochiai(ef, nf, ep, np)
            tarantula = self.compute_tarantula(ef, nf, ep, np)
            dstar = self.compute_dstar(ef, nf, ep, np, star=self.star_exponent)
            if dstar > max_dstar:
                max_dstar = dstar

            scope = visitor.line_to_scope.get(ln, "<module>")
            node_type = visitor.line_to_node_type.get(ln, "Statement")
            src = source_lines[ln - 1] if 1 <= ln <= len(source_lines) else ""

            raw_metrics.append({
                "lineno": ln,
                "ochiai": ochiai,
                "tarantula": tarantula,
                "dstar": dstar,
                "ef": ef,
                "nf": nf,
                "ep": ep,
                "np": np,
                "scope": scope,
                "node_type": node_type,
                "source": src,
            })

        # Normalize DStar and compute weighted ensemble
        ranked_metrics: List[SBFLSpectrumMetric] = []
        for rm in raw_metrics:
            norm_dstar = (rm["dstar"] / max_dstar) if max_dstar > 0.0 else 0.0
            ensemble = (
                self.w_dstar * norm_dstar
                + self.w_ochiai * rm["ochiai"]
                + self.w_tarantula * rm["tarantula"]
            )
            ranked_metrics.append(
                SBFLSpectrumMetric(
                    lineno=rm["lineno"],
                    ochiai=round(rm["ochiai"], 4),
                    tarantula=round(rm["tarantula"], 4),
                    dstar=round(rm["dstar"], 4),
                    ensemble=round(ensemble, 4),
                    ef=rm["ef"],
                    nf=rm["nf"],
                    ep=rm["ep"],
                    np=rm["np"],
                    enclosing_scope=rm["scope"],
                    ast_node_type=rm["node_type"],
                    source_line=rm["source"],
                )
            )

        ranked_metrics.sort(key=lambda m: (m.ensemble, m.ochiai, m.ef), reverse=True)
        top_line = ranked_metrics[0].lineno if ranked_metrics else None

        # Compute consensus confidence (how strongly the top line agrees across metrics)
        confidence = 0.0
        if ranked_metrics:
            top = ranked_metrics[0]
            confidence = (top.ochiai + top.tarantula + (top.dstar / max_dstar)) / 3.0

        return SBFLTriadReport(
            total_tests=total_p + total_f,
            passed_tests=total_p,
            failed_tests=total_f,
            star_exponent=self.star_exponent,
            ranked_lines=ranked_metrics,
            top_suspicious_line=top_line,
            consensus_confidence=round(min(1.0, max(0.0, confidence)), 4),
        )

    def _trace_unit(
        self,
        source_code: str,
        test_unit: str,
        target_filename: str,
    ) -> Tuple[Set[int], bool]:
        """Traces execution of a single unit test against source code."""
        covered: Set[int] = set()

        def tracer(frame: types.FrameType, event: str, arg: Any) -> Any:
            if event == "line":
                fname = frame.f_code.co_filename
                if fname == target_filename:
                    covered.add(frame.f_lineno)
            return tracer

        combined = f"{source_code}\n\n# --- UNIT TEST ---\n{test_unit}"
        env: Dict[str, Any] = {"__name__": "__apex_sbfl__"}

        try:
            compiled = compile(combined, target_filename, "exec")
        except Exception:
            return covered, False

        old_trace = sys.gettrace()
        sys.settrace(tracer)
        passed = False
        try:
            exec(compiled, env, env)
            passed = True
        except Exception:
            passed = False
        finally:
            sys.settrace(old_trace)

        return covered, passed
