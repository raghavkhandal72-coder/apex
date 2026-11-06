"""
Apex Pipe Fixer: Parses raw tracebacks / test failure logs from stdin or files,
identifies the crash site, synthesizes a 1-token minimal repair via CEGIS,
and optionally applies the fix in-place with a backup.

Usage:
  pytest | apex fix
  python test.py 2>&1 | apex fix --apply
  apex fix failure.log --apply
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from apex_council.synthesis.cegis_engine import CEGISEngine
from apex_council.ui.repair_report import render_repair


@dataclass
class FailureTrace:
    target_file: Path
    line_number: Optional[int]
    error_type: str
    error_message: str
    failing_assertion: Optional[str] = None


def parse_traceback(trace_text: str) -> Optional[FailureTrace]:
    """Extracts target source file, line number, and failure error from raw traceback/log."""
    if not trace_text or not trace_text.strip():
        return None

    # Pattern 1: Standard Python traceback: File "path/to/file.py", line 12, in func
    py_tb_files = re.findall(
        r'File\s+"([^"]+\.py)",\s+line\s+(\d+)',
        trace_text,
    )

    # Pattern 2: Pytest format: path/to/file.py:12: ExceptionType
    pytest_matches = re.findall(
        r'([\w\-./\\]+\.py):(\d+):\s+([\w\.]+Error|AssertionError)',
        trace_text,
    )

    # Detect error message / exception
    err_match = re.search(
        r"([\w\.]+Error|Exception):\s*(.*)",
        trace_text,
    )
    err_type = err_match.group(1) if err_match else "AssertionError"
    err_msg = err_match.group(2).strip() if err_match else ""

    # Detect failing assert expression: e.g. ">       assert binary_search(...) == ..."
    assert_match = re.search(r">\s*(assert\s+.*)", trace_text)
    failing_assert = assert_match.group(1).strip() if assert_match else None

    # Determine most likely target file (prefer non-test source files or last frame)
    target_path = None
    line_no = None

    if pytest_matches:
        for f, ln, err in reversed(pytest_matches):
            p = Path(f)
            if p.exists() and not p.name.startswith("test_") and not p.name.endswith("_test.py"):
                target_path = p
                line_no = int(ln)
                err_type = err
                break
        if not target_path and pytest_matches:
            target_path = Path(pytest_matches[-1][0])
            line_no = int(pytest_matches[-1][1])
    elif py_tb_files:
        for f, ln in reversed(py_tb_files):
            p = Path(f)
            if p.exists() and not p.name.startswith("test_") and not p.name.endswith("_test.py"):
                target_path = p
                line_no = int(ln)
                break
        if not target_path and py_tb_files:
            target_path = Path(py_tb_files[-1][0])
            line_no = int(py_tb_files[-1][1])

    if not target_path or not target_path.exists():
        # Fallback: search for any .py file mentioned that exists
        for match in re.findall(r"([\w\-./\\]+\.py)", trace_text):
            p = Path(match)
            if p.exists() and not p.name.startswith("test_") and not p.name.endswith("_test.py"):
                target_path = p
                break

    # If target_path is a test file, inspect it to find the implementation module being tested
    if target_path and (target_path.name.startswith("test_") or target_path.name.endswith("_test.py")):
        try:
            test_content = target_path.read_text(encoding="utf-8", errors="replace")
            for mod in re.findall(r"(?:from|import)\s+([A-Za-z0-9_]+)", test_content):
                cand = target_path.parent / f"{mod}.py"
                if cand.exists() and cand != target_path:
                    target_path = cand
                    break
        except Exception:
            pass

    if not target_path or not target_path.exists():
        return None

    return FailureTrace(
        target_file=target_path,
        line_number=line_no,
        error_type=err_type,
        error_message=err_msg,
        failing_assertion=failing_assert,
    )


def extract_tests_for_file(target_file: Path, fallback_assert: Optional[str] = None) -> str:
    """Finds associated tests file (tests.txt, test_<file>.py) or uses fallback assertion."""
    stem = target_file.stem
    parent = target_file.parent

    # Candidate 1: tests.txt in same directory or root
    candidates = [
        parent / "tests.txt",
        Path("tests.txt"),
        parent / f"test_{stem}.py",
        parent / f"{stem}_test.py",
        Path("tests") / f"test_{stem}.py",
    ]

    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8", errors="replace")

    if fallback_assert:
        return fallback_assert

    return ""


def run_pipe_repair(
    trace_text: str,
    apply_fix: bool = False,
    tests_content: Optional[str] = None,
) -> int:
    """Executes pipe repair from raw traceback text."""
    trace = parse_traceback(trace_text)
    if not trace:
        sys.stderr.write("Apex Pipe Fixer: Could not locate a target Python source file in traceback.\n")
        return 1

    target_file = trace.target_file
    buggy_src = target_file.read_text(encoding="utf-8", errors="replace")

    tests = tests_content or extract_tests_for_file(target_file, trace.failing_assertion)
    if not tests.strip():
        sys.stderr.write(
            f"Apex Pipe Fixer: Located target {target_file}, but could not find a test suite or assert.\n"
            f"Provide tests via --tests-file or create tests.txt.\n"
        )
        return 1

    engine = CEGISEngine()
    rep = engine.synthesize_and_verify(buggy_src, tests)

    # Count visible tests
    test_units = [l.strip() for l in tests.splitlines() if l.strip().startswith("assert")]
    total_vis = max(1, len(test_units))
    visible = (total_vis, total_vis) if rep.success else (0, total_vis)

    output = render_repair(
        buggy_src=buggy_src,
        fixed_src=rep.synthesized_code if rep.success else buggy_src,
        filename=target_file.name,
        visible=visible,
        seconds=rep.duration_ms / 1000.0,
        candidates=rep.total_candidates_explored,
    )
    print(output)

    if rep.success:
        if apply_fix:
            bak_path = target_file.with_suffix(target_file.suffix + ".bak")
            shutil.copyfile(target_file, bak_path)
            target_file.write_text(rep.synthesized_code, encoding="utf-8")
            print(f"\n[APEX PIPE] Applied 1-token fix to {target_file} (backup: {bak_path.name}).")
        else:
            print("\n--- SYNTHESIZED REPAIRED CODE ---")
            print(rep.synthesized_code)
            print("==========================================================")
            print("\nTip: Re-run with '--apply' to patch the file in-place.")
        return 0
    else:
        print("\nApex was unable to synthesize a sound repair within the bounded grammar.")
        return 1
