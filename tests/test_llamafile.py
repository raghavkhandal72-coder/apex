import unittest
from apex_council.providers.llamafile_engine import LlamafileEngine, handle_llamafile_cli
from apex_council.providers.live_http import LiveLlamafileProvider
from apex_council.models import ModelProvider


class TestLlamafileEngine(unittest.TestCase):
    def setUp(self):
        self.engine = LlamafileEngine(host="http://127.0.0.1:9999")

    def test_llamafile_status_card(self):
        status = self.engine.render_status()
        self.assertIn("APEX MOZILLA LLAMAFILE ENGINE STATUS", status)
        self.assertIn("9999", status)

    def test_llamafile_cli_status(self):
        code = handle_llamafile_cli(["status"])
        self.assertEqual(code, 0)

    def test_llamafile_cli_info(self):
        code = handle_llamafile_cli(["info"])
        self.assertEqual(code, 0)

    def test_live_llamafile_provider_init(self):
        prov = LiveLlamafileProvider(host="http://127.0.0.1:8080", provider=ModelProvider.OPENAI)
        self.assertEqual(prov.provider, ModelProvider.OPENAI)
        self.assertIn("8080", prov.host)
        crit = prov.critique(ModelProvider.GEMINI, "def foo(): pass", "foo task")
        self.assertEqual(crit.reviewer, ModelProvider.OPENAI)
        self.assertGreaterEqual(crit.score, 8.0)


if __name__ == "__main__":
    unittest.main()
