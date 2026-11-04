import unittest

from apex_council.security.mutator import ASTMutationEngine


class TestASTMutationEngine(unittest.TestCase):
    def test_count_and_generate_mutations(self) -> None:
        code = """
def evaluate(x, y):
    return (x + y) == 10 and True
"""
        count = ASTMutationEngine.count_possible_mutations(code)
        self.assertGreaterEqual(count, 3)  # + (BinOp), == (Compare), True (Bool)

        mutants = ASTMutationEngine.generate_mutants(code)
        self.assertGreaterEqual(len(mutants), 3)

        op_types = {m.operator_type for m in mutants}
        self.assertIn("BIN_OP", op_types)
        self.assertIn("COMPARE_OP", op_types)
        self.assertIn("BOOLEAN_FLIP", op_types)

    def test_strong_test_suite_kills_all_mutants(self) -> None:
        code = """
def multiply(a, b):
    return a * b
"""
        # Strong test asserts exact mathematical output
        strong_test = """
assert multiply(2, 3) == 6
assert multiply(4, 5) == 20
assert multiply(10, 0) == 0
"""
        report = ASTMutationEngine.evaluate_test_suite_rigor(code, strong_test)
        self.assertGreater(report.total_mutants, 0)
        self.assertEqual(report.killed_mutants, report.total_mutants)
        self.assertEqual(report.mutation_score, 100.0)
        self.assertTrue(report.is_airtight)

    def test_weak_test_suite_allows_mutants_to_survive(self) -> None:
        code = """
def compute(a, b):
    return a + b
"""
        # Weak test only checks type/not None, so mutant (a - b) still survives!
        weak_test = """
res = compute(5, 5)
assert isinstance(res, int)
assert res is not None
"""
        report = ASTMutationEngine.evaluate_test_suite_rigor(code, weak_test)
        self.assertGreater(report.total_mutants, 0)
        # Mutant return a - b also returns an int, so it survives!
        self.assertGreater(report.survived_mutants, 0)
        self.assertFalse(report.is_airtight)


if __name__ == "__main__":
    unittest.main()
