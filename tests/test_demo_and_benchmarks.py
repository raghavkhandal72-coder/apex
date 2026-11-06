#!/usr/bin/env python3
"""
Unit tests for Apex Live Demo, Micro-Benchmark, and Code Review engines.
100% Pure Python Standard Library (pip = 0).
"""

from __future__ import annotations

import unittest
from apex_council.ui.demo_engine import run_live_demo
from apex_council.ui.benchmark_engine import run_benchmark_suite, _bench_ast_mutation, _bench_swift_guard
from apex_council.ui.review_engine import run_code_review, render_colorized_diff


class TestDemoAndBenchmarks(unittest.TestCase):
    def test_live_demo_runs_successfully(self) -> None:
        """Verify the 5-stage live inductive program repair walkthrough passes."""
        rc = run_live_demo(animated=False)
        self.assertEqual(rc, 0)

    def test_benchmark_suite_runs_successfully(self) -> None:
        """Verify the runtime micro-benchmark suite executes cleanly."""
        rc = run_benchmark_suite()
        self.assertEqual(rc, 0)

    def test_micro_benchmarks_return_valid_metrics(self) -> None:
        """Verify individual micro-benchmarks compute valid throughput and latency."""
        ast_res = _bench_ast_mutation(iterations=50)
        self.assertGreater(ast_res["ops_sec"], 0)
        self.assertGreater(ast_res["mean_ms"], 0)

        swift_res = _bench_swift_guard(iterations=50)
        self.assertGreater(swift_res["ops_sec"], 0)

    def test_code_review_runs_successfully(self) -> None:
        """Verify autonomous code review executes on workspace without error."""
        rc = run_code_review("main.py")
        self.assertEqual(rc, 0)

    def test_colorized_diff_returns_string(self) -> None:
        """Verify render_colorized_diff returns non-empty formatted output."""
        diff = render_colorized_diff(".")
        self.assertIsInstance(diff, str)
        self.assertGreater(len(diff), 0)


if __name__ == "__main__":
    unittest.main()
