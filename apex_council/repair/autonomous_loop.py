"""
Apex Autonomous Closed-Loop Repair (Feature #100).
Test-Driven Synthesis: Test -> Traceback -> CEGIS Synthesis -> Invariant Verification -> In-Place Patch -> Re-Test.
Loops autonomously until 100% tests pass or max iterations reached.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from apex_council.repair.pipe_fixer import run_pipe_repair


def run_autonomous_loop(
    test_command: Optional[str] = None,
    max_iterations: int = 5,
    auto_commit: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Execute the closed-loop autonomous repair cycle until all tests pass."""
    if test_command is None:
        if os.path.isdir("tests"):
            test_command = f"{sys.executable} -m unittest discover -s tests"
        else:
            test_command = f"{sys.executable} -m unittest"

    print("=" * 64)
    print("        APEX AUTONOMOUS CLOSED-LOOP REPAIR")
    print("=" * 64)
    print(f"Target test suite : {test_command}")
    print(f"Max iterations    : {max_iterations}")
    print(f"Auto-commit       : {auto_commit}\n")

    repaired_files: List[str] = []
    start_time = time.time()

    for iteration in range(1, max_iterations + 1):
        print(f"--- Iteration {iteration}/{max_iterations} ---")
        print(f"[*] Running: {test_command}")

        proc = subprocess.run(test_command, shell=True, capture_output=True, text=True)
        if proc.stdout and verbose:
            print(proc.stdout.strip())
        if proc.stderr and verbose:
            print(proc.stderr.strip())

        # If tests pass, we are done!
        if proc.returncode == 0:
            elapsed = time.time() - start_time
            print("\n" + "=" * 64)
            print(f"[OK] ALL TESTS PASS! Autonomous loop achieved 100% green suite in {elapsed:.2f}s.")
            if repaired_files:
                print(f"Repaired files: {', '.join(repaired_files)}")
            print("=" * 64)
            return {
                "success": True,
                "iterations": iteration,
                "repaired_files": repaired_files,
                "elapsed": elapsed,
            }

        print(f"[!] Test suite failed (exit code {proc.returncode}). Intercepting crash traceback...")
        combined_output = f"{proc.stdout}\n{proc.stderr}"
        if "Traceback" not in combined_output:
            print("[FAIL] No Python traceback detected in test runner output. Halting loop.")
            return {
                "success": False,
                "iterations": iteration,
                "error": "No traceback found in failure output",
                "repaired_files": repaired_files,
            }

        from apex_council.repair.pipe_fixer import parse_traceback, run_pipe_repair

        trace = parse_traceback(combined_output)
        if not trace:
            print("[FAIL] Could not locate a target Python source file in traceback. Halting loop.")
            return {
                "success": False,
                "iterations": iteration,
                "error": "Could not locate target file in traceback",
                "repaired_files": repaired_files,
            }

        target_file = str(trace.target_file)
        ret_code = run_pipe_repair(trace_text=combined_output, apply_fix=True)
        if ret_code != 0:
            print("[FAIL] CEGIS synthesis could not find a sound patch within bounded grammar. Halting.")
            return {
                "success": False,
                "iterations": iteration,
                "error": "CEGIS synthesis failed",
                "repaired_files": repaired_files,
            }

        repaired_files.append(target_file)
        print(f"[OK] Synthesized sound patch for '{target_file}' and applied with .bak backup.")

        if auto_commit:
            try:
                subprocess.run(f"git add {target_file}", shell=True, check=True)
                commit_msg = f"fix(apex): autonomous repair of {os.path.basename(target_file)}"
                subprocess.run(f'git commit -m "{commit_msg}"', shell=True, check=True)
                print(f"[OK] Auto-committed fix: '{commit_msg}'")
            except Exception as e:
                print(f"[WARN] Auto-commit skipped: {e}")

        # Continue to next iteration to re-run test suite
        print("")

    elapsed = time.time() - start_time
    print(f"\n[FAIL] Autonomous loop reached max iterations ({max_iterations}) without reaching 100% pass.")
    return {
        "success": False,
        "iterations": max_iterations,
        "repaired_files": repaired_files,
        "elapsed": elapsed,
    }
