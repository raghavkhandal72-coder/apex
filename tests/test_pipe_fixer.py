import tempfile
import unittest
from pathlib import Path

from apex_council.repair.pipe_fixer import extract_tests_for_file, parse_traceback, run_pipe_repair


class PipeFixerTests(unittest.TestCase):
    def test_parse_standard_python_traceback(self):
        tb = (
            "Traceback (most recent call last):\n"
            '  File "test_runner.py", line 15, in <module>\n'
            '  File "binary_search.py", line 4, in binary_search\n'
            "    while left < right:\n"
            "AssertionError: Expected 4 but got -1\n"
        )
        trace = parse_traceback(tb)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.target_file.name, "binary_search.py")
        self.assertEqual(trace.line_number, 4)
        self.assertEqual(trace.error_type, "AssertionError")

    def test_parse_pytest_traceback(self):
        tb = (
            "_____________________ test_search _____________________\n"
            ">       assert binary_search([1, 2, 3, 4, 5], 5) == 4\n"
            "E       assert -1 == 4\n"
            "\n"
            "binary_search.py:4: AssertionError\n"
        )
        trace = parse_traceback(tb)
        self.assertIsNotNone(trace)
        self.assertEqual(trace.target_file.name, "binary_search.py")
        self.assertEqual(trace.error_type, "AssertionError")
        self.assertIn("assert binary_search", trace.failing_assertion)

    def test_apply_pipe_repair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            target = tmp / "calculator.py"
            target.write_text(
                "def add_positive(a, b):\n"
                "    if a > 0 and b > 0:\n"
                "        return a - b\n"  # Buggy!
                "    return 0\n",
                encoding="utf-8",
            )
            tests = "assert add_positive(5, 3) == 8\nassert add_positive(1, 1) == 2\n"

            tb = f'File "{target}", line 3, in add_positive\nAssertionError\n'
            ret = run_pipe_repair(tb, apply_fix=True, tests_content=tests)
            self.assertEqual(ret, 0)

            # Check that file was patched
            fixed_src = target.read_text(encoding="utf-8")
            self.assertIn("return a + b", fixed_src)

            # Check backup exists
            bak = target.with_suffix(".py.bak")
            self.assertTrue(bak.exists())


if __name__ == "__main__":
    unittest.main()
