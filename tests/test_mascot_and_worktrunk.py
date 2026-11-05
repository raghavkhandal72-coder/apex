#!/usr/bin/env python3
"""
Unit Test Suite for Pixel Mascot, Worktrunk Table & Interactive Console
100% Pure Python Standard Library | Zero Dependencies
"""

import unittest
from apex_council.ui.mascot import MascotRenderer, APEX_PIXEL_MASCOT
from apex_council.git_engine.worktrunk_advanced import WorktrunkAdvancedEngine


class TestMascotAndWorktrunkSuite(unittest.TestCase):
    def test_mascot_header_rendering(self) -> None:
        header = MascotRenderer.render_header(
            version="v2.5.0",
            model="Claude 3.7 Sonnet · Gemini 2.5",
            workspace_path="/workspace/test",
            tip="Switch models with /model",
        )
        self.assertIn("Apex-Sovereign v2.5.0", header)
        self.assertIn("Claude 3.7 Sonnet", header)
        self.assertIn("MCTS PUCT", header)
        self.assertIn("Switch models with /model", header)

    def test_mascot_status_bar(self) -> None:
        bar = MascotRenderer.render_status_bar(
            worktree_path="~/w/acme.billing",
            pr_num="#6",
            model_name="Opus 4.6",
        )
        self.assertIn("~/w/acme.billing", bar)
        self.assertIn("#6", bar)
        self.assertIn("Opus 4.6", bar)
        self.assertIn("Ctrl + <n> New Pane", bar)

    def test_worktrunk_advanced_table_rendering(self) -> None:
        engine = WorktrunkAdvancedEngine(".")
        table_output = engine.render_table(full=True)
        self.assertIn("Branch", table_output)
        self.assertIn("Status", table_output)
        self.assertIn("HEAD±", table_output)
        self.assertIn("main↕", table_output)
        self.assertIn("Summary", table_output)
        self.assertIn("Showing", table_output)


if __name__ == "__main__":
    unittest.main()
