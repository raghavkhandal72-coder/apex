"""Tests for Apex Formal Mathematical Safety & Invariant Prover."""

import unittest
from pathlib import Path

from apex_council.formal.prover import FormalSafetyProver, handle_prove_cli


class TestFormalSafetyProver(unittest.TestCase):
    def test_safe_program_proves_clean(self):
        code = """
def safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b
"""
        rep = FormalSafetyProver.prove_source(code, filename="safe.py")
        self.assertIn("proof_certificate_hash", rep)
        self.assertEqual(len(rep["proof_certificate_hash"]), 64)

    def test_unsafe_zero_division_detected(self):
        code = """
def crash_div(x: int, y: int) -> float:
    return x / y
"""
        rep = FormalSafetyProver.prove_source(code, filename="unsafe.py")
        self.assertFalse(rep["is_provably_safe"])
        self.assertTrue(len(rep["hoare_violations"]) > 0)
        self.assertEqual(rep["hoare_violations"][0]["category"], "ZERO_DIVISION_RISK")

    def test_handle_prove_cli_help(self):
        exit_code = handle_prove_cli(["--help"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
