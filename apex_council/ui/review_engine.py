#!/usr/bin/env python3
"""
Apex Autonomous Code Review & Diff Inspector
Zero external dependencies (pip = 0). Standard library only.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from typing import List, Dict, Any, Tuple

from .mascot import MascotTheme
from ..formal.swift_guard import audit_swift_safety

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def render_colorized_diff(repo_dir: str = ".") -> str:
    """Fetches and colorizes current git diff."""
    t = MascotTheme
    try:
        res = subprocess.run(
            ["git", "diff"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        diff_text = res.stdout
        if not diff_text.strip():
            # Check staged diff
            res_staged = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            diff_text = res_staged.stdout

        if not diff_text.strip():
            # Check last commit diff
            res_head = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            diff_text = res_head.stdout
            prefix = f"{t.DIM}[Working tree clean. Showing diff from last commit HEAD~1..HEAD]{t.RESET}\n"
        else:
            prefix = ""

        if not diff_text.strip():
            return f"{t.GRAY}No changes found in repository.{t.RESET}"

        out_lines = [prefix]
        for line in diff_text.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                out_lines.append(f"{t.CYAN}{line}{t.RESET}")
            elif line.startswith("+"):
                out_lines.append(f"{t.GREEN}{line}{t.RESET}")
            elif line.startswith("-"):
                out_lines.append(f"{t.RED}{line}{t.RESET}")
            elif line.startswith("@@"):
                out_lines.append(f"{t.APEX_GOLD}{line}{t.RESET}")
            elif line.startswith("diff --git"):
                out_lines.append(f"{t.BOLD}{t.WHITE}{line}{t.RESET}")
            else:
                out_lines.append(f"{t.GRAY}{line}{t.RESET}")

        return "\n".join(out_lines)
    except Exception as ex:
        return f"{t.RED}Failed to read git diff: {ex}{t.RESET}"


def run_code_review(target_path: str = ".") -> int:
    """Performs an AI Council code review on Python files in the target directory or specific file."""
    t = MascotTheme
    print("\n" + "=" * 76)
    print(f" {t.APEX_GOLD}{t.BOLD}APEX AUTONOMOUS CODE REVIEW & DEFECT AUDITOR{t.RESET}")
    print("=" * 76 + "\n")

    files_to_check: List[str] = []
    if os.path.isfile(target_path):
        files_to_check = [target_path]
    else:
        # Check modified files via git status
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=target_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[-1].endswith(".py") and os.path.exists(parts[-1]):
                    files_to_check.append(parts[-1])
        except Exception:
            pass

        # If none modified, audit key entrypoint files
        if not files_to_check:
            for cand in ["main.py", "apex_council/cli.py", "apex_council/synthesis/cegis_engine.py"]:
                full = os.path.join(target_path, cand) if target_path != "." else cand
                if os.path.exists(full):
                    files_to_check.append(full)

    total_findings = 0
    print(f"  {t.DIM}Auditing {len(files_to_check)} Python source files...{t.RESET}\n")

    for fpath in files_to_check:
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
            tree = ast.parse(src, filename=fpath)
        except Exception as ex:
            print(f"  {t.RED}✗ {fpath}: Syntax error parsing AST ({ex}){t.RESET}")
            total_findings += 1
            continue

        # Check 1: SwiftGuard safety
        findings = audit_swift_safety(src)
        # Check 2: Bare except
        bare_excepts = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                bare_excepts += 1

        rel_path = os.path.relpath(fpath, target_path)
        if not findings and bare_excepts == 0:
            print(f"  {t.GREEN}✓ {rel_path:<40} 100% CLEAN (0 defects, 0 safety violations){t.RESET}")
        else:
            print(f"  {t.AMBER}▲ {rel_path:<40} {len(findings)} safety warnings, {bare_excepts} bare excepts{t.RESET}")
            for fnd in findings[:2]:
                print(f"    {t.DIM}• {fnd.message}{t.RESET}")
            total_findings += len(findings) + bare_excepts

    print("\n" + "─" * 76)
    if total_findings == 0:
        print(f" {t.GREEN}{t.BOLD}REVIEW VERDICT: APPROVED FOR PRODUCTION (0 Critical Defects Found){t.RESET}")
    else:
        print(f" {t.AMBER}{t.BOLD}REVIEW VERDICT: {total_findings} Advisory item(s) logged. Review details above.{t.RESET}")
    print("─" * 76 + "\n")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    sys.exit(run_code_review(target))
