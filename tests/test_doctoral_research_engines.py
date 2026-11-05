"""Unit tests for Apex-Sovereign Doctoral Research Breakthrough Engines.
100% Pure Python Standard Library | Zero Dependencies | Zero Mocks.
"""

import unittest

from apex_council.formal.abstract_interpreter import ASTAbstractInterpreter, Interval
from apex_council.graph.cfg_dominator import CFGDominatorEngine
from apex_council.search.solomonoff_prior import LZWCompressor, SolomonoffPriorEngine
from apex_council.synthesis.cegis_engine import CEGISEngine


class TestDoctoralResearchEngines(unittest.TestCase):
    def test_cfg_dominator_lengauer_tarjan_natural_loop(self) -> None:
        code = (
            "def loop_function(n):\n"
            "    total = 0\n"
            "    i = 0\n"
            "    while i < n:\n"
            "        total += i\n"
            "        i += 1\n"
            "    return total\n"
        )
        report = CFGDominatorEngine.analyze_source(code)
        self.assertGreater(report.total_blocks, 3)
        self.assertGreater(report.total_edges, 3)
        self.assertGreaterEqual(len(report.natural_loops), 1)

        # Check natural loop properties
        nl = report.natural_loops[0]
        self.assertGreaterEqual(nl.header, 0)
        self.assertIn(nl.header, nl.body_blocks)
        self.assertIn(nl.back_edge_source, nl.body_blocks)

    def test_abstract_interpreter_interval_arithmetic(self) -> None:
        i1 = Interval(2.0, 5.0)
        i2 = Interval(3.0, 4.0)

        add_res = i1.add(i2)
        self.assertEqual(add_res.lower, 5.0)
        self.assertEqual(add_res.upper, 9.0)

        sub_res = i1.sub(i2)
        self.assertEqual(sub_res.lower, -2.0)
        self.assertEqual(sub_res.upper, 2.0)

        mul_res = i1.mul(i2)
        self.assertEqual(mul_res.lower, 6.0)
        self.assertEqual(mul_res.upper, 20.0)

        # Non-zero division
        div_res, has_zero = i1.div(i2)
        self.assertFalse(has_zero)
        self.assertAlmostEqual(div_res.lower, 0.5, places=2)
        self.assertAlmostEqual(div_res.upper, 1.67, places=2)

        # Division with zero
        i_zero = Interval(-1.0, 1.0)
        _, has_zero_flag = i1.div(i_zero)
        self.assertTrue(has_zero_flag)

    def test_abstract_interpreter_ast_safety_proof(self) -> None:
        safe_code = (
            "def calculate(x):\n"
            "    y = 10\n"
            "    if y > 0:\n"
            "        z = x / y\n"
            "    return z\n"
        )
        analyzer = ASTAbstractInterpreter()
        report = analyzer.analyze(safe_code)
        self.assertGreaterEqual(report.total_proofs, 1)
        self.assertEqual(report.zero_division_risks, 0)
        self.assertTrue(report.safety_proofs[0].is_provably_safe)

    def test_cegis_inductive_synthesis_loop(self) -> None:
        # Buggy implementation: subtracting instead of adding
        buggy_code = (
            "def add_pair(x):\n"
            "    return x - 2\n"
        )
        test_suite = "assert add_pair(5) == 7\n"

        def ground_truth_oracle(x: int) -> int:
            return x + 2

        engine = CEGISEngine(max_iterations=5)
        report = engine.synthesize_and_verify(
            initial_buggy_code=buggy_code,
            test_suite_code=test_suite,
            oracle_eval_fn=ground_truth_oracle,
            boundary_inputs=[0, 1, 5, 10, -5],
        )

        self.assertTrue(report.success)
        self.assertIn("+", report.synthesized_code)
        self.assertTrue(report.verification_certified)

    def test_solomonoff_prior_and_ncd_compression(self) -> None:
        engine = SolomonoffPriorEngine()

        code_simple = "def f(x): return x + 1"
        code_bloated = (
            "def f(x):\n"
            "    temp_var_one = 1\n"
            "    temp_var_two = temp_var_one\n"
            "    result_accumulator = x + temp_var_two\n"
            "    return result_accumulator\n"
        )

        rep_simple = engine.evaluate_program(code_simple)
        rep_bloated = engine.evaluate_program(code_bloated)

        self.assertGreater(rep_bloated.lzw_token_count, rep_simple.lzw_token_count)
        self.assertGreater(rep_bloated.compressed_bits, rep_simple.compressed_bits)

        # Occam's Razor preference: simple code must have strictly higher Solomonoff prior score
        self.assertGreater(rep_simple.solomonoff_prior_score, rep_bloated.solomonoff_prior_score)

        # Normalized Compression Distance (NCD)
        ncd_self = engine.compute_ncd(code_simple, code_simple)
        self.assertLess(ncd_self, 0.5)

        ncd_diff = engine.compute_ncd(code_simple, "import os; os.system('ls')")
        self.assertGreater(ncd_diff, 0.3)


if __name__ == "__main__":
    unittest.main()
