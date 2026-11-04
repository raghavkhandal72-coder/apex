import unittest
from pathlib import Path
from apex_council.engine import CouncilEngine
from apex_council.evaluator.security_eval import evaluate_security
from apex_council.evaluator.runtime_eval import evaluate_runtime
from apex_council.models import ModelProvider
from apex_council.providers.live_http import LiveGeminiProvider, LiveClaudeProvider, LiveOpenAIProvider


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

    def test_audit_file(self):
        this_file = Path(__file__)
        audit_res = self.engine.audit_file(this_file)
        self.assertIn("original_security_score", audit_res)
        self.assertIsNotNone(audit_res["council_result"])

    def test_live_adapters_error_handling(self):
        # Verify fallback error handling when dummy invalid key is provided
        gemini = LiveGeminiProvider("invalid-dummy-key")
        sub = gemini.generate("test task")
        self.assertIn("Fallback", sub.model_name)


if __name__ == "__main__":
    unittest.main()
