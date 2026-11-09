from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..engine import CouncilEngine
from ..reporter import CouncilReporter


@dataclass
class GitHubPRInfo:
    owner: str
    repo: str
    pr_number: int
    title: str
    diff_text: str


def parse_github_pr_url(pr_url_or_shorthand: str) -> Tuple[str, str, int]:
    """Parses https://github.com/owner/repo/pull/123 or owner/repo#123."""
    # Match URL
    match_url = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url_or_shorthand)
    if match_url:
        return match_url.group(1), match_url.group(2), int(match_url.group(3))

    # Match shorthand: owner/repo#123
    match_short = re.search(r"^([^/]+)/([^#]+)#(\d+)$", pr_url_or_shorthand.strip())
    if match_short:
        return match_short.group(1), match_short.group(2), int(match_short.group(3))

    raise ValueError(f"Invalid GitHub PR reference: {pr_url_or_shorthand}. Expected 'owner/repo#123' or 'https://github.com/owner/repo/pull/123'")


def fetch_pr_diff(owner: str, repo: str, pr_number: int, token: Optional[str] = None) -> GitHubPRInfo:
    """Fetches diff and PR metadata from GitHub."""
    diff_url = f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{pr_number}.diff"
    headers = {"User-Agent": "Apex-Council-Bot"}
    if token or os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"token {token or os.getenv('GITHUB_TOKEN')}"

    try:
        from ..security.safe_net import safe_http_request
        req = safe_http_request(diff_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        diff_text = f"# Failed to download live diff from {diff_url}: {e}\n# Simulation diff used for testing."

    return GitHubPRInfo(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        title=f"PR #{pr_number} in {owner}/{repo}",
        diff_text=diff_text,
    )


def review_github_pr(
    pr_target: str,
    token: Optional[str] = None,
    force_offline: bool = False,
) -> Dict[str, Any]:
    """Fetches a GitHub Pull Request, convenes the Council, and formats a PR Review."""
    owner, repo, pr_num = parse_github_pr_url(pr_target)
    pr_info = fetch_pr_diff(owner, repo, pr_num, token=token)

    prompt = (
        f"Perform an exhaustive Pull Request Code Review on GitHub PR #{pr_num} ({owner}/{repo}).\n"
        f"Examine diff for security regressions, logical errors, memory leaks, and breaking API changes.\n\n"
        f"PR Diff:\n```diff\n{pr_info.diff_text[:6000]}\n```"
    )

    engine = CouncilEngine(force_offline=force_offline)
    council_result = engine.convene_council(prompt)

    winner_score = council_result.evaluations[council_result.winner].overall_score
    status = "APPROVED" if winner_score >= 85.0 else "REQUEST_CHANGES"

    markdown_comment = (
        f"## 🏛️ Apex-Council Pull Request Review: `{status}`\n\n"
        f"> **PR:** `{owner}/{repo}#{pr_num}` | **Deliberation Winner:** 🏆 **{council_result.winner.value}** ({winner_score}/100)\n\n"
        f"### 📊 Supreme Council Evaluation\n"
        f"| Model Provider | Security Rating | Peer Review | Score |\n"
        f"| :--- | :--- | :--- | :--- |\n"
    )

    for p, ev in council_result.evaluations.items():
        markdown_comment += f"| **{p.value}** | `{ev.security_score:.0f}%` | `{ev.peer_review_avg:.1f}/10` | **`{ev.overall_score:.1f}`** |\n"

    markdown_comment += (
        f"\n### 🔍 Council Verdict & Remediation\n"
        f"{council_result.verdict_summary}\n\n"
        f"#### ✨ Recommended Synthesized Patch\n"
        f"```python\n{council_result.consensus_code}\n```\n"
    )

    return {
        "owner": owner,
        "repo": repo,
        "pr_number": pr_num,
        "status": status,
        "council_result": council_result,
        "markdown_comment": markdown_comment,
    }
