"""
Apex Watcher: Zero-dependency file watcher and continuous test/repair loop.
Monitors Python files for modifications and triggers automated testing and CEGIS repair.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Set

from apex_council.repair.pipe_fixer import run_pipe_repair


IGNORED_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    "dist",
    "build",
    "site-packages",
}

IGNORED_EXTENSIONS: Set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".bak",
    ".swp",
    ".tmp",
}


def scan_mtimes(path: str) -> Dict[str, int]:
    """Scan directory or file and return map of absolute file path to modification timestamp (ns)."""
    mtimes: Dict[str, int] = {}
    if os.path.isfile(path):
        try:
            mtimes[os.path.abspath(path)] = os.stat(path).st_mtime_ns
        except OSError:
            pass
        return mtimes

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORED_EXTENSIONS or not file.endswith(".py"):
                continue
            full_path = os.path.join(root, file)
            try:
                mtimes[os.path.abspath(full_path)] = os.stat(full_path).st_mtime_ns
            except OSError:
                pass
    return mtimes


def detect_changes(prev_mtimes: Dict[str, int], current_mtimes: Dict[str, int]) -> List[str]:
    """Identify files that are added or modified between two scans."""
    changed: List[str] = []
    for file, mtime in current_mtimes.items():
        if file not in prev_mtimes:
            changed.append(file)
        elif prev_mtimes[file] != mtime:
            changed.append(file)
    return changed


def run_watch_loop(
    target_path: str = ".",
    command: Optional[str] = None,
    interval: float = 0.5,
    auto_fix: bool = False,
    once: bool = False,
    on_change_callback: Optional[Callable[[List[str]], None]] = None,
) -> int:
    """Run watch loop over target_path.
    
    If command is None, defaults to 'python -m unittest discover -s tests'.
    If auto_fix is True and the command fails with a traceback, invokes CEGIS repair.
    """
    if command is None:
        if os.path.isdir("tests"):
            command = f"{sys.executable} -m unittest discover -s tests"
        else:
            command = f"{sys.executable} -m unittest"

    abs_target = os.path.abspath(target_path)
    print(f"[APEX WATCH] Watching '{abs_target}' (interval: {interval}s)")
    print(f"[APEX WATCH] Trigger command: {command}")
    print("[APEX WATCH] Press Ctrl+C to stop.\n")

    prev_mtimes = scan_mtimes(abs_target)

    # Initial run
    _execute_watch_action(command, auto_fix)
    if once:
        return 0

    try:
        while True:
            time.sleep(interval)
            current_mtimes = scan_mtimes(abs_target)
            changed = detect_changes(prev_mtimes, current_mtimes)
            if changed:
                prev_mtimes = current_mtimes
                rel_names = [os.path.relpath(f, os.getcwd()) for f in changed]
                print(f"\n[APEX WATCH] Change detected in {', '.join(rel_names)}")
                if on_change_callback:
                    on_change_callback(changed)
                _execute_watch_action(command, auto_fix)
    except KeyboardInterrupt:
        print("\n[APEX WATCH] Stopped by user.")
        return 0


def _execute_watch_action(command: str, auto_fix: bool) -> int:
    """Execute the configured command and optionally trigger auto-repair on failure."""
    print(f"--> Running: {command}")
    start = time.time()
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start

    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())

    if proc.returncode == 0:
        print(f"[OK] Tests passed in {elapsed:.2f}s\n")
        return 0

    print(f"[FAIL] Command failed with exit code {proc.returncode} in {elapsed:.2f}s")
    if auto_fix:
        combined_output = f"{proc.stdout}\n{proc.stderr}"
        if "Traceback" in combined_output:
            print("[APEX WATCH] Attempting automated CEGIS repair on detected traceback...")
            ret = run_pipe_repair(trace_text=combined_output, apply_fix=True)
            if ret == 0:
                print("[APEX WATCH] Successfully applied repair! Re-running tests...")
                proc_retry = subprocess.run(command, shell=True, capture_output=True, text=True)
                if proc_retry.returncode == 0:
                    print("[APEX WATCH] All tests pass after repair!")
                    return 0
    return proc.returncode
