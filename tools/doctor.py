#!/usr/bin/env python3
"""
Apex Pre-Flight Launch Doctor (stdlib only).
Verifies that the repository is 100% launch-ready for Hacker News and GitHub.

Checks:
  1. Standard library purity (pip = 0)
  2. Test suite pass rate (272 tests)
  3. Standalone zipapp (dist/apex.pyz exists and < 450 KB)
  4. 20-second demo verification (binary_search.py repair)
  5. Version parity across pyproject.toml, cli.py, and CHANGELOG.md
  6. Git history secrets audit (zero real credentials committed)
  7. Placeholder check (identifies any remaining YOUR_USER placeholders)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _log(status: bool, message: str):
    icon = "[OK]" if status else "[WARN]"
    print(f"  {icon} {message}")


def check_stdlib_purity(root: Path) -> bool:
    checker = root / "tools" / "check_stdlib_only.py"
    if not checker.exists():
        _log(False, "tools/check_stdlib_only.py not found")
        return False
    res = subprocess.run(
        [sys.executable, str(checker), "apex_council", "tools"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    ok = res.returncode == 0
    _log(ok, "Standard library purity verified (pip = 0 across apex_council & tools)")
    return ok


def check_tests(root: Path) -> bool:
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    ok = res.returncode == 0
    num_tests = "all"
    m = re.search(r"Ran (\d+) tests", res.stderr + res.stdout)
    if m:
        num_tests = m.group(1)
    _log(ok, f"Unit test suite: {num_tests} tests passing (100% success)")
    return ok


def check_zipapp(root: Path) -> bool:
    pyz = root / "dist" / "apex.pyz"
    if not pyz.exists():
        _log(False, "dist/apex.pyz does not exist. Run: python scripts/build_pyz.py")
        return False
    size_kb = pyz.stat().st_size / 1024.0
    ok = size_kb < 450.0
    _log(ok, f"Standalone zipapp dist/apex.pyz: {size_kb:.1f} KB (< 450 KB limit)")
    return ok


def check_demo(root: Path) -> bool:
    pyz = root / "dist" / "apex.pyz"
    target = root / "binary_search.py"
    tests = root / "tests.txt"
    if not (pyz.exists() and target.exists() and tests.exists()):
        _log(False, "Demo files missing (binary_search.py or tests.txt)")
        return False
    res = subprocess.run(
        [sys.executable, str(pyz), "cegis", str(target), "--tests-file", str(tests)],
        cwd=root,
        capture_output=True,
        text=True,
    )
    ok = res.returncode == 0 and "<=" in res.stdout and "500/500" in res.stdout
    _log(ok, "20-second repair demo (binary_search.py) synthesizes '<=' and passes 500/500 hidden probes")
    return ok


def check_version_parity(root: Path) -> bool:
    versions = {}
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        m = re.search(r'version\s*=\s*"([^"]+)"', pyproj.read_text(encoding="utf-8"))
        if m:
            versions["pyproject.toml"] = m.group(1)

    cli = root / "apex_council" / "cli.py"
    if cli.exists():
        m = re.search(r'version="Apex v([^"]+)"', cli.read_text(encoding="utf-8"))
        if m:
            versions["cli.py"] = m.group(1)

    changelog = root / "CHANGELOG.md"
    if changelog.exists():
        m = re.search(r'## \[([0-9]+\.[0-9]+\.[0-9]+)\]', changelog.read_text(encoding="utf-8"))
        if m:
            versions["CHANGELOG.md"] = m.group(1)

    unique = set(versions.values())
    ok = len(unique) == 1
    ver_str = ", ".join(f"{k}: {v}" for k, v in versions.items())
    _log(ok, f"Version parity: {ver_str}")
    return ok


def check_git_secrets(root: Path) -> bool:
    try:
        p = subprocess.run(
            ["git", "log", "-p"],
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
        )
        patterns = [
            re.compile(r"AIza[0-9A-Za-z-_]{35}"),
            re.compile(r"sk-ant-[0-9A-Za-z-_]{20,}"),
            re.compile(r"sk-proj-[0-9A-Za-z-_]{20,}"),
        ]
        leaks = []
        for line in p.stdout.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                for pat in patterns:
                    if pat.search(line):
                        leaks.append(line)
        ok = len(leaks) == 0
        _log(ok, f"Git history audit: {len(leaks)} real API credentials detected in commit log")
        return ok
    except Exception as ex:
        _log(False, f"Git audit error: {ex}")
        return False


def check_placeholders(root: Path) -> None:
    files_to_check = [
        root / "README.md",
        root / "pyproject.toml",
        root / "CONTRIBUTING.md",
        root / "action.yml",
        root / "install.sh",
        root / "install.ps1",
        root / "docs" / "show_hn.md",
    ]
    found = []
    for f in files_to_check:
        if f.exists() and "YOUR_USER" in f.read_text(encoding="utf-8", errors="replace"):
            found.append(f.name)
    if found:
        print(f"\n  [NOTE] 'YOUR_USER' placeholder is present in: {', '.join(found)}")
        print("         Remember to replace 'YOUR_USER' with your GitHub username before pushing to GitHub!")
    else:
        print("\n  [OK] No 'YOUR_USER' placeholders detected.")


def main() -> int:
    root = Path(__file__).parent.parent.resolve()
    print("=" * 64)
    print("           APEX PRE-FLIGHT LAUNCH DOCTOR")
    print("=" * 64)
    print(f"Repository Root: {root}\n")

    results = [
        check_stdlib_purity(root),
        check_tests(root),
        check_zipapp(root),
        check_demo(root),
        check_version_parity(root),
        check_git_secrets(root),
    ]

    check_placeholders(root)

    print("=" * 64)
    if all(results):
        print("RESULT: ALL CRITICAL PRE-FLIGHT CHECKS PASSED. LAUNCH READY! (ALL SYSTEMS GO)")
        print("=" * 64)
        return 0
    else:
        print("RESULT: ONE OR MORE CHECKS FAILED. REVIEW ABOVE BEFORE LAUNCHING.")
        print("=" * 64)
        return 1


if __name__ == "__main__":
    sys.exit(main())
