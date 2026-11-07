import unittest
from apex_council.providers.llamafile_engine import (
    ApexPortableRunner,
    LlamafileEngine,
    handle_runner_cli,
    handle_llamafile_cli,
)
from apex_council.providers.live_http import LiveApexRunnerProvider, LiveLlamafileProvider
from apex_council.models import ModelProvider


class TestApexPortableRunner(unittest.TestCase):
    def setUp(self):
        self.engine = ApexPortableRunner(host="http://127.0.0.1:9999")

    def test_runner_status_card(self):
        status = self.engine.render_status()
        self.assertIn("APEX SOVEREIGN PORTABLE BINARY RUNNER", status)
        self.assertIn("9999", status)

    def test_runner_cli_status(self):
        code = handle_runner_cli(["status"])
        self.assertEqual(code, 0)

    def test_runner_cli_info(self):
        code = handle_runner_cli(["info"])
        self.assertEqual(code, 0)

    def test_llamafile_alias_compatibility(self):
        code = handle_llamafile_cli(["status"])
        self.assertEqual(code, 0)
        self.assertIs(LlamafileEngine, ApexPortableRunner)

    def test_live_apex_runner_provider_init(self):
        prov = LiveApexRunnerProvider(host="http://127.0.0.1:8080", provider=ModelProvider.OPENAI)
        self.assertEqual(prov.provider, ModelProvider.OPENAI)
        self.assertIn("8080", prov.host)
        crit = prov.critique(ModelProvider.GEMINI, "def foo(): pass", "foo task")
        self.assertEqual(crit.reviewer, ModelProvider.OPENAI)
        self.assertGreaterEqual(crit.score, 8.0)


if __name__ == "__main__":
    unittest.main()
