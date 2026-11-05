#!/usr/bin/env python3
"""
Apex-Sovereign: Pre-Landing Gatekeeper Review
Inspired by garrytan/gstack (review/checklist.md)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import ast
import dataclasses
import os
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class PreLandingIssue:
    category: str  # Gate Integrity, Shell Injection, Completeness Gap, Platform Fit
    severity: str  # ERROR, WARNING, INFO
    file_path: str
    line_number: Optional[int]
    message: str
    suggested_fix: str


@dataclasses.dataclass(frozen=True)
class PreLandingReviewReport:
    pr_type: str  # docs-only, CI/infra, scripts/tooling, application, mixed
    passed: bool
    score: float  # 0.0 to 10.0
    issues: List[PreLandingIssue]
    checklist_status: Dict[str, bool]
    verdict_summary: str


class PreLandingReviewEngine:
    """
    Executes the gstack Pre-Landing Checklist before merging or shipping PRs.
    """

    @classmethod
    def classify_pr_type(cls, file_paths: List[str]) -> str:
        """Determines the PR type from the list of changed files."""
        if not file_paths:
            return "application"

        types: set[str] = set()
        for p in file_paths:
            ext = os.path.splitext(p)[1].lower()
            norm = p.replace("\\", "/").lower()

            if ext in {".md", ".txt", ".rst"} and not any(k in norm for k in ["prompt", "skill", "template"]):
                types.add("docs-only")
            elif any(k in norm for k in [".github", "dockerfile", "docker-compose", "k8s", "helm", "terraform"]):
                types.add("CI/infra")
            elif ext in {".sh", ".bash", ".bat", ".cmd", ".ps1"} or "makefile" in norm:
                types.add("scripts/tooling")
            else:
                types.add("application")

        if len(types) == 1:
            return list(types)[0]
        return "mixed"

    @classmethod
    def review_diff(cls, file_paths: List[str], diff_or_code: str) -> PreLandingReviewReport:
        pr_type = cls.classify_pr_type(file_paths)
        issues: List[PreLandingIssue] = []
        checklist = {
            "Gate Integrity": True,
            "Shell Injection & Security": True,
            "Completeness Gaps": True,
            "Platform Fit & Conventions": True,
        }

        lines = diff_or_code.splitlines()

        for idx, line in enumerate(lines, 1):
            # 1. Shell Injection check
            if re.search(r"subprocess\.(?:Popen|run|call)\s*\(.*shell\s*=\s*True", line):
                checklist["Shell Injection & Security"] = False
                issues.append(
                    PreLandingIssue(
                        category="Shell Injection & Security",
                        severity="ERROR",
                        file_path=file_paths[0] if file_paths else "unknown",
                        line_number=idx,
                        message="subprocess with shell=True is susceptible to command injection",
                        suggested_fix="Set shell=False and pass arguments as an explicit list",
                    )
                )

            # 2. Path Traversal check
            if re.search(r"\.\./\.\.", line) and not line.strip().startswith("#"):
                issues.append(
                    PreLandingIssue(
                        category="Shell Injection & Security",
                        severity="WARNING",
                        file_path=file_paths[0] if file_paths else "unknown",
                        line_number=idx,
                        message="Relative path traversal '../..' pattern detected",
                        suggested_fix="Resolve paths using pathlib.Path(p).resolve() and verify root boundary",
                    )
                )

            # 3. Completeness Gaps: TODO / FIXME left in production code
            if re.search(r"\b(?:TODO|FIXME|XXX|HACK)\b", line, re.IGNORECASE) and not line.strip().startswith("#!"):
                issues.append(
                    PreLandingIssue(
                        category="Completeness Gaps",
                        severity="WARNING",
                        file_path=file_paths[0] if file_paths else "unknown",
                        line_number=idx,
                        message="Unresolved TODO/FIXME marker found in PR diff",
                        suggested_fix="Resolve implementation before landing or convert to tracked issue",
                    )
                )

            # 4. Platform Fit: Hardcoded Windows or POSIX paths
            if re.search(r"[A-Z]:\\[Users|Program Files]", line) and not line.strip().startswith("#"):
                checklist["Platform Fit & Conventions"] = False
                issues.append(
                    PreLandingIssue(
                        category="Platform Fit & Conventions",
                        severity="ERROR",
                        file_path=file_paths[0] if file_paths else "unknown",
                        line_number=idx,
                        message="Hardcoded absolute local Windows path detected",
                        suggested_fix="Use dynamic relative Path.cwd() or os.path.expanduser('~')",
                    )
                )

        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warn_count = sum(1 for i in issues if i.severity == "WARNING")

        score = max(0.0, 10.0 - (error_count * 2.5) - (warn_count * 0.5))
        passed = error_count == 0

        summary = (
            f"Pre-Landing Review: PR Type [{pr_type.upper()}] PASSED ({score:.1f}/10.0). Ready for merge."
            if passed
            else f"Pre-Landing Review: PR Type [{pr_type.upper()}] BLOCKED ({score:.1f}/10.0). Found {error_count} blocking errors."
        )

        return PreLandingReviewReport(
            pr_type=pr_type,
            passed=passed,
            score=score,
            issues=issues,
            checklist_status=checklist,
            verdict_summary=summary,
        )
