import subprocess
import tempfile
import unittest
from pathlib import Path

from apex_council.git_engine.proof_notes import GitProofNotesEngine
from apex_council.swarm.live_llm import LiveLLMClient
from apex_council.swarm.solver import AutonomousIssueSolver


class TestPhase6MCTSAndNeuroSymbolicSolver(unittest.TestCase):
    def test_live_llm_client_detection(self) -> None:
        client = LiveLLMClient()
        # Should gracefully return boolean without crashing
        is_avail = client.is_ollama_available()
        self.assertIsInstance(is_avail, bool)

        providers = client.get_available_cloud_providers()
        self.assertIsInstance(providers, list)

    def test_tier1_deterministic_solver_end_to_end_with_git_plumbing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)

            # Initialize a real Git repository
            subprocess.run(["git", "init"], cwd=str(repo_path), check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Apex Autonomous"], cwd=str(repo_path), check=True)
            subprocess.run(["git", "config", "user.email", "apex@sovereign.ai"], cwd=str(repo_path), check=True)

            target_rel = "calculator.py"
            file_path = repo_path / target_rel
            # Real buggy Python code: wrong operator (Add instead of Mult)
            file_path.write_text("def multiply(a, b):\n    return a + b\n", encoding="utf-8")

            # Commit initial buggy code to establish HEAD commit
            subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit with buggy code"], cwd=str(repo_path), check=True)

            test_harness = "assert multiply(3, 4) == 12"

            solver = AutonomousIssueSolver(repo_dir=repo_path)
            # Notice: generator_fn=None so it uses Tier-1 Deterministic AST Synthesizer!
            report = solver.solve_issue(
                target_file_rel=target_rel,
                issue_description="Fix multiply function returning sum instead of product",
                test_harness=test_harness,
                generator_fn=None,  # 100% Deterministic AST Synthesizer
                mcts_iterations=2,
            )

            self.assertTrue(report.success)
            self.assertIn("return a * b", report.patched_code)
            self.assertGreater(len(report.merkle_root), 0)

            # Check that file on disk was patched
            updated_disk = file_path.read_text(encoding="utf-8")
            self.assertIn("return a * b", updated_disk)

            # Verify that Git Proof Note was attached to refs/notes/apex-proof
            notes_engine = GitProofNotesEngine(repo_path)
            commit_sha = report.details.get("commit_sha")
            if commit_sha and commit_sha != "N/A":
                is_valid, msg, proof = notes_engine.verify_proof(commit_sha)
                self.assertTrue(is_valid)
                self.assertIsNotNone(proof)
                self.assertEqual(proof.target_file, target_rel)


if __name__ == "__main__":
    unittest.main()
