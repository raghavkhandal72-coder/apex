import unittest

from apex_council.security.fuzzer import ConcurrencyStressTester, PropertyFuzzer
from apex_council.security.ledger import CryptographicLedger, MerkleTreeAttestor
from apex_council.security.mutator import ASTMutationEngine
from apex_council.security.sandbox import HermeticExecutionSandbox
from apex_council.security.scanner import SovereignSecurityScanner


class TestPhase5SecurityAndMutation(unittest.TestCase):
    def test_pep578_audit_hook_blocks_forbidden_actions(self) -> None:
        malicious_code = """
import socket
s = socket.socket()
s.connect(("1.1.1.1", 80))
"""
        passed, _, output = HermeticExecutionSandbox.execute_isolated(malicious_code)
        self.assertFalse(passed)
        self.assertIn("APEX-PEP578-BLOCK", output)

    def test_ast_mutation_testing_engine(self) -> None:
        code = "def add(a, b): return a + b"
        strong_tests = "assert add(2, 3) == 5\nassert add(-1, 1) == 0"
        report = ASTMutationEngine.evaluate_test_suite_rigor(code, strong_tests)
        self.assertGreater(report.total_mutants, 0)
        self.assertEqual(report.killed_mutants, report.total_mutants)
        self.assertEqual(report.mutation_score, 100.0)

    def test_property_fuzzer_and_scanner(self) -> None:
        findings = SovereignSecurityScanner.scan_code("TOKEN = 'AKIA1234567890ABCDEF'")
        self.assertTrue(any(f.category == "SECRET_LEAK" for f in findings))

    def test_merkle_attestation(self) -> None:
        leaves = ["hash1", "hash2", "hash3"]
        root = MerkleTreeAttestor.compute_merkle_root(leaves)
        self.assertEqual(len(root), 64)


if __name__ == "__main__":
    unittest.main()
