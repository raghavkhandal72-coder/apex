#!/usr/bin/env python3
"""
Unit tests for Apex Offline AI Synthesizer and Local LLM Provider.
100% Pure Python Standard Library (pip = 0).
"""

from __future__ import annotations

import ast
import unittest
from apex_council.models import ModelProvider
from apex_council.synthesis.offline_ai import OfflineAISynthesizer
from apex_council.providers.local_llm import LocalLLMClient
from apex_council.engine import CouncilEngine


class TestOfflineAISynthesizer(unittest.TestCase):
    def test_fibonacci_synthesis(self) -> None:
        code = OfflineAISynthesizer.synthesize("Write a function to generate fibonacci numbers", ModelProvider.GEMINI)
        self.assertIn("fibonacci", code.lower())
        ast.parse(code)

    def test_quicksort_synthesis(self) -> None:
        code = OfflineAISynthesizer.synthesize("Implement quicksort algorithm", ModelProvider.OPENAI)
        self.assertIn("quicksort", code.lower())
        ast.parse(code)

    def test_rate_limiter_synthesis(self) -> None:
        code = OfflineAISynthesizer.synthesize("Build a token bucket rate limiter", ModelProvider.CLAUDE)
        self.assertIn("rate", code.lower())
        ast.parse(code)

    def test_trie_synthesis(self) -> None:
        code = OfflineAISynthesizer.synthesize("Create a Trie prefix tree", ModelProvider.GEMINI)
        self.assertIn("trie", code.lower())
        ast.parse(code)

    def test_compound_interest_synthesis(self) -> None:
        code = OfflineAISynthesizer.synthesize("Calculate compound interest", ModelProvider.CLAUDE)
        self.assertIn("compound", code.lower())
        ast.parse(code)

    def test_local_llm_detection_returns_none_or_tuple(self) -> None:
        res = LocalLLMClient.detect_active_endpoint()
        self.assertTrue(res is None or isinstance(res, tuple))

    def test_offline_council_deliberation(self) -> None:
        engine = CouncilEngine(force_offline=True)
        res = engine.convene_council("Write a quicksort algorithm in python")
        self.assertIsNotNone(res.consensus_code)
        self.assertIn("quicksort", res.consensus_code.lower())
        ast.parse(res.consensus_code)


if __name__ == "__main__":
    unittest.main()
