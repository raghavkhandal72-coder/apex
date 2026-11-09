"""Hermetic Unit Tests for Awesome-AITools Registry and Recommendation Engine.
100% Python Standard Library (pip = 0).
"""

import unittest
from apex_council.aitools.engine import AwesomeAIToolsEngine


class TestAwesomeAIToolsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AwesomeAIToolsEngine()

    def test_catalog_loaded_and_non_empty(self):
        tools = self.engine.tools
        self.assertGreaterEqual(len(tools), 260)
        self.assertGreaterEqual(len(self.engine.categories), 35)

    def test_search_exact_and_fuzzy(self):
        results = self.engine.search("Antigravity")
        self.assertTrue(any(t.name == "Antigravity" for t in results))

        results_cursor = self.engine.search("Cursor")
        self.assertTrue(any(t.name == "Cursor" for t in results_cursor))

    def test_search_free_only(self):
        results = self.engine.search("agent", free_only=True)
        self.assertTrue(len(results) > 0)
        for t in results:
            self.assertTrue(t.is_free)

    def test_list_categories(self):
        cats = dict(self.engine.list_categories())
        self.assertIn("Coding Agents", cats)
        self.assertIn("AI Agent", cats)
        self.assertGreater(cats["Coding Agents"], 0)

    def test_get_tool(self):
        tool = self.engine.get_tool("Antigravity")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "Antigravity")
        self.assertTrue("antigravity.google" in tool.url)

    def test_recommend_relevance(self):
        rec_browser = self.engine.recommend("Automated browser navigation and scraping", limit=5)
        self.assertTrue(len(rec_browser) > 0)
        rec_names = [t.name.lower() for t in rec_browser]
        self.assertTrue(any("browser" in n or "steel" in n for n in rec_names))

        rec_tts = self.engine.recommend("Text to speech audio synthesizer", limit=5)
        self.assertTrue(len(rec_tts) > 0)
        self.assertTrue(any(t.category in ["Text to Speech (TTS)", "Speech Processing & Translation", "Voice Cloning & Conversion"] for t in rec_tts))


if __name__ == "__main__":
    unittest.main()
