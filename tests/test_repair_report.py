import io
import os
import unittest

from apex_council.ui.repair_report import render_repair, token_changes


class Buf(io.StringIO):
    encoding = "utf-8"

    def isatty(self) -> bool:
        return False


class ReportTests(unittest.TestCase):
    def test_token_change(self):
        self.assertEqual(token_changes("while left < right:", "while left <= right:"), [("<", "<=")])

    def test_plain_output_has_no_ansi_and_says_one_token(self):
        os.environ.pop("FORCE_COLOR", None)
        s = render_repair("x = a < b\n", "x = a <= b\n", visible=(2, 2), hidden=(10, 10), stream=Buf())
        self.assertNotIn("\033[", s)
        self.assertIn("1-token change", s)
        self.assertIn("hidden probes  10/10", s)
        self.assertIn("not a proof", s)

    def test_failed_hidden_is_marked(self):
        s = render_repair("a\n", "b\n", visible=(1, 1), hidden=(3, 5), stream=Buf())
        self.assertIn("hidden probes  3/5", s)


if __name__ == "__main__":
    unittest.main()
