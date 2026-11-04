import subprocess
import tempfile
import unittest
from pathlib import Path

from apex_council.git_engine.plumbing import GitPlumbingEngine, GitTreeEntry
from apex_council.git_engine.proof_notes import GitProofNotesEngine


class TestPhase2GitPlumbingAndNotes(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        # Initialize a real Git repository in temp_dir
        subprocess.run(["git", "init"], cwd=str(self.repo_path), check=True, capture_output=True)
        # Configure user for commit creation
        subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(self.repo_path), check=True)
        subprocess.run(["git", "config", "user.email", "test@apex.ai"], cwd=str(self.repo_path), check=True)

        self.plumbing = GitPlumbingEngine(self.repo_path)
        self.notes = GitProofNotesEngine(self.repo_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_git_hash_object_and_cat_file(self) -> None:
        content = "print('Hello Bare-Metal Git Plumbing')\n"
        sha = self.plumbing.hash_object(content, write=True)
        self.assertEqual(len(sha), 40)

        retrieved = self.plumbing.cat_file(sha)
        self.assertEqual(retrieved.strip(), content.strip())

    def test_git_mktree_and_commit_tree(self) -> None:
        blob_sha = self.plumbing.hash_object("def solve(): return 42\n", write=True)
        entry = GitTreeEntry(mode="100644", object_type="blob", sha=blob_sha, path="solve.py")

        tree_sha = self.plumbing.make_tree([entry])
        self.assertEqual(len(tree_sha), 40)

        tree_entries = self.plumbing.list_tree(tree_sha)
        self.assertEqual(len(tree_entries), 1)
        self.assertEqual(tree_entries[0].path, "solve.py")
        self.assertEqual(tree_entries[0].sha, blob_sha)

        commit_sha = self.plumbing.commit_tree(tree_sha, message="Autonomously synthesized patch")
        self.assertEqual(len(commit_sha), 40)

    def test_proof_notes_attach_and_verify(self) -> None:
        blob_sha = self.plumbing.hash_object("def add(a, b): return a + b\n", write=True)
        tree_sha = self.plumbing.make_tree([GitTreeEntry(mode="100644", object_type="blob", sha=blob_sha, path="math.py")])
        commit_sha = self.plumbing.commit_tree(tree_sha, message="Math fix")

        payload = self.notes.attach_proof(
            commit_sha=commit_sha,
            target_file="math.py",
            crashing_instruction="BINARY_OP",
            ochiai_score=1.0,
            mutation_kill_score=100.0,
            killed_mutants=10,
            opcode_delta=-5,
            merkle_root="abc123merkle",
        )
        self.assertIsNotNone(payload.hmac_seal)

        # Verify proof
        is_valid, msg, retrieved = self.notes.verify_proof(commit_sha)
        self.assertTrue(is_valid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.target_file, "math.py")
        self.assertEqual(retrieved.opcode_delta, -5)


if __name__ == "__main__":
    unittest.main()
