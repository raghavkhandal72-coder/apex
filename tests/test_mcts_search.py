import unittest

from apex_council.search.mcts import MCTSEngine, MCTSNode


class TestMCTSSearch(unittest.TestCase):
    def test_immediate_pass(self) -> None:
        passing_code = "def multiply(a, b): return a * b"
        test_harness = "assert multiply(3, 4) == 12"

        def dummy_gen(state: str, action: str) -> list[str]:
            return [state]

        engine = MCTSEngine(
            task_prompt="Multiply two numbers",
            test_code=test_harness,
            generator_fn=dummy_gen,
        )
        res = engine.search(initial_code=passing_code, iterations=3)
        self.assertTrue(res.is_verified_passing)
        self.assertEqual(res.best_score, 1.0)
        self.assertEqual(res.total_nodes_explored, 1)

    def test_mcts_exploration_and_convergence(self) -> None:
        broken_code = "def divide(a, b): return a + b"  # Buggy!
        test_harness = "assert divide(10, 2) == 5"

        # Generator produces 3 candidates:
        # 1. Still buggy (returns a - b)
        # 2. Syntax error
        # 3. Correct fix (returns a // b)
        def mock_generator(state: str, action: str) -> list[str]:
            return [
                "def divide(a, b): return a - b",
                "def divide(a, b): return a / / b",  # syntax error
                "def divide(a, b): return a // b",   # correct
            ]

        engine = MCTSEngine(
            task_prompt="Fix divide function",
            test_code=test_harness,
            generator_fn=mock_generator,
            iterations=2,
        )
        res = engine.search(initial_code=broken_code, iterations=2)
        self.assertTrue(res.is_verified_passing)
        self.assertEqual(res.best_score, 1.0)
        self.assertIn("return a // b", res.best_code)
        self.assertGreaterEqual(res.total_nodes_explored, 2)

    def test_ast_bomb_pruning(self) -> None:
        initial_code = "def process(): return False"
        test_harness = "assert process() is True"

        # Generator generates an exploit attempt with deep recursion
        def exploit_generator(state: str, action: str) -> list[str]:
            bomb = "f(" * 300 + "1" + ")" * 300
            return [bomb]

        engine = MCTSEngine(
            task_prompt="Test pruning",
            test_code=test_harness,
            generator_fn=exploit_generator,
            iterations=1,
        )
        res = engine.search(initial_code=initial_code, iterations=1)
        self.assertGreater(res.pruned_branches, 0)
        self.assertFalse(res.is_verified_passing)

    def test_ephemeral_worktree_lifecycle(self) -> None:
        import tempfile
        from pathlib import Path
        from apex_council.search.worktree import EphemeralWorktreePool

        with tempfile.TemporaryDirectory() as base_repo:
            p = Path(base_repo)
            (p / "main.py").write_text("print('hello')", encoding="utf-8")

            pool = EphemeralWorktreePool(p)
            captured_wt_path = None
            with pool.acquire_worktree("test_branch") as wt_path:
                captured_wt_path = wt_path
                self.assertTrue(wt_path.exists())
                self.assertTrue((wt_path / "main.py").exists())
                # Create a file in worktree
                (wt_path / "patch.txt").write_text("mod", encoding="utf-8")
                self.assertTrue((wt_path / "patch.txt").exists())
                # Base repo must NOT have patch.txt
                self.assertFalse((p / "patch.txt").exists())

            # After exit, worktree should be cleaned up
            self.assertFalse(captured_wt_path.exists())

    def test_semantic_ast_crossover(self) -> None:
        from apex_council.search.crossover import SemanticASTCrossover

        code_a = """
def parse_payload(raw):
    if not raw: return {}
    return {'data': raw}
"""
        code_b = """
def format_output(parsed):
    return str(parsed)
"""
        res = SemanticASTCrossover.cross_synthesize(code_a, code_b)
        self.assertIn("parse_payload", res.merged_code)
        self.assertIn("format_output", res.merged_code)
        self.assertEqual(res.crossover_type, "AST_HYBRID_CROSSOVER")


if __name__ == "__main__":
    unittest.main()
