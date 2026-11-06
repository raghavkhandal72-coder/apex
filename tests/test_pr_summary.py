import unittest

from apex_council.git.pr_summary import parse_diff_files, generate_pr_summary_markdown


class TestApexPRSummary(unittest.TestCase):
    def test_parse_diff_and_generate_markdown(self):
        sample_diff = (
            "diff --git a/calc.py b/calc.py\n"
            "--- a/calc.py\n"
            "+++ b/calc.py\n"
            "@@ -1,3 +1,4 @@\n"
            "-def old_func():\n"
            "+def new_func():\n"
            "+    return 42\n"
        )
        files = parse_diff_files(sample_diff)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["file"], "calc.py")
        self.assertEqual(files[0]["added"], 2)
        self.assertEqual(files[0]["deleted"], 1)

        summary = generate_pr_summary_markdown(sample_diff, title="Feat: new calculation")
        self.assertIn("Feat: new calculation", summary)
        self.assertIn("`calc.py`", summary)
        self.assertIn("`new_func`", summary)
        self.assertIn("Verification Checklist", summary)


if __name__ == "__main__":
    unittest.main()
