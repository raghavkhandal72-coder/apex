"""Unit tests for Apex-Sovereign Frontier Research Mathematical Modules.
100% Pure Python Standard Library | Zero External Dependencies | Zero Mocks.
"""

import unittest

from apex_council.autopsy.sbfl_triad import SBFLTriadEngine
from apex_council.consensus.shapley_consensus import AgentEvaluation, ShapleyConsensusEngine
from apex_council.formal.hoare_invariants import HoareInvariantVerifier
from apex_council.search.dirichlet_puct import DirichletPUCTPolicy, DirichletSampler


class TestFrontierResearchMath(unittest.TestCase):
    def test_sbfl_triad_engine_mathematics(self) -> None:
        source_code = (
            "def calculate_tax(income):\n"
            "    if income < 0:\n"
            "        return 0\n"
            "    rate = 0.2\n"
            "    tax = income * rate\n"
            "    if income > 100000:\n"
            "        tax += 5000\n"
            "    return tax\n"
        )
        # Bug is simulated when income == 50000: expected 10000, but test asserts 9999
        test_code = (
            "assert calculate_tax(-100) == 0\n"
            "assert calculate_tax(10000) == 2000.0\n"
            "assert calculate_tax(50000) == 9999.0\n"  # Failing test
        )

        engine = SBFLTriadEngine(star_exponent=2.0)
        report = engine.localize(source_code, test_code)

        self.assertEqual(report.total_tests, 3)
        self.assertEqual(report.passed_tests, 2)
        self.assertEqual(report.failed_tests, 1)
        self.assertIsNotNone(report.top_suspicious_line)
        self.assertGreater(len(report.ranked_lines), 0)

        # Check formulas on top line
        top = report.ranked_lines[0]
        self.assertGreaterEqual(top.ochiai, 0.0)
        self.assertLessEqual(top.ochiai, 1.0)
        self.assertGreaterEqual(top.tarantula, 0.0)
        self.assertLessEqual(top.tarantula, 1.0)
        self.assertGreaterEqual(top.dstar, 0.0)
        self.assertGreaterEqual(top.ensemble, 0.0)

    def test_shapley_value_consensus_axioms(self) -> None:
        engine = ShapleyConsensusEngine(approval_threshold=0.60)
        evaluations = [
            AgentEvaluation(
                agent_id="sdet_1",
                role="SDET Architect",
                confidence=0.95,
                vote="APPROVE",
                metric_score=1.0,
                findings_count=0,
                weight=1.5,
            ),
            AgentEvaluation(
                agent_id="appsec_1",
                role="Principal AppSec",
                confidence=0.90,
                vote="APPROVE",
                metric_score=0.95,
                findings_count=0,
                weight=1.2,
            ),
            AgentEvaluation(
                agent_id="perf_1",
                role="Performance Optimizer",
                confidence=0.85,
                vote="APPROVE",
                metric_score=0.90,
                findings_count=1,
                weight=1.0,
            ),
            AgentEvaluation(
                agent_id="challenger_1",
                role="Challenger Red Team",
                confidence=0.70,
                vote="APPROVE",
                metric_score=0.80,
                findings_count=0,
                weight=1.0,
            ),
        ]

        report = engine.compute_exact_shapley_values(evaluations)
        self.assertTrue(report.quorum_passed)
        self.assertEqual(report.consensus_verdict, "APPROVED")
        self.assertEqual(len(report.attributions), 4)

        # Efficiency axiom verification: sum(phi_i) == v(N)
        total_phi = sum(a.shapley_value for a in report.attributions)
        self.assertAlmostEqual(total_phi, report.coalition_value, places=3)
        self.assertLessEqual(report.efficiency_gap, 1e-4)

    def test_shapley_value_veto_collapses_coalition(self) -> None:
        engine = ShapleyConsensusEngine()
        evaluations = [
            AgentEvaluation(
                agent_id="sdet_1",
                role="SDET",
                confidence=0.9,
                vote="APPROVE",
                metric_score=1.0,
                findings_count=0,
            ),
            AgentEvaluation(
                agent_id="appsec_1",
                role="AppSec",
                confidence=0.99,
                vote="VETO",
                metric_score=0.0,
                findings_count=3,
            ),
        ]
        report = engine.compute_exact_shapley_values(evaluations)
        self.assertFalse(report.quorum_passed)
        self.assertEqual(report.consensus_verdict, "VETOED")
        self.assertIn("appsec_1", report.vetoing_agents)

    def test_dirichlet_sampler_and_puct_policy(self) -> None:
        sampler = DirichletSampler(rng_seed=42)
        alphas = [0.3, 0.3, 0.3, 0.3]
        sample = sampler.sample_dirichlet(alphas)
        self.assertEqual(len(sample), 4)
        self.assertAlmostEqual(sum(sample), 1.0, places=5)
        for s in sample:
            self.assertGreater(s, 0.0)

        # PUCT Policy root noise blending
        policy = DirichletPUCTPolicy(alpha=0.3, epsilon_dir=0.25)
        priors = [0.4, 0.3, 0.2, 0.1]
        blended = policy.blend_root_noise(priors)
        self.assertEqual(len(blended), 4)
        self.assertAlmostEqual(sum(blended), 1.0, places=5)

        # Temperature-calibrated visit distribution
        visits = [100, 50, 10, 5]
        # Greedy argmax at low temperature
        greedy = policy.compute_visit_distribution(visits, temperature=1e-5)
        self.assertEqual(greedy, [1.0, 0.0, 0.0, 0.0])

        # Soft distribution at tau = 1.0
        soft = policy.compute_visit_distribution(visits, temperature=1.0)
        self.assertAlmostEqual(sum(soft), 1.0, places=5)
        self.assertGreater(soft[0], soft[1])
        self.assertGreater(soft[1], soft[2])

    def test_hoare_invariant_verifier_safe_code(self) -> None:
        safe_code = (
            "def safe_divide(a, b):\n"
            "    if b != 0:\n"
            "        return a / b\n"
            "    return 0.0\n"
        )
        report = HoareInvariantVerifier.verify_code(safe_code)
        self.assertTrue(report.is_provably_safe)
        self.assertEqual(len(report.violations), 0)
        self.assertGreaterEqual(report.safety_confidence, 0.5)

    def test_hoare_invariant_verifier_detects_zero_division(self) -> None:
        unsafe_code = (
            "def unsafe_divide(a, b):\n"
            "    return a / b\n"
        )
        report = HoareInvariantVerifier.verify_code(unsafe_code)
        self.assertFalse(report.is_provably_safe)
        self.assertEqual(len(report.violations), 1)
        self.assertEqual(report.violations[0].category, "ZERO_DIVISION_RISK")
        self.assertEqual(report.violations[0].severity, "CRITICAL")


if __name__ == "__main__":
    unittest.main()
