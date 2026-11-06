#!/usr/bin/env python3
"""Zero-dependency, diff-aware PR Review tool for GitHub Actions.

Parses findings in rdjson (Reviewdog Diagnostic Format) and comments only on lines
added by the pull request diff.

Features:
- Pure Python 3 standard library (zero external pip dependencies)
- Unified diff parsing with exact added-line tracking
- RDJSON diagnostic format parsing
- Priority sorting (ERROR > WARNING > INFO) and comment truncation (--max-comments)
- Strict error gating (--fail-on-error)
- Dry-run simulation mode (--dry-run)
- Resilient GitHub API review posting with automatic issue-comment fallback
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# Unified Diff Parsing & Added-Line Extraction
# ==============================================================================

HUNK_HEADER_PATTERN = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)


@dataclass
class DiffFile:
    """Represents a file in a git unified diff and its added line numbers."""
    old_path: str
    new_path: str
    added_lines: Set[int] = field(default_factory=set)


def normalize_path(path: str) -> str:
    """Normalize file path to POSIX style without leading prefixes."""
    p = str(path).replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("a/"):
        p = p[2:]
    elif p.startswith("b/"):
        p = p[2:]
    return p


def paths_match(diag_path: str, diff_path: str) -> bool:
    """Check if diagnostic path matches a file in the diff."""
    if not diag_path or not diff_path:
        return False
    p1 = normalize_path(diag_path)
    p2 = normalize_path(diff_path)
    if p1 == p2:
        return True
    if p1.endswith("/" + p2) or p2.endswith("/" + p1):
        return True
    name1 = p1.split("/")[-1]
    name2 = p2.split("/")[-1]
    if name1 and name2 and name1 == name2:
        return True
    # Case-insensitive comparison for cross-platform robustness
    if p1.lower() == p2.lower() or name1.lower() == name2.lower():
        return True
    return False


def parse_diff_added_lines(diff_text: str) -> Dict[str, DiffFile]:
    """Parse unified git diff and extract sets of added line numbers per file."""
    files: Dict[str, DiffFile] = {}
    if not diff_text or not diff_text.strip():
        return files

    lines = diff_text.splitlines()
    current_old_path = ""
    current_new_path = ""
    current_file: Optional[DiffFile] = None
    current_new_line = 0
    in_hunk = False

    for line in lines:
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                a_part = parts[2]
                b_part = parts[3]
                current_old_path = a_part[2:] if a_part.startswith("a/") else a_part
                current_new_path = b_part[2:] if b_part.startswith("b/") else b_part
            in_hunk = False

        elif line.startswith("--- "):
            current_old_path = line[4:].strip().split("\t")[0].strip()
            in_hunk = False

        elif line.startswith("+++ "):
            current_new_path = line[4:].strip().split("\t")[0].strip()
            norm_new = normalize_path(current_new_path)
            norm_old = normalize_path(current_old_path)
            current_file = DiffFile(old_path=norm_old, new_path=norm_new)
            files[norm_new] = current_file
            if norm_old and norm_old != "/dev/null":
                files[norm_old] = current_file
            in_hunk = False

        elif line.startswith("@@"):
            m = HUNK_HEADER_PATTERN.match(line)
            if m:
                current_new_line = int(m.group("new_start"))
                in_hunk = True
                if current_file is None:
                    norm_new = normalize_path(current_new_path) if current_new_path else "*"
                    norm_old = normalize_path(current_old_path) if current_old_path else "*"
                    current_file = DiffFile(old_path=norm_old, new_path=norm_new)
                    files[norm_new] = current_file

        elif in_hunk and current_file is not None:
            if line.startswith("+"):
                # Line added to new version of file
                current_file.added_lines.add(current_new_line)
                current_new_line += 1
            elif line.startswith("-"):
                # Line deleted from old file (does not increment new file line)
                pass
            elif line.startswith(" ") or line == "":
                # Context line (exists in new file, but not modified)
                current_new_line += 1
            elif line.startswith("\\"):
                pass
            else:
                in_hunk = False

    return files


# ==============================================================================
# RDJSON Diagnostic Parser
# ==============================================================================

@dataclass
class DiagnosticFinding:
    """Represents a linter/analyzer diagnostic finding."""
    message: str
    path: str
    line: int
    column: Optional[int] = None
    severity: str = "WARNING"  # ERROR, WARNING, INFO
    rule_code: Optional[str] = None
    source_name: Optional[str] = None
    suggestion: Optional[str] = None

    @property
    def severity_rank(self) -> int:
        s = self.severity.upper()
        if s in ("ERROR", "ERR", "CRITICAL", "FATAL"):
            return 0
        if s in ("WARNING", "WARN"):
            return 1
        return 2

    def to_markdown(self) -> str:
        sev = self.severity.upper()
        icon = "[ERROR]" if sev == "ERROR" else "[WARNING]" if sev == "WARNING" else "[INFO]"
        header = f"**{icon}**"
        if self.rule_code:
            header += f" `{self.rule_code}`"
        if self.source_name:
            header += f" *({self.source_name})*"

        body = f"{header}\n\n{self.message}"
        if self.suggestion:
            body += f"\n\n```suggestion\n{self.suggestion}\n```"
        return body


def parse_rdjson_file(file_path: Path) -> List[DiagnosticFinding]:
    """Parse findings from an rdjson file into DiagnosticFinding instances."""
    if not file_path.exists():
        return []

    try:
        raw_text = file_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return []
        data = json.loads(raw_text)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to parse {file_path} as JSON: {e}\n")
        return []

    findings: List[DiagnosticFinding] = []

    default_source = None
    if isinstance(data, dict):
        if "source" in data and isinstance(data["source"], dict):
            default_source = data["source"].get("name")
        raw_items = data.get("diagnostics", [])
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue
        msg = str(item.get("message", "")).strip()
        loc = item.get("location", {})
        path_val = loc.get("path", "")
        range_val = loc.get("range", {})
        start_val = range_val.get("start", {})
        line_num = int(start_val.get("line", 1))
        col_num = start_val.get("column")

        sev_val = str(item.get("severity", "WARNING")).upper()
        if sev_val not in ("ERROR", "WARNING", "INFO"):
            sev_val = "WARNING"

        code_val = None
        code_obj = item.get("code")
        if isinstance(code_obj, dict):
            code_val = code_obj.get("value")
        elif code_obj:
            code_val = str(code_obj)

        source_val = default_source
        if "source" in item and isinstance(item["source"], dict):
            source_val = item["source"].get("name")
        elif "source_name" in item:
            source_val = item.get("source_name")

        suggestion_val = None
        suggestions = item.get("suggestions", [])
        if suggestions and isinstance(suggestions, list) and isinstance(suggestions[0], dict):
            suggestion_val = suggestions[0].get("text")

        findings.append(
            DiagnosticFinding(
                message=msg,
                path=path_val,
                line=line_num,
                column=col_num,
                severity=sev_val,
                rule_code=code_val,
                source_name=source_val,
                suggestion=suggestion_val,
            )
        )

    return findings


# ==============================================================================
# Diff Filtering: Comments only on lines added by the PR
# ==============================================================================

def filter_findings_to_added_lines(
    findings: List[DiagnosticFinding],
    diff_files: Dict[str, DiffFile],
) -> Tuple[List[DiagnosticFinding], List[DiagnosticFinding]]:
    """Filter diagnostics to only those falling on added/modified lines in the diff.

    Returns:
        (added_findings, skipped_findings)
    """
    added_findings: List[DiagnosticFinding] = []
    skipped_findings: List[DiagnosticFinding] = []

    for f in findings:
        matched_file: Optional[DiffFile] = None
        for diff_path, file_info in diff_files.items():
            if paths_match(f.path, diff_path) or paths_match(f.path, file_info.new_path):
                matched_file = file_info
                break

        if matched_file and f.line in matched_file.added_lines:
            # Finding is directly on an added line in this PR!
            # Use the normalized new path from the diff
            f.path = matched_file.new_path
            added_findings.append(f)
        else:
            skipped_findings.append(f)

    # Sort added findings: ERRORs first, then WARNINGs, then INFO, then path & line
    added_findings.sort(key=lambda x: (x.severity_rank, x.path, x.line))
    return added_findings, skipped_findings


# ==============================================================================
# GitHub API Interaction
# ==============================================================================

def get_github_context() -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Extract owner/repo, pull_request_number, and commit_sha from GitHub Actions environment."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number: Optional[int] = None
    commit_sha: Optional[str] = os.environ.get("GITHUB_SHA")

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and Path(event_path).exists():
        try:
            event_data = json.loads(Path(event_path).read_text(encoding="utf-8"))
            if "pull_request" in event_data:
                pr_info = event_data["pull_request"]
                pr_number = pr_info.get("number")
                if "head" in pr_info and "sha" in pr_info["head"]:
                    commit_sha = pr_info["head"]["sha"]
            elif "number" in event_data:
                pr_number = event_data.get("number")
        except Exception as e:
            sys.stderr.write(f"Warning: Could not read GITHUB_EVENT_PATH: {e}\n")

    if not pr_number:
        # Fallback: check GITHUB_REF (e.g. refs/pull/123/merge)
        ref = os.environ.get("GITHUB_REF", "")
        m = re.match(r"^refs/pull/(\d+)/", ref)
        if m:
            pr_number = int(m.group(1))

    return repo, pr_number, commit_sha


def post_github_pr_review(
    repo: str,
    pr_number: int,
    token: str,
    summary_body: str,
    comments: List[Dict[str, Any]],
    commit_sha: Optional[str] = None,
    api_url: str = "https://api.github.com",
) -> bool:
    """Post PR review with inline comments to GitHub REST API.

    Falls back to posting an issue comment if review fails (e.g., 422 line mismatch).
    """
    review_endpoint = f"{api_url}/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Apex-PR-Review/0.9.0",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "body": summary_body,
        "event": "COMMENT",
        "comments": comments,
    }
    if commit_sha:
        payload["commit_id"] = commit_sha

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(review_endpoint, data=req_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            if 200 <= status < 300:
                print(f"[Apex PR Review] Successfully posted PR review with {len(comments)} inline comment(s).")
                return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"Warning: GitHub review creation failed (HTTP {e.code}): {err_msg}\n")
        # Fallback: post summary as an issue comment if inline placement failed (e.g. HTTP 422)
        print("[Apex PR Review] Falling back to general PR issue comment...")
        fallback_endpoint = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
        fb_payload = json.dumps({"body": summary_body}).encode("utf-8")
        fb_req = urllib.request.Request(fallback_endpoint, data=fb_payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(fb_req) as fb_resp:
                if 200 <= fb_resp.status < 300:
                    print("[Apex PR Review] Successfully posted fallback PR comment.")
                    return True
        except Exception as fb_err:
            sys.stderr.write(f"Error: Fallback comment also failed: {fb_err}\n")

    except Exception as e:
        sys.stderr.write(f"Error: Network exception posting review: {e}\n")

    return False


# ==============================================================================
# Main Review Orchestrator
# ==============================================================================

def build_review_summary(
    total_findings: int,
    added_findings: List[DiagnosticFinding],
    skipped_count: int,
    max_comments: int,
) -> str:
    """Build markdown summary for the PR review."""
    errors = sum(1 for f in added_findings if f.severity.upper() == "ERROR")
    warnings = sum(1 for f in added_findings if f.severity.upper() == "WARNING")
    infos = sum(1 for f in added_findings if f.severity.upper() == "INFO")

    lines = [
        "## Apex PR Review Report",
        "",
        "> **Diff-Aware Review:** Comments are posted strictly on lines added/modified in this PR.",
        "",
        f"- **Findings on Added Lines:** **{len(added_findings)}** ({errors} errors, {warnings} warnings, {infos} info)",
        f"- **Findings Outside PR Diff:** {skipped_count} (ignored to prevent noise)",
        f"- **Total Diagnostic Findings:** {total_findings}",
    ]

    if len(added_findings) > max_comments:
        lines.append(f"- **Note:** Displaying top {max_comments} comments (prioritized by severity).")

    lines.append("")
    if not added_findings:
        lines.append("✓ **All added lines passed inspection! No issues found.**")
    elif errors > 0:
        lines.append(f"**Attention:** Found **{errors} ERROR** severity finding(s) on added lines.")
    else:
        lines.append("Review findings are available inline on changed lines.")

    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="pr_review",
        description="Diff-aware PR review: comment only on lines added by the PR.",
    )
    parser.add_argument("--diff", required=True, type=Path, help="Path to unified git diff file")
    parser.add_argument("--findings", required=True, type=Path, help="Path to findings file in rdjson format")
    parser.add_argument("--max-comments", type=int, default=30, help="Maximum inline comments per review")
    parser.add_argument("--fail-on-error", action="store_true", help="Fail job if ERROR finding is on an added line")
    parser.add_argument("--dry-run", action="store_true", help="Print review instead of posting to GitHub")
    parser.add_argument("--token", default=None, help="GitHub Token (defaults to GITHUB_TOKEN env var)")
    parser.add_argument("--repo", default=None, help="Target repo owner/name (defaults to GITHUB_REPOSITORY)")
    parser.add_argument("--pr", type=int, default=None, help="PR number (defaults to GitHub Actions event context)")
    parser.add_argument("--commit-id", default=None, help="Head commit SHA")

    args = parser.parse_args(argv)

    # 1. Read and parse unified diff
    if not args.diff.exists():
        sys.stderr.write(f"Error: Diff file not found: {args.diff}\n")
        return 2

    diff_text = args.diff.read_text(encoding="utf-8", errors="replace")
    diff_files = parse_diff_added_lines(diff_text)
    total_added_lines = sum(len(df.added_lines) for df in diff_files.values())
    print(f"[Apex PR Review] Parsed diff: {len(diff_files)} file(s), {total_added_lines} added line(s).")

    # 2. Read and parse findings
    findings = parse_rdjson_file(args.findings)
    print(f"[Apex PR Review] Parsed findings: {len(findings)} total finding(s) from {args.findings.name}.")

    # 3. Filter to added lines only
    added_findings, skipped_findings = filter_findings_to_added_lines(findings, diff_files)
    print(f"[Apex PR Review] Filtered to added lines: {len(added_findings)} relevant, {len(skipped_findings)} outside diff.")

    # 4. Truncate comments according to max-comments
    comments_to_post = added_findings[: args.max_comments]

    # 5. Build review summary and inline comment payloads
    summary_markdown = build_review_summary(
        total_findings=len(findings),
        added_findings=added_findings,
        skipped_count=len(skipped_findings),
        max_comments=args.max_comments,
    )

    inline_comments: List[Dict[str, Any]] = []
    for f in comments_to_post:
        inline_comments.append({
            "path": f.path,
            "line": f.line,
            "side": "RIGHT",
            "body": f.to_markdown(),
        })

    # 6. Check for ERROR severity on added lines
    has_errors_on_added_lines = any(f.severity.upper() == "ERROR" for f in added_findings)

    # 7. Dry-Run or Posting
    if args.dry_run:
        print("\n" + "=" * 70)
        print("              APEX PR REVIEW: DRY RUN PREVIEW             ")
        print("=" * 70)
        print(summary_markdown)
        print("-" * 70)
        print(f"Inline Comments to Post: {len(inline_comments)}")
        for idx, c in enumerate(inline_comments, 1):
            print(f"\n[{idx}] {c['path']}:{c['line']}")
            print(c["body"])
        print("=" * 70 + "\n")
    else:
        # Determine GitHub context
        token = args.token or os.environ.get("GITHUB_TOKEN")
        repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
        env_repo, env_pr, env_commit = get_github_context()
        repo = repo or env_repo
        pr_number = args.pr or env_pr
        commit_sha = args.commit_id or env_commit

        if not token:
            print("[Apex PR Review] Notice: No GITHUB_TOKEN supplied. Skipping review API call.")
        elif not repo or not pr_number:
            print(f"[Apex PR Review] Notice: Not a pull_request event context (repo={repo}, pr={pr_number}). Skipping review API call.")
        else:
            post_github_pr_review(
                repo=repo,
                pr_number=pr_number,
                token=token,
                summary_body=summary_markdown,
                comments=inline_comments,
                commit_sha=commit_sha,
                api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            )

    # 8. Handle --fail-on-error
    if args.fail_on_error and has_errors_on_added_lines:
        error_count = sum(1 for f in added_findings if f.severity.upper() == "ERROR")
        sys.stderr.write(f"\n[Apex PR Review] FAILED: {error_count} ERROR severity finding(s) detected on added lines.\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
