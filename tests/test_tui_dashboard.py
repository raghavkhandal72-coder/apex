"""Tests for Apex Sovereign Cyber-TUI Live Dashboard."""

import unittest

from apex_council.ui.tui_dashboard import ApexLiveTUI


class TestApexLiveTUI(unittest.TestCase):
    def test_system_stats_collection(self):
        stats = ApexLiveTUI.get_system_stats()
        self.assertIn("platform", stats)
        self.assertIn("python", stats)
        self.assertIn("cores", stats)
        self.assertGreater(stats["cores"], 0)

    def test_render_dashboard(self):
        output = ApexLiveTUI.render_dashboard(tick=1)
        self.assertIn("APEX-SOVEREIGN CYBER-TUI", output)
        self.assertIn("4-AGENT SUPREME COUNCIL ROSTER", output)
        self.assertIn("Autonomous Fuzzer", output)


if __name__ == "__main__":
    unittest.main()
