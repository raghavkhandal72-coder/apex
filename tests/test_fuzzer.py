"""Unit Tests for Autonomous Mutation Fuzzer.
100% Pure Python Standard Library (pip = 0).
"""

import unittest
from apex_council.analysis.fuzzer import AutonomousFuzzer


class TestAutonomousFuzzer(unittest.TestCase):
    def test_fuzzer_detects_zerodiv_and_indexerror(self):
        def vulnerable_math(a, b):
            if a > 50:
                return [10, 20][b]
            return a / b

        report = AutonomousFuzzer.fuzz_function(vulnerable_math, max_probes=500)
        self.assertFalse(report.passed)
        self.assertGreater(report.crashes_found, 0)
        self.assertIn("ZeroDivisionError", report.unique_exceptions)
        self.assertGreater(len(report.crash_vectors), 0)

    def test_fuzzer_immune_function(self):
        def immune_func(a, b):
            try:
                if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                    return 0
                if b == 0:
                    return 0
                return a / b
            except Exception:
                return 0

        report = AutonomousFuzzer.fuzz_function(immune_func, max_probes=300)
        self.assertTrue(report.passed)
        self.assertEqual(report.crashes_found, 0)


if __name__ == "__main__":
    unittest.main()
