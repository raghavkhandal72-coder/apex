"""Spectrum-Based Fault Localization (SBFL) via Ochiai Coefficient.
Uses sys.settrace to track statement execution across passing and failing test executions
and pinpoints suspicious buggy lines with mathematical precision.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import math
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple


@dataclass
class SuspiciousStatement:
    filepath: str
    line_number: int
    ochiai_score: float  # 0.0 to 1.0
    failed_executions: int
    passed_executions: int
    source_snippet: str = ""


class OchiaiFaultLocalizer:
    """Computes statement suspiciousness using the standard Ochiai fault localization metric."""

    def __init__(self, target_files: Optional[List[str]] = None) -> None:
        self.target_files = set(str(Path(f).resolve()) for f in (target_files or []))
        # statement -> (failed_count, passed_count)
        # statement is (filepath, lineno)
        self.statement_failed: Dict[Tuple[str, int], int] = {}
        self.statement_passed: Dict[Tuple[str, int], int] = {}
        self.total_failed_tests: int = 0
        self.total_passed_tests: int = 0

    def trace_test_execution(self, test_callable: Callable[[], None]) -> Tuple[bool, Set[Tuple[str, int]]]:
        """Runs test_callable under sys.settrace to collect executed line statements.
        Returns: (passed: bool, executed_statements: Set[(filepath, lineno)])
        """
        executed: Set[Tuple[str, int]] = set()

        def tracer(frame: types.FrameType, event: str, arg: object) -> Optional[Callable]:
            if event == "line":
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno
                # Normalize path
                norm_file = str(Path(filename).resolve())
                if not self.target_files or norm_file in self.target_files:
                    executed.add((norm_file, lineno))
            return tracer

        old_trace = sys.gettrace()
        passed = False
        try:
            sys.settrace(tracer)
            test_callable()
            passed = True
        except Exception:
            passed = False
        finally:
            sys.settrace(old_trace)

        # Update spectra
        if passed:
            self.total_passed_tests += 1
            for stmt in executed:
                self.statement_passed[stmt] = self.statement_passed.get(stmt, 0) + 1
        else:
            self.total_failed_tests += 1
            for stmt in executed:
                self.statement_failed[stmt] = self.statement_failed.get(stmt, 0) + 1

        return passed, executed

    def compute_ochiai_scores(self) -> List[SuspiciousStatement]:
        """Computes Ochiai ranking:
        Ochiai(s) = failed(s) / sqrt(total_failed * (failed(s) + passed(s)))
        """
        if self.total_failed_tests == 0:
            return []

        all_statements = set(self.statement_failed.keys()) | set(self.statement_passed.keys())
        results: List[SuspiciousStatement] = []

        for filepath, lineno in all_statements:
            n_cf = self.statement_failed.get((filepath, lineno), 0)
            n_cp = self.statement_passed.get((filepath, lineno), 0)

            denominator = math.sqrt(self.total_failed_tests * (n_cf + n_cp))
            if denominator == 0.0:
                score = 0.0
            else:
                score = n_cf / denominator

            snippet = ""
            try:
                p = Path(filepath)
                if p.exists():
                    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                    if 1 <= lineno <= len(lines):
                        snippet = lines[lineno - 1].strip()
            except Exception:
                pass

            results.append(
                SuspiciousStatement(
                    filepath=filepath,
                    line_number=lineno,
                    ochiai_score=round(score, 4),
                    failed_executions=n_cf,
                    passed_executions=n_cp,
                    source_snippet=snippet,
                )
            )

        # Sort by suspiciousness score descending
        results.sort(key=lambda s: (s.ochiai_score, s.failed_executions), reverse=True)
        return results
