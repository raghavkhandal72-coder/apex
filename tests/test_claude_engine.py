#!/usr/bin/env python3
"""
Unit Test Suite for Claude-Inspired SWE-Bench Accelerator Engines
100% Pure Python Standard Library | Zero Dependencies
"""

import os
import pathlib
import tempfile
import unittest

from apex_council.claude_engine.oracle_synthesizer import BugReproductionOracle
from apex_council.claude_engine.ast_navigator import ASTSymbolNavigator
from apex_council.claude_engine.cognitive_memory import CognitiveMemoryStream, MemoryRecord
from apex_council.claude_engine.mini_swe_aci import MiniSWEAgentACI, ACIAction


class TestClaudeEngineSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="apex_claude_test_")
        self.workspace = pathlib.Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_bug_reproduction_oracle_extraction_and_synthesis(self) -> None:
        issue_text = """
        Bug: Division by zero when divisor is zero in compute_ratio
        Traceback (most recent call last):
          File "calculator.py", line 12, in compute_ratio
            return numerator / denominator
        ZeroDivisionError: division by zero

        How to reproduce:
        ```python
        compute_ratio(10, 0)
        ```
        """
        spec = BugReproductionOracle.parse_issue(issue_text, repo_files=["calculator.py"])
        self.assertEqual(spec.target_file, "calculator.py")
        self.assertEqual(spec.target_symbol, "compute_ratio")
        self.assertEqual(spec.exception_type, "ZeroDivisionError")
        self.assertIn("compute_ratio(10, 0)", spec.reproduction_code)
        self.assertIn("run_reproduction_oracle", spec.reproduction_code)

    def test_oracle_execution_fails_on_bug_and_passes_on_fix(self) -> None:
        # Create buggy module
        buggy_code = """
def safe_divide(a, b):
    return a // b
"""
        calc_file = self.workspace / "calculator.py"
        calc_file.write_text(buggy_code, encoding="utf-8")

        oracle_script = """
import sys
import os
sys.path.insert(0, os.path.abspath("."))
from calculator import safe_divide

if safe_divide(10, 2) != 5:
    sys.exit(1)

try:
    safe_divide(10, 0)
    # If it doesn't handle zero division, this line is reached on fix if default is returned
    sys.exit(0)
except ZeroDivisionError:
    # Bug reproduced!
    sys.exit(2)
"""
        # Run on baseline -> should fail with exit code 2
        ok, code, out, err = BugReproductionOracle.execute_oracle(
            oracle_script, cwd=self.workspace
        )
        self.assertFalse(ok)
        self.assertEqual(code, 2)

        # Apply fix
        fixed_code = """
def safe_divide(a, b):
    if b == 0:
        return 0
    return a // b
"""
        calc_file.write_text(fixed_code, encoding="utf-8")

        # Run on patched code -> should succeed with exit code 0
        ok2, code2, out2, err2 = BugReproductionOracle.execute_oracle(
            oracle_script, cwd=self.workspace
        )
        self.assertTrue(ok2)
        self.assertEqual(code2, 0)

    def test_ast_symbol_navigator_queries_and_callees(self) -> None:
        source = """
class DataVault:
    \"\"\"Manages persistent records.\"\"\"
    def __init__(self, capacity: int):
        self.capacity = capacity

    def save_record(self, key: str, value: str) -> bool:
        \"\"\"Saves a record.\"\"\"
        self._validate(key)
        return True

    def _validate(self, key: str) -> None:
        if not key:
            raise ValueError("Empty key")

def helper_func(x):
    return x * 2
"""
        file_path = self.workspace / "vault.py"
        file_path.write_text(source, encoding="utf-8")

        navigator = ASTSymbolNavigator(self.workspace)
        classes = navigator.search_class("DataVault")
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0].name, "DataVault")
        self.assertEqual(classes[0].docstring, "Manages persistent records.")

        methods = navigator.search_method("save_record")
        self.assertEqual(len(methods), 1)
        self.assertEqual(methods[0].parent_class, "DataVault")
        self.assertIn("key", methods[0].parameters)

        funcs = navigator.search_function("helper_func")
        self.assertEqual(len(funcs), 1)

        # Call hierarchy
        hier = navigator.get_call_hierarchy("DataVault.save_record")
        self.assertIn("_validate", hier.callees)

        # Context lines
        ctx = navigator.get_surrounding_context(str(file_path), target_line=9, window=2)
        self.assertIn("->    9 |", ctx)
        self.assertIn("def save_record", ctx)

    def test_cognitive_memory_stream_persistence_and_search(self) -> None:
        mem_file = self.workspace / "test_memory.json"
        stream = CognitiveMemoryStream(mem_file)

        # Record invariants
        stream.record_pattern(
            category="architectural_invariant",
            title="Zero Pip Dependencies",
            description="All modules must use only standard library components.",
            tags=["architecture", "zero-dependency"],
        )
        stream.record_pattern(
            category="bug_pattern",
            title="ReDoS Prevention",
            description="Avoid nested quantifiers in regular expressions.",
            code_example="re.compile(r'^[a-zA-Z0-9_-]+$')",
            tags=["security", "regex", "redos"],
        )

        # Search
        results = stream.search("regex security redos", top_k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "ReDoS Prevention")

        # Synthesize CLAUDE.md
        claude_md_path = self.workspace / "CLAUDE.md"
        content = stream.synthesize_claude_md(claude_md_path)
        self.assertTrue(claude_md_path.exists())
        self.assertIn("CLAUDE.md — Institutional Architecture", content)
        self.assertIn("Zero Pip Dependencies", content)
        self.assertIn("ReDoS Prevention", content)

    def test_mini_swe_aci_actions_and_linter_shield(self) -> None:
        sample_file = self.workspace / "sample.py"
        sample_file.write_text("x = 10\ny = 20\n", encoding="utf-8")

        aci = MiniSWEAgentACI(self.workspace)

        # 1. View file
        view_res = aci.dispatch(ACIAction("VIEW_FILE", {"path": "sample.py", "start_line": 1, "end_line": 2}))
        self.assertTrue(view_res.success)
        self.assertIn("x = 10", view_res.output)

        # 2. Lint syntax - Clean
        lint_ok = aci.dispatch(ACIAction("LINT_SYNTAX", {"code": "def foo():\n    return 42\n"}))
        self.assertTrue(lint_ok.success)

        # 3. Lint syntax - Syntax error caught immediately
        lint_err = aci.dispatch(ACIAction("LINT_SYNTAX", {"code": "def broken_syntax(\n"}))
        self.assertFalse(lint_err.success)
        self.assertIn("SyntaxError", lint_err.error)

        # 4. Apply replace with invalid syntax - Linter shield rejects edit!
        bad_replace = aci.dispatch(ACIAction("APPLY_REPLACE", {
            "path": "sample.py",
            "old_str": "y = 20",
            "new_str": "y = def invalid",
        }))
        self.assertFalse(bad_replace.success)
        self.assertIn("Replacement rejected by Linter-in-the-Loop", bad_replace.error)

        # File content must remain untouched
        self.assertEqual(sample_file.read_text(encoding="utf-8"), "x = 10\ny = 20\n")

        # 5. Apply clean replace
        good_replace = aci.dispatch(ACIAction("APPLY_REPLACE", {
            "path": "sample.py",
            "old_str": "y = 20",
            "new_str": "y = 50",
        }))
        self.assertTrue(good_replace.success)
        self.assertIn("y = 50", sample_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
