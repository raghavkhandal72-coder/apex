import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import pr_review as pr  # noqa: E402

DIFF = """diff --git a/apex_council/core.py b/apex_council/core.py
--- a/apex_council/core.py
+++ b/apex_council/core.py
@@ -10,3 +10,5 @@ def f():
     ctx = 1
+    added_a = 2
+    added_b = 3
     ctx2 = 4
@@ -40,2 +42,2 @@ def g():
-    old = 1
+    new = 1
     tail = 2
diff --git a/new.txt b/gone.txt
--- a/gone.txt
+++ /dev/null
@@ -1 +0,0 @@
-bye
"""


def d(path, line, msg="m", sev="WARNING", code=None):
    x = {"message": msg, "location": {"path": path, "range": {"start": {"line": line}}}, "severity": sev}
    if code:
        x["code"] = {"value": code}
    return x


class ParseTests(unittest.TestCase):
    def test_added_line_numbers(self):
        added = pr.parse_added_lines(DIFF)
        self.assertEqual(added["apex_council/core.py"], {11, 12, 42})
        self.assertNotIn("gone.txt", added)

    def test_filter_keeps_only_added_lines(self):
        added = pr.parse_added_lines(DIFF)
        diags = [d("apex_council/core.py", 12), d("apex_council/core.py", 10), d("apex_council/core.py", 100)]
        kept = pr.filter_findings(diags, added)
        self.assertEqual([f["line"] for f in kept], [12])

    def test_windows_and_dot_slash_paths(self):
        added = pr.parse_added_lines(DIFF)
        kept = pr.filter_findings([d(".\\apex_council\\core.py", 11)], added)
        self.assertEqual(len(kept), 1)

    def test_absolute_path_with_root(self):
        added = pr.parse_added_lines(DIFF)
        kept = pr.filter_findings([d("/work/repo/apex_council/core.py", 42)], added, root="/work/repo")
        self.assertEqual(len(kept), 1)

    def test_dedup_and_cap(self):
        added = pr.parse_added_lines(DIFF)
        diags = [d("apex_council/core.py", 11, "same")] * 3 + [d("apex_council/core.py", 12, "x", "ERROR", "SEC01")]
        kept = pr.filter_findings(diags, added)
        self.assertEqual(len(kept), 2)
        review = pr.to_review(kept, max_comments=1)
        self.assertEqual(len(review["comments"]), 1)
        self.assertIn("1 more not shown", review["body"])

    def test_rdjson_parse_and_bad_input(self):
        self.assertEqual(pr.parse_rdjson(json.dumps({"diagnostics": [d("a", 1)]}))[0]["message"], "m")
        with self.assertRaises(ValueError):
            pr.parse_rdjson("{ invalid_json: true,")


class PRReviewCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.diff_file = self.temp_path / "pr.diff"
        self.diff_file.write_text(DIFF, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_output(self):
        findings_file = self.temp_path / "findings.rdjson"
        findings_file.write_text(
            json.dumps({"diagnostics": [d("apex_council/core.py", 11, "style warning", "WARNING")]}),
            encoding="utf-8",
        )

        code = pr.main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    def test_fail_on_error_trigger(self):
        findings_file = self.temp_path / "findings_err.rdjson"
        findings_file.write_text(
            json.dumps({"diagnostics": [d("apex_council/core.py", 12, "critical flaw", "ERROR")]}),
            encoding="utf-8",
        )

        code = pr.main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 1)

    def test_fail_on_error_not_triggered_for_warning(self):
        findings_file = self.temp_path / "findings_warn.rdjson"
        findings_file.write_text(
            json.dumps({"diagnostics": [d("apex_council/core.py", 11, "minor style", "WARNING")]}),
            encoding="utf-8",
        )

        code = pr.main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    def test_fail_on_error_not_triggered_when_error_outside_diff(self):
        findings_file = self.temp_path / "findings_outside.rdjson"
        findings_file.write_text(
            json.dumps({"diagnostics": [d("apex_council/core.py", 10, "legacy error", "ERROR")]}),
            encoding="utf-8",
        )

        code = pr.main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    @patch("urllib.request.urlopen")
    def test_post_github_pr_review_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        ok = pr.post_github_pr_review(
            repo="octocat/Hello-World",
            pr_number=42,
            token="ghp_fake_token",
            review_payload={"body": "Summary", "comments": []},
            commit_sha="abcdef123456",
        )
        self.assertTrue(ok)
        self.assertTrue(mock_urlopen.called)


if __name__ == "__main__":
    unittest.main()
