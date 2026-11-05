#!/usr/bin/env python3
"""
Apex-Sovereign: Bug Reproduction Oracle Synthesizer
Inspired by Agentless & Top SWE-Bench Verified Architectures
100% Pure Python Standard Library | Zero Dependencies

Synthesizes a minimal, hermetic `reproduce_issue.py` oracle script from raw
unstructured issue descriptions and stack traces. Verifies that the oracle:
1. FAILS on the baseline (bug reproduced).
2. PASSES on candidate patches (fix verified).
"""

from __future__ import annotations

import ast
import dataclasses
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class BugReproductionSpec:
    target_file: Optional[str]
    target_symbol: Optional[str]
    exception_type: Optional[str]
    reproduction_code: str
    assertion_expected: Optional[str]
    raw_issue_summary: str


class BugReproductionOracle:
    """
    Synthesizes and executes reproduction scripts to turn natural-language
    bug reports into deterministic PASS/FAIL test oracles.
    """

    # Common exception patterns in Python
    EXCEPTION_PATTERN = re.compile(
        r"\b(ZeroDivisionError|IndexError|KeyError|TypeError|ValueError|"
        r"AttributeError|AssertionError|FileNotFoundError|ImportError|"
        r"NameError|OverflowError|RecursionError|StopIteration|UnboundLocalError)\b"
    )
    TRACEBACK_FILE_PATTERN = re.compile(
        r'File ["\']([^"\']+\.py)["\'], line (\d+)(?:, in (\w+))?'
    )
    CODE_BLOCK_PATTERN = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
    CALL_PATTERN = re.compile(r"\b([a-zA-Z_]\w*)\s*\((.*?)\)")

    @classmethod
    def parse_issue(
        cls,
        issue_text: str,
        repo_files: Optional[List[str]] = None,
    ) -> BugReproductionSpec:
        """
        Parses an unstructured GitHub issue description and generates
        a target reproduction specification.
        """
        lines = [line.strip() for line in issue_text.splitlines() if line.strip()]
        summary = lines[0] if lines else "Autonomous Bug Report"

        # 1. Extract exception type if mentioned
        exc_match = cls.EXCEPTION_PATTERN.search(issue_text)
        exception_type = exc_match.group(1) if exc_match else None

        # 2. Extract file and line from traceback if present
        target_file: Optional[str] = None
        target_symbol: Optional[str] = None
        tb_matches = cls.TRACEBACK_FILE_PATTERN.findall(issue_text)
        if tb_matches:
            # Last frame in traceback is usually the crash site
            raw_path, line_no, func_name = tb_matches[-1]
            norm_path = raw_path.replace("\\", "/")
            if repo_files:
                for rf in repo_files:
                    if rf.endswith(norm_path) or norm_path.endswith(rf):
                        target_file = rf
                        break
            if not target_file:
                target_file = os.path.basename(norm_path)
            if func_name:
                target_symbol = func_name

        # If file not in traceback, try matching known repo files in issue text
        if not target_file and repo_files:
            for rf in repo_files:
                base = os.path.basename(rf)
                if base in issue_text:
                    target_file = rf
                    break

        # 3. Extract code blocks or minimal invocation snippets
        code_blocks = cls.CODE_BLOCK_PATTERN.findall(issue_text)
        code_snippet = ""
        assertion_expected = None

        if code_blocks:
            # Pick the shortest or most relevant python snippet
            code_snippet = max(code_blocks, key=lambda b: len(b.strip())).strip()
        else:
            # Try to find inline calls like `foo(1, 2)`
            calls = cls.CALL_PATTERN.findall(issue_text)
            if calls:
                func_name, args = calls[0]
                if not target_symbol:
                    target_symbol = func_name
                code_snippet = f"{func_name}({args})"

        # Check for assertions in the snippet or text
        assert_match = re.search(r"assert\s+([^\n]+)", issue_text)
        if assert_match:
            assertion_expected = assert_match.group(1).strip()

        # 4. Synthesize robust reproduction script
        repro_script = cls._synthesize_script(
            target_file=target_file,
            target_symbol=target_symbol,
            code_snippet=code_snippet,
            exception_type=exception_type,
            assertion_expected=assertion_expected,
        )

        return BugReproductionSpec(
            target_file=target_file,
            target_symbol=target_symbol,
            exception_type=exception_type,
            reproduction_code=repro_script,
            assertion_expected=assertion_expected,
            raw_issue_summary=summary,
        )

    @classmethod
    def _synthesize_script(
        cls,
        target_file: Optional[str],
        target_symbol: Optional[str],
        code_snippet: str,
        exception_type: Optional[str],
        assertion_expected: Optional[str],
    ) -> str:
        """Generates self-contained Python script designed to exit 0 on fix, !=0 on failure."""
        import_stmt = ""
        if target_file:
            mod_name = os.path.splitext(os.path.basename(target_file))[0]
            if target_symbol:
                import_stmt = f"try:\n    from {mod_name} import {target_symbol}\nexcept ImportError:\n    pass\n"
            else:
                import_stmt = f"try:\n    import {mod_name}\nexcept ImportError:\n    pass\n"

        body_lines: List[str] = []
        if code_snippet:
            # Clean snippet of markdown artifacts
            clean_snippet = "\n".join(
                line for line in code_snippet.splitlines() if not line.startswith(">>>")
            )
            body_lines.append(clean_snippet)

        if assertion_expected and assertion_expected not in code_snippet:
            body_lines.append(f"assert {assertion_expected}, 'Assertion failed'")

        if not body_lines and target_symbol:
            body_lines.append(f"result = {target_symbol}()")

        if not body_lines:
            body_lines.append("# No direct invocation extracted; checking module import")
            body_lines.append("pass")

        exec_block = "\n".join(f"    {line}" for line in "\n".join(body_lines).splitlines())

        script = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Auto-generated by Apex-Sovereign Bug Reproduction Oracle
# Exit 0 indicates BUG RESOLVED / TEST PASSED.
# Exit != 0 indicates BUG REPRODUCED / UNEXPECTED CRASH.

import sys
import os

# Add current workspace to path
sys.path.insert(0, os.path.abspath("."))

{import_stmt}
def run_reproduction_oracle():
{exec_block}

if __name__ == '__main__':
    try:
        run_reproduction_oracle()
        print("[ORACLE] Execution successful: Test passed cleanly.")
        sys.exit(0)
    except Exception as exc:
        print(f"[ORACLE] Defect reproduced: {{type(exc).__name__}}: {{exc}}", file=sys.stderr)
        sys.exit(1)
"""
        return script

    @classmethod
    def execute_oracle(
        cls,
        reproduction_code: str,
        cwd: str | os.PathLike = ".",
        timeout_sec: float = 10.0,
    ) -> Tuple[bool, int, str, str]:
        """
        Executes reproduction script in the given directory.
        Returns: (success: bool, returncode: int, stdout: str, stderr: str)
        success is True if returncode == 0.
        """
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix="_apex_oracle.py",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(reproduction_code)
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            success = proc.returncode == 0
            return (success, proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            return (False, -1, "", f"Timeout after {timeout_sec}s")
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    @classmethod
    def verify_patch(
        cls,
        reproduction_code: str,
        base_dir: str | os.PathLike,
        patch_dir: str | os.PathLike,
    ) -> Dict[str, object]:
        """
        Verifies that:
        1. Base directory fails the oracle (Defect reproduced: returncode != 0)
        2. Patch directory passes the oracle (Defect resolved: returncode == 0)
        """
        base_ok, base_code, base_out, base_err = cls.execute_oracle(
            reproduction_code, cwd=base_dir
        )
        patch_ok, patch_code, patch_out, patch_err = cls.execute_oracle(
            reproduction_code, cwd=patch_dir
        )

        reproduced = not base_ok
        resolved = patch_ok

        verified = reproduced and resolved
        return {
            "verified": verified,
            "defect_reproduced_on_baseline": reproduced,
            "defect_resolved_on_patch": resolved,
            "baseline_exit_code": base_code,
            "patch_exit_code": patch_code,
            "baseline_stderr": base_err.strip(),
            "patch_stdout": patch_out.strip(),
        }
