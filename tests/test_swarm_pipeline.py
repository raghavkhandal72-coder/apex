import tempfile
import unittest
from pathlib import Path

from apex_council.swarm.contracts import ContractSpecification, ContractVerifier
from apex_council.swarm.coordinator import (
    BlindPeerReviewer,
    BrierCalibrationTracker,
    DebateBus,
    SwarmCoordinator,
)
from apex_council.swarm.fuzzy_patch import AutoImportFixer, FuzzyPatchApplier
from apex_council.swarm.llm_router import DeterministicMockLLM, LLMRouter
from apex_council.swarm.roles import StaffArchitect
from apex_council.swarm.solver import AutonomousIssueSolver


class TestSwarmPipelineSuite(unittest.TestCase):
    def test_deterministic_mock_llm(self) -> None:
        router = LLMRouter(default_provider="mock")
        res = router.call("Implement divide function")
        self.assertTrue(res.is_mock)
        self.assertIn("def divide", res.content)
        self.assertGreater(res.total_tokens, 0)

    def test_contract_verifier_cyclomatic_complexity_and_imports(self) -> None:
        clean_code = '''
def clean_function(x: int) -> int:
    """Computes clean calculation."""
    if x > 0:
        return x * 2
    return 0
'''
        spec = ContractSpecification(
            required_symbols=["clean_function"],
            prohibited_imports=["pickle", "telnetlib"],
            max_cyclomatic_complexity=5,
            enforce_docstrings=True,
        )
        report = ContractVerifier.verify(clean_code, spec)
        self.assertTrue(report.is_compliant)
        self.assertEqual(len(report.violations), 0)

        # Violating code: prohibited import and missing docstring
        bad_code = '''
import pickle

def unverified(x):
    return pickle.loads(x)
'''
        bad_report = ContractVerifier.verify(bad_code, spec)
        self.assertFalse(bad_report.is_compliant)
        self.assertTrue(any("pickle" in v for v in bad_report.violations))
        self.assertTrue(any("docstring" in v for v in bad_report.violations))

    def test_auto_import_fixer(self) -> None:
        code_missing_imports = '''
def save_config(cfg: Dict[str, Any], path: Path) -> None:
    data = json.dumps(cfg)
    path.write_text(data)
'''
        fixed, injected = AutoImportFixer.fix_imports(code_missing_imports)
        self.assertIn("import json", fixed)
        self.assertIn("from pathlib import Path", fixed)
        self.assertIn("from typing import Any", fixed)
        self.assertIn("from typing import Dict", fixed)
        self.assertGreaterEqual(len(injected), 3)

    def test_fuzzy_patch_applier_search_replace(self) -> None:
        original = '''
def calculate_tax(income):
    # Old tax logic
    rate = 0.20
    return income * rate
'''
        patch_text = '''
<<<<<<< SEARCH
    # Old tax logic
    rate = 0.20
    return income * rate
=======
    # Progressive tax bracket
    if income > 100000:
        return income * 0.30
    return income * 0.15
>>>>>>> REPLACE
'''
        res = FuzzyPatchApplier.apply_patch(original, patch_text)
        self.assertTrue(res.success)
        self.assertEqual(res.applied_hunks, 1)
        self.assertIn("Progressive tax bracket", res.patched_code)
        self.assertIn("return income * 0.30", res.patched_code)

    def test_blind_peer_reviewer_and_debate_bus(self) -> None:
        tracker = BrierCalibrationTracker()
        spec = ContractSpecification(max_cyclomatic_complexity=10)

        cand_good = 'def solve():\n    """Docstring."""\n    return 42'
        cand_insecure = 'import os\ndef solve():\n    os.system("echo hello")\n    return 42'

        best_cand, votes = BlindPeerReviewer.review_candidates(
            candidates=[cand_insecure, cand_good],
            contract_spec=spec,
            test_harness="assert solve() == 42",
            calibration=tracker,
        )
        self.assertEqual(best_cand, cand_good)
        self.assertGreater(len(votes), 0)

        # Test Debate Bus
        blueprint = StaffArchitect.design_blueprint("solve problem")
        debated, rounds = DebateBus.debate(cand_good, "solve problem", blueprint)
        self.assertEqual(len(rounds), 2)
        self.assertEqual(rounds[0].speaker_role, "RedTeamBreaker")
        self.assertEqual(rounds[1].speaker_role, "AutonomousEngineer")

    def test_autonomous_issue_solver_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_path = Path(tmp_dir)
            target_rel = "calculator.py"
            file_path = repo_path / target_rel
            file_path.write_text("def multiply(a, b): return a + b\n", encoding="utf-8")  # Buggy!

            test_harness = "assert multiply(3, 4) == 12"

            def solver_gen(state: str, action: str) -> list[str]:
                return [
                    "def multiply(a, b): return a * b",
                ]

            solver = AutonomousIssueSolver(repo_dir=repo_path)
            report = solver.solve_issue(
                target_file_rel=target_rel,
                issue_description="Fix multiply returning sum instead of product",
                test_harness=test_harness,
                generator_fn=solver_gen,
                mcts_iterations=2,
            )

            self.assertTrue(report.success)
            self.assertIn("return a * b", report.patched_code)
            self.assertGreater(len(report.merkle_root), 0)
            self.assertGreaterEqual(report.ledger_block_index, 1)

            # Check that file on disk was patched
            updated_disk = file_path.read_text(encoding="utf-8")
            self.assertIn("return a * b", updated_disk)


if __name__ == "__main__":
    unittest.main()
