import unittest

from apex_council.search.sovereign_mcts import (
    AutonomousSDETTestAmplifier,
    SovereignMCTSEngine,
    _LineTargetedOperatorSynthesizer,
)
from apex_council.search.transposition_and_crossover import (
    ASTMetricsAndHashEngine,
    ASTTranspositionTable,
    BitmaskGeneticASTCrossover,
)
from apex_council.security.mutator import ASTMutationTestingGate


class TestPhase9SovereignMCTSAndSDET(unittest.TestCase):
    def test_canonical_alpha_hasher_and_mccabe(self) -> None:
        code_1 = "def compute(x, y):\n    return x + y\n"
        code_2 = "def compute(first, second):\n    return first + second\n"

        hash_1 = ASTMetricsAndHashEngine.compute_canonical_fingerprint(code_1)
        hash_2 = ASTMetricsAndHashEngine.compute_canonical_fingerprint(code_2)
        self.assertEqual(hash_1, hash_2)

        branchy_code = """
def route(data):
    if not data:
        return 0
    for x in data:
        if x > 5:
            pass
    return 1
"""
        mccabe, nodes, bytes_len = ASTMetricsAndHashEngine.compute_mdl_score(branchy_code)
        self.assertGreaterEqual(mccabe, 4)
        self.assertGreater(nodes, 10)
        self.assertGreater(bytes_len, 20)

    def test_ast_mutation_testing_gate_survivors(self) -> None:
        code = "def subtract(a, b):\n    return a - b\n"
        weak_test = "assert isinstance(subtract(5, 3), int)\n"
        report = ASTMutationTestingGate.evaluate_test_rigor(code, weak_test)
        self.assertFalse(report.is_airtight)
        self.assertGreater(report.survived_mutants, 0)

        strong_test = "assert subtract(5, 3) == 2\nassert subtract(0, 1) == -1\n"
        strong_report = ASTMutationTestingGate.evaluate_test_rigor(code, strong_test)
        self.assertTrue(strong_report.is_airtight)
        self.assertEqual(strong_report.mutation_score, 100.0)

    def test_autonomous_sdet_test_amplifier(self) -> None:
        oracle = "def add(a, b):\n    return a + b\n"
        weak_test = "assert add(1, 1) == 2\n"

        amplified_code, final_score = AutonomousSDETTestAmplifier.amplify_tests(
            oracle_code=oracle,
            initial_test_code=weak_test,
        )
        self.assertGreaterEqual(final_score, 90.0)
        self.assertIn("assert add(", amplified_code)

    def test_bitmask_genetic_ast_crossover(self) -> None:
        cand_a = "def part_a(): return 'A'\n"
        cand_b = "def part_b(): return 'B'\n"
        cross = BitmaskGeneticASTCrossover.cross_synthesize(cand_a, cand_b)
        self.assertIn("part_a", cross.merged_code)
        self.assertIn("part_b", cross.merged_code)
        self.assertEqual(cross.crossover_type, "AST_HYBRID_CROSSOVER")

    def test_sovereign_mcts_puct_convergence(self) -> None:
        broken_code = "def calculate(a, b):\n    return a * b\n"
        test_harness = "assert calculate(10, 2) == 12\n"

        def test_gen(state: str, action: str) -> list[str]:
            return [
                "def calculate(a, b):\n    return a - b\n",
                "def calculate(a, b):\n    return a + b\n",
            ]

        engine = SovereignMCTSEngine(
            task_prompt="Fix calculator addition",
            test_code=test_harness,
            generator_fn=test_gen,
            iterations=2,
        )
        res = engine.search(broken_code, iterations=2)
        self.assertTrue(res.is_verified_passing)
        self.assertEqual(res.best_score, 1.0)
        self.assertIn("return a + b", res.best_code)


if __name__ == "__main__":
    unittest.main()
