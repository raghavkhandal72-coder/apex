import unittest

from apex_council.search.mcts import MCTSEngine
from apex_council.search.transposition import ASTTranspositionTable


class TestTranspositionAndPUCT(unittest.TestCase):
    def test_transposition_table_ast_caching(self) -> None:
        table = ASTTranspositionTable(max_entries=10)
        code1 = "def add(x, y): return x + y"
        code2 = "def add(a, b): return a + b"  # Renamed args, identical AST!

        table.store(code1, score=1.0, details={"status": "PASS"})

        # Lookup with code2 should hit cache
        res = table.lookup(code2)
        self.assertIsNotNone(res)
        score, details = res
        self.assertEqual(score, 1.0)
        self.assertEqual(table.hits, 1)
        self.assertEqual(table.hit_ratio, 1.0)

    def test_mcts_mdl_tie_breaker(self) -> None:
        broken_code = "def solve(): return 0"
        test_harness = "assert solve() == 42"

        # Generator returns two passing candidates:
        # 1. Bloated passing solution (long code)
        # 2. Concise passing solution (short code)
        def multi_pass_gen(state: str, action: str) -> list[str]:
            return [
                "def solve():\n    # Bloated comment\n    a = 10\n    b = 32\n    return a + b",
                "def solve(): return 42",
            ]

        engine = MCTSEngine(
            task_prompt="Return 42",
            test_code=test_harness,
            generator_fn=multi_pass_gen,
            iterations=2,
        )
        res = engine.search(initial_code=broken_code, iterations=2)
        self.assertTrue(res.is_verified_passing)
        # MDL should select the concise implementation
        self.assertEqual(res.best_code.strip(), "def solve(): return 42")


if __name__ == "__main__":
    unittest.main()
