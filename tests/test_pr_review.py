import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.pr_review import (
    DiagnosticFinding,
    DiffFile,
    build_review_summary,
    filter_findings_to_added_lines,
    main,
    normalize_path,
    parse_diff_added_lines,
    parse_rdjson_file,
    paths_match,
    post_github_pr_review,
)


SAMPLE_DIFF = """diff --git a/src/calc.py b/src/calc.py
index 1234567..89abcdef 100644
--- a/src/calc.py
+++ b/src/calc.py
@@ -10,6 +10,8 @@ def existing_func():
     x = 1
     y = 2
+    z = x + y
+    result = dangerous_eval(z)
     return result
"""

SAMPLE_MULTI_DIFF = """diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 def a():
+    added_line = 1
     pass
diff --git a/bar.py b/bar.py
--- /dev/null
+++ b/bar.py
@@ -0,0 +1,2 @@
+new_file_line_1 = True
+new_file_line_2 = False
"""


class PRReviewDiffTests(unittest.TestCase):
    def test_normalize_path(self):
        self.assertEqual(normalize_path("a/src/file.py"), "src/file.py")
        self.assertEqual(normalize_path("b/src/file.py"), "src/file.py")
        self.assertEqual(normalize_path("./src/file.py"), "src/file.py")
        self.assertEqual(normalize_path("src\\file.py"), "src/file.py")

    def test_paths_match(self):
        self.assertTrue(paths_match("src/calc.py", "b/src/calc.py"))
        self.assertTrue(paths_match("calc.py", "src/calc.py"))
        self.assertTrue(paths_match("SRC/CALC.PY", "src/calc.py"))
        self.assertFalse(paths_match("other.py", "src/calc.py"))

    def test_parse_diff_added_lines(self):
        files = parse_diff_added_lines(SAMPLE_DIFF)
        self.assertIn("src/calc.py", files)
        calc = files["src/calc.py"]
        # In hunk @@ -10,6 +10,8 @@:
        # Context: line 10, line 11
        # Added: line 12 (z = x + y), line 13 (result = dangerous_eval(z))
        # Context: line 14 (return result)
        self.assertEqual(calc.added_lines, {12, 13})

    def test_parse_multi_file_diff(self):
        files = parse_diff_added_lines(SAMPLE_MULTI_DIFF)
        self.assertIn("foo.py", files)
        self.assertIn("bar.py", files)
        self.assertEqual(files["foo.py"].added_lines, {2})
        self.assertEqual(files["bar.py"].added_lines, {1, 2})


class PRReviewFilterTests(unittest.TestCase):
    def setUp(self):
        self.diff_files = parse_diff_added_lines(SAMPLE_DIFF)

    def test_filter_only_added_lines(self):
        findings = [
            # Finding on added line 12 -> SHOULD BE KEPT
            DiagnosticFinding(
                message="Unused variable z",
                path="src/calc.py",
                line=12,
                severity="WARNING",
                rule_code="W0612",
            ),
            # Finding on added line 13 -> SHOULD BE KEPT
            DiagnosticFinding(
                message="Use of eval is dangerous",
                path="src/calc.py",
                line=13,
                severity="ERROR",
                rule_code="S102",
            ),
            # Finding on context line 10 -> SHOULD BE SKIPPED
            DiagnosticFinding(
                message="Missing docstring",
                path="src/calc.py",
                line=10,
                severity="INFO",
                rule_code="C0111",
            ),
            # Finding on line 1 -> SHOULD BE SKIPPED (outside hunk)
            DiagnosticFinding(
                message="License header missing",
                path="src/calc.py",
                line=1,
                severity="INFO",
            ),
            # Finding on different file -> SHOULD BE SKIPPED
            DiagnosticFinding(
                message="Syntax error",
                path="src/other.py",
                line=5,
                severity="ERROR",
            ),
        ]

        added, skipped = filter_findings_to_added_lines(findings, self.diff_files)
        self.assertEqual(len(added), 2)
        self.assertEqual(len(skipped), 3)

        # Priority sorting: ERROR should be first, even though line 13 > line 12
        self.assertEqual(added[0].severity, "ERROR")
        self.assertEqual(added[0].line, 13)
        self.assertEqual(added[1].severity, "WARNING")
        self.assertEqual(added[1].line, 12)


class PRReviewRDJSONTests(unittest.TestCase):
    def test_parse_rdjson(self):
        sample_rdjson = {
            "source": {"name": "apex-linter"},
            "diagnostics": [
                {
                    "message": "Potential bug",
                    "location": {
                        "path": "src/calc.py",
                        "range": {"start": {"line": 12, "column": 5}},
                    },
                    "severity": "WARNING",
                    "code": {"value": "RULE_01"},
                    "suggestions": [{"text": "z = 42"}],
                }
            ],
        }

        with tempfile.NamedTemporaryFile("w", suffix=".rdjson", delete=False) as f:
            json.dump(sample_rdjson, f)
            temp_path = Path(f.name)

        try:
            findings = parse_rdjson_file(temp_path)
            self.assertEqual(len(findings), 1)
            f0 = findings[0]
            self.assertEqual(f0.message, "Potential bug")
            self.assertEqual(f0.path, "src/calc.py")
            self.assertEqual(f0.line, 12)
            self.assertEqual(f0.column, 5)
            self.assertEqual(f0.severity, "WARNING")
            self.assertEqual(f0.rule_code, "RULE_01")
            self.assertEqual(f0.source_name, "apex-linter")
            self.assertEqual(f0.suggestion, "z = 42")
            self.assertIn("```suggestion", f0.to_markdown())
        finally:
            temp_path.unlink(missing_ok=True)


class PRReviewCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.diff_file = self.temp_path / "pr.diff"
        self.diff_file.write_text(SAMPLE_DIFF, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_output(self):
        findings_file = self.temp_path / "findings.rdjson"
        findings_file.write_text(
            json.dumps({
                "diagnostics": [
                    {
                        "message": "Security vulnerability",
                        "location": {"path": "src/calc.py", "range": {"start": {"line": 13}}},
                        "severity": "ERROR",
                        "code": {"value": "SEC01"},
                    }
                ]
            }),
            encoding="utf-8",
        )

        code = main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    def test_fail_on_error_trigger(self):
        # ERROR is on added line 13 -> exit code must be 1
        findings_file = self.temp_path / "findings_err.rdjson"
        findings_file.write_text(
            json.dumps({
                "diagnostics": [
                    {
                        "message": "Critical flaw",
                        "location": {"path": "src/calc.py", "range": {"start": {"line": 13}}},
                        "severity": "ERROR",
                    }
                ]
            }),
            encoding="utf-8",
        )

        code = main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 1)

    def test_fail_on_error_not_triggered_for_warning(self):
        # WARNING is on added line 12 -> exit code must be 0
        findings_file = self.temp_path / "findings_warn.rdjson"
        findings_file.write_text(
            json.dumps({
                "diagnostics": [
                    {
                        "message": "Minor style warning",
                        "location": {"path": "src/calc.py", "range": {"start": {"line": 12}}},
                        "severity": "WARNING",
                    }
                ]
            }),
            encoding="utf-8",
        )

        code = main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    def test_fail_on_error_not_triggered_when_error_outside_diff(self):
        # ERROR is on context line 10 -> outside added lines -> exit code must be 0
        findings_file = self.temp_path / "findings_outside.rdjson"
        findings_file.write_text(
            json.dumps({
                "diagnostics": [
                    {
                        "message": "Error on legacy line",
                        "location": {"path": "src/calc.py", "range": {"start": {"line": 10}}},
                        "severity": "ERROR",
                    }
                ]
            }),
            encoding="utf-8",
        )

        code = main([
            "--diff", str(self.diff_file),
            "--findings", str(findings_file),
            "--fail-on-error",
            "--dry-run",
        ])
        self.assertEqual(code, 0)

    def test_max_comments_capping(self):
        # Create 5 findings on added lines, cap at 2
        diagnostics = []
        for i in range(5):
            diagnostics.append({
                "message": f"Finding {i}",
                "location": {"path": "src/calc.py", "range": {"start": {"line": 12}}},
                "severity": "WARNING",
            })
        findings_file = self.temp_path / "findings_many.rdjson"
        findings_file.write_text(json.dumps({"diagnostics": diagnostics}), encoding="utf-8")

        summary = build_review_summary(
            total_findings=5,
            added_findings=[
                DiagnosticFinding(message=f"F{i}", path="src/calc.py", line=12) for i in range(5)
            ],
            skipped_count=0,
            max_comments=2,
        )
        self.assertIn("Displaying top 2 comments", summary)

    @patch("urllib.request.urlopen")
    def test_post_github_pr_review_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        ok = post_github_pr_review(
            repo="octocat/Hello-World",
            pr_number=42,
            token="ghp_fake_token",
            summary_body="Summary markdown",
            comments=[{"path": "src/calc.py", "line": 12, "side": "RIGHT", "body": "Comment"}],
            commit_sha="abcdef123456",
        )
        self.assertTrue(ok)
        self.assertTrue(mock_urlopen.called)


if __name__ == "__main__":
    unittest.main()
