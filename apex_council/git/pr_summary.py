"""
Apex PR Summary Generator (Feature #51).
Inspects Git diffs and AST changes to generate high-density, professional GitHub PR descriptions.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_git_diff(base_ref: Optional[str] = None) -> str:
    """Capture unified git diff against base_ref or uncommitted staged/unstaged changes."""
    cmd = ["git", "diff"]
    if base_ref:
        cmd.append(base_ref)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return proc.stdout
    except Exception:
        # Fallback to git diff HEAD
        try:
            proc = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True, check=True)
            return proc.stdout
        except Exception:
            return ""


def parse_diff_files(diff_text: str) -> List[Dict[str, Any]]:
    """Parse unified diff text into structured file change summaries."""
    files: List[Dict[str, Any]] = []
    current_file: Optional[Dict[str, Any]] = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                files.append(current_file)
            parts = line.split()
            path_b = parts[-1].lstrip("b/") if len(parts) >= 4 else "unknown"
            current_file = {
                "file": path_b,
                "added": 0,
                "deleted": 0,
                "added_lines": [],
            }
        elif current_file is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current_file["added"] += 1
                current_file["added_lines"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_file["deleted"] += 1

    if current_file:
        files.append(current_file)
    return files


def generate_pr_summary_markdown(
    diff_text: str,
    title: Optional[str] = None,
    base_ref: Optional[str] = None,
) -> str:
    """Generate professional Markdown PR summary."""
    files = parse_diff_files(diff_text)
    if not files:
        return "## Apex PR Summary\n\nNo changes detected in git diff."

    total_added = sum(f["added"] for f in files)
    total_deleted = sum(f["deleted"] for f in files)

    # Detect touched functions and classes from added lines
    touched_symbols: List[str] = []
    for f in files:
        for added_l in f["added_lines"]:
            m = re.search(r"^\s*(def|class)\s+([A-Za-z0-9_]+)", added_l)
            if m:
                touched_symbols.append(f"`{m.group(2)}` ({f['file']})")

    # Risk heuristic
    risk_level = "LOW"
    if any("security" in f["file"].lower() or "auth" in f["file"].lower() for f in files):
        risk_level = "HIGH"
    elif total_added + total_deleted > 200:
        risk_level = "MEDIUM"

    md = [
        f"## {title or 'PR: Automated Code Changes Summary'}",
        "",
        "> Generated automatically by **Apex PR Summary** (zero-dependency git inspector).",
        "",
        "### 📊 Changes Overview",
        f"- **Files Modified:** {len(files)}",
        f"- **Lines Added:** `+{total_added}`",
        f"- **Lines Deleted:** `-{total_deleted}`",
        f"- **Risk Assessment:** **{risk_level}**",
        "",
        "### 📁 Modified Files",
        "| File | Added | Deleted | Status |",
        "| :--- | :---: | :---: | :---: |",
    ]

    for f in files:
        md.append(f"| `{f['file']}` | `+{f['added']}` | `-{f['deleted']}` | Modified |")

    if touched_symbols:
        md.extend([
            "",
            "### 🧩 Key Touched Symbols",
            ", ".join(touched_symbols[:10]) + ("..." if len(touched_symbols) > 10 else ""),
        ])

    md.extend([
        "",
        "### ✅ Verification Checklist",
        "- [ ] Unit tests pass cleanly (`python -m unittest discover -s tests`)",
        "- [ ] Standard library purity verified (`pip = 0`)",
        "- [ ] Zero new external dependencies introduced",
        "- [ ] CI/CD reviewdog diff check passing",
        "",
    ])

    return "\n".join(md)
