import unittest

from apex_council.autopsy.bytecode_inspector import BytecodeAutopsyReport
from apex_council.security.safe_exec import safe_exec
from apex_council.synthesis.ast_synthesizer import DeterministicASTSynthesizer


class TestPhase3ASTSynthesizer(unittest.TestCase):
    def test_synthesizer_repairs_mutable_default(self) -> None:
        buggy_code = """
def append_value(val, target_list=[]):
    target_list.append(val)
    return target_list
"""
        candidates = DeterministicASTSynthesizer.synthesize_repairs(buggy_code)
        self.assertGreater(len(candidates), 0)

        # Check candidate code
        repair = [c for c in candidates if c.repair_strategy == "MutableDefaultGuard"][0]
        self.assertIn("target_list=None", repair.candidate_code)
        self.assertIn("if target_list is None:", repair.candidate_code)

        # Verify executing candidate fixes state leakage
        scope: dict = {}
        safe_exec(repair.candidate_code, scope)
        fn = scope["append_value"]
        r1 = fn(1)
        r2 = fn(2)
        self.assertEqual(r1, [1])
        self.assertEqual(r2, [2])  # Does not leak [1, 2]!

    def test_synthesizer_repairs_operator_inversion(self) -> None:
        buggy_mult = """
def multiply(a, b):
    return a + b
"""
        candidates = DeterministicASTSynthesizer.synthesize_repairs(buggy_mult, suspicious_lines=[3])
        repairs = [c for c in candidates if "OperatorInversion" in c.repair_strategy]
        self.assertGreater(len(repairs), 0)

        # Find multiplication repair
        mult_cands = [c for c in repairs if "Mult" in c.repair_strategy]
        self.assertGreater(len(mult_cands), 0)
        self.assertIn("return a * b", mult_cands[0].candidate_code)

        scope: dict = {}
        safe_exec(mult_cands[0].candidate_code, scope)
        self.assertEqual(scope["multiply"](3, 4), 12)

    def test_synthesizer_repairs_boundary_relational(self) -> None:
        buggy_comp = """
def check_limit(val, limit):
    return val <= limit
"""
        candidates = DeterministicASTSynthesizer.synthesize_repairs(buggy_comp, suspicious_lines=[3])
        bound_cands = [c for c in candidates if c.repair_strategy == "BoundaryRelationalInversion"]
        self.assertGreater(len(bound_cands), 0)
        self.assertIn("val < limit", bound_cands[0].candidate_code)


if __name__ == "__main__":
    unittest.main()
