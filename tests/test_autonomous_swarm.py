import unittest

from apex_council.memory.vault import MemoryVault
from apex_council.swarm.coordinator import SwarmCoordinator
from apex_council.swarm.roles import (
    RedTeamBreaker,
    SovereignGatekeeper,
    StaffArchitect,
    TestFirstSpeculator,
)


class TestAutonomousSwarm(unittest.TestCase):
    def test_staff_architect(self) -> None:
        blueprint = StaffArchitect.design_blueprint(
            task_spec="Build a distributed lock manager in lock_manager.py with heartbeat",
            repo_map_skeleton="📁 core.py\n  class LockManager:",
        )
        self.assertIn("lock_manager.py", blueprint.target_components)
        self.assertGreater(len(blueprint.invariants), 2)
        self.assertGreater(len(blueprint.edge_cases), 2)

    def test_test_first_speculator(self) -> None:
        blueprint = StaffArchitect.design_blueprint(
            task_spec="Implement validate_token in auth.py",
        )
        suite = TestFirstSpeculator.generate_reproduction_suite(
            task_spec="Implement validate_token in auth.py",
            blueprint=blueprint,
        )
        self.assertIn("validate_token", suite.test_code)
        self.assertIn("class TestAutonomousReproduction", suite.test_code)

    def test_red_team_breaker(self) -> None:
        clean_code = "def add(a, b): return a + b"
        fuzz_clean = RedTeamBreaker.audit_and_fuzz(clean_code)
        self.assertTrue(fuzz_clean["passed"])
        self.assertEqual(len(fuzz_clean["vulnerabilities"]), 0)

        hostile_code = "def run(): eval('import os; os.system(\"rm -rf /\")')"
        fuzz_hostile = RedTeamBreaker.audit_and_fuzz(hostile_code)
        self.assertFalse(fuzz_hostile["passed"])
        self.assertIn("eval(", fuzz_hostile["vulnerabilities"])

    def test_sovereign_gatekeeper(self) -> None:
        passing_code = "def get_status(): return 'active'"
        test_harness = "assert get_status() == 'active'"

        passed, signed_code, sig = SovereignGatekeeper.attest_and_sign(
            code=passing_code,
            task_spec="Get status",
            test_harness=test_harness,
        )
        self.assertTrue(passed)
        self.assertIn("# APEX-SIG-SHA512:", signed_code)
        self.assertEqual(len(sig), 128)

    def test_swarm_coordinator_solve(self) -> None:
        vault = MemoryVault(":memory:")
        coordinator = SwarmCoordinator(memory_vault=vault)

        # Run end-to-end solve
        solution = coordinator.solve(
            task_prompt="Implement cache_worker to handle in-memory cache lookups",
            mcts_iterations=2,
        )

        self.assertTrue(solution.is_passing)
        self.assertIn("# APEX-SIG-SHA512:", solution.verified_code)
        self.assertGreaterEqual(solution.mcts_score, 1.0)
        self.assertGreater(solution.total_nodes_explored, 0)

        # Verify episodic memory was recorded
        episodes = vault.get_all_episodes()
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].status, "SOLVED")


if __name__ == "__main__":
    unittest.main()
