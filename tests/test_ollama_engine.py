#!/usr/bin/env python3
"""
Unit tests for Apex Ollama Integration Engine.
100% Pure Python Standard Library (pip = 0).
"""

from __future__ import annotations

import unittest
from apex_council.providers.ollama_engine import OllamaEngine, handle_ollama_cli


class TestOllamaEngine(unittest.TestCase):
    def test_init_defaults(self) -> None:
        engine = OllamaEngine()
        self.assertEqual(engine.host, "http://127.0.0.1:11434")
        self.assertIsNotNone(engine.model)

    def test_custom_host_and_model(self) -> None:
        engine = OllamaEngine(host="http://localhost:9999", model="codellama")
        self.assertEqual(engine.host, "http://localhost:9999")
        self.assertEqual(engine.model, "codellama")

    def test_is_running_returns_bool(self) -> None:
        engine = OllamaEngine(host="http://127.0.0.1:99999")
        # Should gracefully return False when port is unreachable
        self.assertFalse(engine.is_running(timeout=0.05))

    def test_list_models_returns_list(self) -> None:
        engine = OllamaEngine(host="http://127.0.0.1:99999")
        models = engine.list_models(timeout=0.05)
        self.assertIsInstance(models, list)

    def test_set_active_model(self) -> None:
        engine = OllamaEngine()
        engine.set_active_model("mistral:7b")
        self.assertEqual(engine.model, "mistral:7b")

    def test_render_status_string(self) -> None:
        engine = OllamaEngine()
        status_txt = engine.render_status()
        self.assertIn("OLLAMA LOCAL AI ENGINE STATUS", status_txt)
        self.assertIn(engine.host, status_txt)

    def test_handle_ollama_cli_status(self) -> None:
        rc = handle_ollama_cli(["status"])
        self.assertEqual(rc, 0)

    def test_handle_ollama_cli_use(self) -> None:
        rc = handle_ollama_cli(["use", "qwen2.5-coder"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
