from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Any

from ..engine import CouncilEngine
from ..reporter import CouncilReporter


def review_git_diff(target_dir: Path | str = ".", staged_only: bool = False, force_offline: bool = False) -> Dict[str, Any]:
    """Inspects git changes and convenes the Supreme Council on the diff."""
    cmd = ["git", "diff", "--cached"] if staged_only else ["git", "diff", "HEAD"]
    
    try:
        proc = subprocess.run(cmd, cwd=str(target_dir), capture_output=True, encoding="utf-8", errors="replace", check=False)
        diff_output = proc.stdout.strip()
    except Exception as e:
        diff_output = ""

    if not diff_output:
        # Check unstaged working directory diff if HEAD diff was empty
        try:
            proc2 = subprocess.run(["git", "diff"], cwd=str(target_dir), capture_output=True, encoding="utf-8", errors="replace", check=False)
            diff_output = proc2.stdout.strip()
        except Exception:
            diff_output = ""

    if not diff_output:
        return {
            "status": "clean",
            "message": "No uncommitted git changes detected in working tree.",
            "council_result": None,
        }

    # Convene council on git diff
    prompt = (
        f"Perform an exhaustive Pre-Commit Security & Quality Review on this git diff.\n"
        f"Detect security regressions, breaking changes, missing exception handling, or anti-patterns.\n\n"
        f"Git Diff:\n```diff\n{diff_output[:4000]}\n```"
    )

    engine = CouncilEngine(force_offline=force_offline)
    result = engine.convene_council(prompt)

    return {
        "status": "reviewed",
        "diff_length": len(diff_output),
        "council_result": result,
    }
