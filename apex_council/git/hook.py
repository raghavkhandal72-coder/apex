"""
Apex Self-Healing Git Pre-Commit Hook.
Intercepts broken commits, isolates the staged regression,
synthesizes a 1-token fix via CEGIS, stages the fix, and allows the commit to succeed!
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from apex_council.repair.pipe_fixer import extract_tests_for_file
from apex_council.synthesis.cegis_engine import CEGISEngine


HOOK_START = "# --- APEX SELF-HEALING PRE-COMMIT HOOK START ---"
HOOK_END = "# --- APEX SELF-HEALING PRE-COMMIT HOOK END ---"

HOOK_BLOCK = f"""{HOOK_START}
if command -v apex >/dev/null 2>&1; then
    apex hook run
elif [ -f "dist/apex.pyz" ]; then
    python dist/apex.pyz hook run
else
    python -m apex_council.cli hook run
fi
{HOOK_END}"""


def install_hook(repo_root: Optional[Path] = None) -> bool:
    root = repo_root or Path.cwd()
    hooks_dir = root / ".git" / "hooks"
    if not hooks_dir.parent.exists():
        sys.stderr.write(f"Error: {root} does not appear to be a git repository.\n")
        return False

    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    if hook_file.exists():
        content = hook_file.read_text(encoding="utf-8", errors="replace")
        if HOOK_START in content:
            print("Apex self-healing pre-commit hook is already installed.")
            return True
        hook_file.write_text(content.strip() + "\n\n" + HOOK_BLOCK + "\n", encoding="utf-8")
    else:
        hook_file.write_text("#!/usr/bin/env bash\n" + HOOK_BLOCK + "\n", encoding="utf-8")

    try:
        hook_file.chmod(0o755)
    except Exception:
        pass

    print(f"[OK] Self-healing pre-commit hook installed to: {hook_file}")
    return True


def uninstall_hook(repo_root: Optional[Path] = None) -> bool:
    root = repo_root or Path.cwd()
    hook_file = root / ".git" / "hooks" / "pre-commit"
    if not hook_file.exists():
        print("No pre-commit hook found to uninstall.")
        return True

    content = hook_file.read_text(encoding="utf-8", errors="replace")
    if HOOK_START not in content:
        print("Apex hook is not present in pre-commit hook.")
        return True

    # Remove the apex block between HOOK_START and HOOK_END
    in_block = False
    new_lines = []
    for line in content.splitlines():
        if HOOK_START in line:
            in_block = True
            continue
        if HOOK_END in line:
            in_block = False
            continue
        if not in_block:
            new_lines.append(line)

    cleaned = "\n".join(new_lines).strip()
    if not cleaned or cleaned == "#!/usr/bin/env bash":
        hook_file.unlink()
    else:
        hook_file.write_text(cleaned + "\n", encoding="utf-8")

    print("[OK] Apex pre-commit hook successfully uninstalled.")
    return True


def get_staged_python_files(repo_root: Path) -> List[Path]:
    """Returns list of staged Python files."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return [
            repo_root / p.strip()
            for p in res.stdout.splitlines()
            if p.strip().endswith(".py") and (repo_root / p.strip()).exists()
        ]
    except Exception:
        return []


def run_tests_check(repo_root: Path) -> Tuple[bool, str]:
    """Runs test suite (tests.txt, unittest, or pytest) and returns (passed, output)."""
    # 1. Check if tests.txt exists
    tests_txt = repo_root / "tests.txt"
    if tests_txt.exists():
        staged = get_staged_python_files(repo_root)
        if staged:
            target = staged[0]
            code = target.read_text(encoding="utf-8", errors="replace")
            harness = f"{code}\n\n{tests_txt.read_text(encoding='utf-8', errors='replace')}"
            res = subprocess.run([sys.executable, "-c", harness], capture_output=True, text=True)
            return res.returncode == 0, res.stderr + res.stdout

    # 2. Try unittest
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return res.returncode == 0, res.stderr + res.stdout


def run_pre_commit_hook(repo_root: Optional[Path] = None) -> int:
    """Executes the self-healing pre-commit hook workflow."""
    root = repo_root or Path.cwd()
    staged_py = get_staged_python_files(root)
    if not staged_py:
        return 0

    passed, out = run_tests_check(root)
    if passed:
        return 0

    print("[Apex Pre-Commit] Test failure detected on staged files. Attempting self-healing repair...")

    engine = CEGISEngine()
    healed_any = False

    for target_file in staged_py:
        if target_file.name.startswith("test_"):
            continue

        src = target_file.read_text(encoding="utf-8", errors="replace")
        tests = extract_tests_for_file(target_file)
        if not tests.strip():
            continue

        rep = engine.synthesize_and_verify(src, tests)
        if rep.success:
            target_file.write_text(rep.synthesized_code, encoding="utf-8")
            subprocess.run(["git", "add", str(target_file)], cwd=root, check=True)
            print(f"[Apex Pre-Commit] [OK] Auto-healed regression in {target_file.name}!")
            healed_any = True

    if healed_any:
        # Re-verify tests
        re_passed, _ = run_tests_check(root)
        if re_passed:
            print("[Apex Pre-Commit] All tests now pass! Amending repair into staged commit.")
            return 0

    sys.stderr.write("[Apex Pre-Commit] Could not automatically heal all failing tests. Commit aborted.\n")
    if out:
        sys.stderr.write(out + "\n")
    return 1
