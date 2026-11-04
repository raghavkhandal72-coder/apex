import unittest
from pathlib import Path
from apex_council.engine import CouncilEngine
from apex_council.evaluator.security_eval import evaluate_security
from apex_council.evaluator.runtime_eval import evaluate_runtime
from apex_council.evaluator.redteam import run_redteam_analysis
from apex_council.evaluator.self_healing import SelfHealingLoop
from apex_council.evaluator.github_pr import parse_github_pr_url
from apex_council.polyglot import detect_language, Language
from apex_council.models import ModelProvider
from apex_council.providers.live_http import LiveGeminiProvider


class TestApexCouncil(unittest.TestCase):
    def setUp(self):
        self.engine = CouncilEngine(force_offline=True)

    def test_security_eval_catches_flaws(self):
        vuln_code = """
import os
def bad_func(user_input):
    os.system("rm " + user_input)
    eval(user_input)
"""
        score, issues = evaluate_security(vuln_code)
        self.assertLess(score, 60.0)
        self.assertGreaterEqual(len(issues), 2)

    def test_security_eval_rewards_clean_code(self):
        clean_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        score, issues = evaluate_security(clean_code)
        self.assertEqual(score, 100.0)
        self.assertEqual(len(issues), 0)

    def test_runtime_eval_execution(self):
        test_code = """
def multiply(x, y):
    return x * y

assert multiply(3, 4) == 12
"""
        syntax_ok, runtime_ok, duration_ms, err = evaluate_runtime(test_code)
        self.assertTrue(syntax_ok)
        self.assertTrue(runtime_ok)
        self.assertGreater(duration_ms, 0)
        self.assertEqual(err, "")

    def test_convene_council_end_to_end(self):
        result = self.engine.convene_council("Write a thread-safe singleton pattern in Python")
        self.assertIsNotNone(result.winner)
        self.assertIn(result.winner, [ModelProvider.GEMINI, ModelProvider.CLAUDE, ModelProvider.OPENAI])
        self.assertEqual(len(result.submissions), 3)
        self.assertEqual(len(result.critiques), 6)  # 3 models * 2 critiques each
        self.assertTrue(result.consensus_code.startswith('"""Apex-Council Synthesized Implementation'))

    def test_collaborative_relay_pipeline(self):
        res = self.engine.collaborative_relay("Build a task scheduler")
        self.assertIn("combined_code", res)
        self.assertIn("IMPLEMENTATION", res["combined_code"])
        self.assertIn("VERIFICATION SUITE", res["combined_code"])

    def test_redteam_analysis(self):
        code = "def safe_calc(a, b): return a + b"
        report = run_redteam_analysis(code)
        self.assertGreaterEqual(report.total_probes, 5)

    def test_parse_github_pr_url(self):
        owner, repo, num = parse_github_pr_url("https://github.com/torvalds/linux/pull/1234")
        self.assertEqual(owner, "torvalds")
        self.assertEqual(repo, "linux")
        self.assertEqual(num, 1234)

        owner2, repo2, num2 = parse_github_pr_url("django/django#9999")
        self.assertEqual(owner2, "django")
        self.assertEqual(repo2, "django")
        self.assertEqual(num2, 9999)

    def test_polyglot_detection(self):
        self.assertEqual(detect_language("app.ts"), Language.TYPESCRIPT)
        self.assertEqual(detect_language("server.go"), Language.GO)
        self.assertEqual(detect_language("main.rs"), Language.RUST)
        self.assertEqual(detect_language("test.py"), Language.PYTHON)

    def test_self_healing_already_clean(self):
        clean_file = Path(__file__).parent.parent / "apex_council" / "polyglot.py"
        healer = SelfHealingLoop(engine=self.engine)
        # Should detect as already clean / not needing changes
        res = healer.heal(clean_file, max_attempts=1, auto_write=False)
        self.assertTrue(res.healed)
        self.assertEqual(res.iterations_run, 0)


    def test_autonomous_engineer_build(self):
        from apex_council.engineer import AutonomousEngineer
        import tempfile
        engineer = AutonomousEngineer(engine=self.engine)
        with tempfile.TemporaryDirectory() as tmp_dir:
            proj = engineer.build_project("Build a thread-safe counter with reset", tmp_dir)
            self.assertTrue(proj.tests_passed)
            self.assertGreaterEqual(len(proj.files_created), 3)


if __name__ == "__main__":
    unittest.main()
