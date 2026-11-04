import tempfile
import unittest
from pathlib import Path

from apex_council.cli import parse_args
from apex_council.ui.replay import HTMLReportGenerator
from apex_council.ui.terminal import CyberpunkTUI


class TestCLIAndHTMLSuite(unittest.TestCase):
    def test_cyberpunk_sparkline_and_split_pane(self) -> None:
        values = [10.0, 20.0, 50.0, 80.0, 100.0]
        spark = CyberpunkTUI.render_sparkline(values)
        self.assertEqual(len(spark), len(values))
        self.assertEqual(spark[0], " ")
        self.assertEqual(spark[-1], "█")

        # Split pane
        left = ["Line 1A", "Line 2A"]
        right = ["Line 1B", "Line 2B"]
        pane = CyberpunkTUI.render_split_pane(left, right, width=60)
        self.assertIn("Line 1A", pane)
        self.assertIn("Line 1B", pane)
        self.assertIn("│", pane)

        # MCTS tree
        traj = ["Root Node", "Branch A (Score: 0.5)", "Branch B (Score: 1.0)"]
        tree = CyberpunkTUI.render_mcts_tree(traj)
        self.assertIn("Root Node", tree)
        self.assertIn("└──", tree)

    def test_html_report_generator_airtight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_html = Path(tmp_dir) / "audit_report.html"
            diff_text = """--- original
+++ sovereign_patch
@@ -1,2 +1,2 @@
-def solve(): return 0
+def solve(): return 42"""

            content = HTMLReportGenerator.generate_report(
                title="Unit Test Resolution",
                task_prompt="Fix return 0 to 42",
                target_file="solver.py",
                diff_text=diff_text,
                is_passing=True,
                merkle_root="a1b2c3d4e5f6071829",
                signature="sha512-test-seal",
                duration_ms=45.2,
                mcts_nodes=4,
                output_path=out_html,
            )

            self.assertTrue(out_html.exists())
            self.assertIn("PASSED & SIGNED", content)
            self.assertIn("a1b2c3d4e5f6071829", content)
            self.assertIn("sha512-test-seal", content)
            self.assertIn("def solve(): return 42", content)

            # Air-tight verification: ZERO external CDN dependencies
            self.assertNotIn("http://", content)
            self.assertNotIn("https://", content)
            self.assertNotIn("<script", content)

    def test_cli_argument_parsing(self) -> None:
        # 1. solve with file and tests
        args = parse_args(["solve", "Fix bug", "--file", "math.py", "--tests", "assert True"])
        self.assertEqual(args.command, "solve")
        self.assertEqual(args.file, "math.py")
        self.assertEqual(args.tests, "assert True")

        # 2. localize
        args2 = parse_args(["localize", "calculator.py", "--tests", "assert calc() == 1"])
        self.assertEqual(args2.command, "localize")
        self.assertEqual(args2.tests, "assert calc() == 1")

        # 3. build-pyz
        args3 = parse_args(["build-pyz", "-o", "out.pyz"])
        self.assertEqual(args3.command, "build-pyz")
        self.assertEqual(args3.output, "out.pyz")

        # 4. swe-bench
        args4 = parse_args(["swe-bench"])
        self.assertEqual(args4.command, "swe-bench")


if __name__ == "__main__":
    unittest.main()
