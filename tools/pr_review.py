#!/usr/bin/env python3
"""Zero-dependency, diff-aware PR Review tool for GitHub Actions.

Parses findings in rdjson (Reviewdog Diagnostic Format) and comments only on lines
added by the pull request diff.

Features:
- Pure Python 3 standard library (zero external pip dependencies)
- Unified diff parsing with exact added-line tracking (`parse_added_lines`)
- RDJSON diagnostic format parsing (`parse_rdjson`)
- Diff-aware findings filtering with path normalization (`filter_findings`)
- Review payload generation with deduplication & capping (`to_review`)
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
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from apex_council.security.safe_net import safe_http_request
except ImportError:
    safe_http_request = None


# ==============================================================================
# Unified Diff Parsing & Added-Line Extraction
# ==============================================================================

HUNK_HEADER_PATTERN = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)


def normalize_path(path: str, root: str = "") -> str:
    """Normalize file path to POSIX style, stripping root prefix if provided."""
    p = str(path).replace("\\", "/").strip()
    if root:
        r = str(root).replace("\\", "/").strip().rstrip("/")
        if p == r:
            return ""
        if p.startswith(r + "/"):
            p = p[len(r) + 1 :]
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("a/") or p.startswith("b/"):
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


def parse_added_lines(diff_text: str) -> Dict[str, Set[int]]:
    """Parse unified git diff and extract mapping of normalized new_path -> added line numbers."""
    files: Dict[str, Set[int]] = {}
    if not diff_text or not diff_text.strip():
        return files

    lines = diff_text.splitlines()
    current_old_path = ""
    current_new_path = ""
    current_new_line = 0
    in_hunk = False
    is_deleted_file = False

    for line in lines:
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                a_part = parts[2]
                b_part = parts[3]
                current_old_path = a_part[2:] if a_part.startswith("a/") else a_part
                current_new_path = b_part[2:] if b_part.startswith("b/") else b_part
            in_hunk = False
            is_deleted_file = False

        elif line.startswith("--- "):
            current_old_path = line[4:].strip().split("\t")[0].strip()
            in_hunk = False

        elif line.startswith("+++ "):
            new_p = line[4:].strip().split("\t")[0].strip()
            current_new_path = new_p
            if current_new_path == "/dev/null":
                is_deleted_file = True
            else:
                is_deleted_file = False
                norm_new = normalize_path(current_new_path)
                if norm_new not in files:
                    files[norm_new] = set()
            in_hunk = False

        elif line.startswith("@@"):
            m = HUNK_HEADER_PATTERN.match(line)
            if m:
                current_new_line = int(m.group("new_start"))
                in_hunk = True
                if not is_deleted_file and current_new_path and current_new_path != "/dev/null":
                    norm_new = normalize_path(current_new_path)
                    if norm_new not in files:
                        files[norm_new] = set()

        elif in_hunk and not is_deleted_file:
            norm_new = normalize_path(current_new_path) if current_new_path else ""
            if line.startswith("+"):
                # Line added to new version of file
                if norm_new:
                    if norm_new not in files:
                        files[norm_new] = set()
                    files[norm_new].add(current_new_line)
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

    # Filter out empty deleted file references
    return {k: v for k, v in files.items() if v}


# ==============================================================================
# RDJSON Diagnostic Parser
# ==============================================================================

def parse_rdjson(raw_content: Union[str, Dict[str, Any], List[Any]]) -> List[Dict[str, Any]]:
    """Parse findings from rdjson content into a list of diagnostic dictionaries."""
    if isinstance(raw_content, str):
        content = raw_content.strip()
        if not content:
            return []
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Invalid JSON format for rdjson: {e}") from e
    else:
        data = raw_content

    if isinstance(data, dict):
        if "diagnostics" in data and isinstance(data["diagnostics"], list):
            return data["diagnostics"]
        if "message" in data and "location" in data:
            return [data]
        return []
    elif isinstance(data, list):
        return data

    return []


def parse_rdjson_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read and parse findings from an rdjson file path."""
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
        return parse_rdjson(content)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to parse {file_path} as rdjson: {e}\n")
        return []


# ==============================================================================
# Diff Filtering & Deduplication
# ==============================================================================

def _extract_diag_info(diag: Dict[str, Any], root: str = "") -> Tuple[str, int, str, str, Optional[str]]:
    """Helper to extract normalized (path, line, message, severity, code) from a diagnostic dict."""
    loc = diag.get("location", {})
    raw_path = loc.get("path") if isinstance(loc, dict) else None
    if not raw_path:
        raw_path = diag.get("path", "")
    norm_p = normalize_path(str(raw_path), root=root)

    line = None
    if isinstance(loc, dict) and "range" in loc and isinstance(loc["range"], dict):
        start = loc["range"].get("start", {})
        if isinstance(start, dict):
            line = start.get("line")
    if line is None:
        line = diag.get("line", 1)
    line = int(line)

    message = str(diag.get("message", "")).strip()
    severity = str(diag.get("severity", "WARNING")).upper()
    code = None
    code_obj = diag.get("code")
    if isinstance(code_obj, dict):
        code = code_obj.get("value")
    elif code_obj:
        code = str(code_obj)

    return norm_p, line, message, severity, code


def filter_findings(
    diags: List[Dict[str, Any]],
    added_lines: Dict[str, Set[int]],
    root: str = "",
) -> List[Dict[str, Any]]:
    """Filter diagnostics to only those on lines added by the diff, with deduplication.

    Returns a list of dicts with standardized keys ('path', 'line', 'message', 'severity', etc.).
    """
    kept: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, int, str, str, Optional[str]]] = set()

    for d in diags:
        norm_p, line, message, severity, code = _extract_diag_info(d, root=root)

        # Match against added_lines map
        matched_path: Optional[str] = None
        matched_set: Optional[Set[int]] = None

        if norm_p in added_lines:
            matched_path = norm_p
            matched_set = added_lines[norm_p]
        else:
            for diff_p, lines in added_lines.items():
                if paths_match(norm_p, diff_p):
                    matched_path = diff_p
                    matched_set = lines
                    break

        if matched_path and matched_set and line in matched_set:
            dedup_key = (matched_path, line, message, severity, code)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Build enriched finding dict
            item = dict(d)
            item["path"] = matched_path
            item["line"] = line
            item["message"] = message
            item["severity"] = severity
            if code is not None:
                item["code"] = code
            kept.append(item)

    return kept


# ==============================================================================
# Review Payload Generation
# ==============================================================================

def _severity_rank(sev: str) -> int:
    s = str(sev).upper()
    if s in ("ERROR", "ERR", "CRITICAL", "FATAL"):
        return 0
    if s in ("WARNING", "WARN"):
        return 1
    return 2


def to_review(findings: List[Dict[str, Any]], max_comments: int = 30) -> Dict[str, Any]:
    """Convert filtered findings into a GitHub PR Review payload with comments capped at max_comments."""
    # Priority sorting: ERROR first, then WARNING, then INFO, then path & line
    sorted_findings = sorted(
        findings,
        key=lambda x: (_severity_rank(x.get("severity", "WARNING")), x.get("path", ""), x.get("line", 0)),
    )

    comments_to_post = sorted_findings[:max_comments]
    hidden_count = max(0, len(sorted_findings) - max_comments)

    inline_comments: List[Dict[str, Any]] = []
    for f in comments_to_post:
        sev = f.get("severity", "WARNING").upper()
        code = f.get("code")
        if isinstance(code, dict):
            code = code.get("value")

        header = f"**[{sev}]**"
        if code:
            header += f" `{code}`"

        body = f"{header}\n\n{f.get('message', '')}"
        suggestions = f.get("suggestions", [])
        if suggestions and isinstance(suggestions, list) and isinstance(suggestions[0], dict):
            stext = suggestions[0].get("text")
            if stext:
                body += f"\n\n```suggestion\n{stext}\n```"

        inline_comments.append({
            "path": f["path"],
            "line": f["line"],
            "side": "RIGHT",
            "body": body,
        })

    # Build review body summary
    total = len(findings)
    errors = sum(1 for f in findings if _severity_rank(f.get("severity", "")) == 0)
    warnings = sum(1 for f in findings if _severity_rank(f.get("severity", "")) == 1)
    infos = total - errors - warnings

    summary_lines = [
        "## Apex PR Review Report",
        "",
        "> **Diff-Aware Review:** Comments are posted strictly on lines added/modified in this PR.",
        "",
        f"- **Findings on Added Lines:** **{total}** ({errors} errors, {warnings} warnings, {infos} info)",
    ]

    if hidden_count > 0:
        summary_lines.append(f"- **Note:** {hidden_count} more not shown (capped at {max_comments} max comments).")

    summary_lines.append("")
    if total == 0:
        summary_lines.append("✓ **All added lines passed inspection! No issues found.**")
    elif errors > 0:
        summary_lines.append(f"**Attention:** Found **{errors} ERROR** severity finding(s) on added lines.")
    else:
        summary_lines.append("Review findings are available inline on changed lines.")

    return {
        "body": "\n".join(summary_lines),
        "event": "COMMENT",
        "comments": inline_comments,
    }


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
        ref = os.environ.get("GITHUB_REF", "")
        m = re.match(r"^refs/pull/(\d+)/", ref)
        if m:
            pr_number = int(m.group(1))

    return repo, pr_number, commit_sha


def post_github_pr_review(
    repo: str,
    pr_number: int,
    token: str,
    review_payload: Dict[str, Any],
    commit_sha: Optional[str] = None,
    api_url: str = "https://api.github.com",
) -> bool:
    """Post PR review with inline comments to GitHub REST API.

    Falls back to posting an issue comment if review fails (e.g. 422 line mismatch).
    """
    review_endpoint = f"{api_url}/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Apex-PR-Review/0.9.0",
        "Content-Type": "application/json",
    }

    payload = dict(review_payload)
    if commit_sha:
        payload["commit_id"] = commit_sha

    req_data = json.dumps(payload).encode("utf-8")
    if safe_http_request:
        req = safe_http_request(review_endpoint, data=req_data, headers=headers, method="POST")
    else:
        _dest_uri = str(review_endpoint)
        req = urllib.request.Request(_dest_uri, data=req_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            if 200 <= status < 300:
                print(f"[Apex PR Review] Successfully posted PR review with {len(payload.get('comments', []))} inline comment(s).")
                return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"Warning: GitHub review creation failed (HTTP {e.code}): {err_msg}\n")
        # Fallback: post summary as an issue comment if inline placement failed (e.g. HTTP 422)
        print("[Apex PR Review] Falling back to general PR issue comment...")
        fallback_endpoint = f"{api_url}/repos/{repo}/issues/{pr_number}/comments"
        fb_payload = json.dumps({"body": payload.get("body", "")}).encode("utf-8")
        if safe_http_request:
            fb_req = safe_http_request(fallback_endpoint, data=fb_payload, headers=headers, method="POST")
        else:
            _fb_uri = str(fallback_endpoint)
            fb_req = urllib.request.Request(_fb_uri, data=fb_payload, headers=headers, method="POST")
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
# CLI Entrypoint
# ==============================================================================

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
    parser.add_argument("--root", default="", help="Root repository directory to strip from absolute paths")
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
    added_lines = parse_added_lines(diff_text)
    total_added_lines = sum(len(lines) for lines in added_lines.values())
    print(f"[Apex PR Review] Parsed diff: {len(added_lines)} file(s), {total_added_lines} added line(s).")

    # 2. Read and parse findings
    findings = parse_rdjson_file(args.findings)
    print(f"[Apex PR Review] Parsed findings: {len(findings)} total finding(s) from {args.findings.name}.")

    # 3. Filter to added lines only (with deduplication)
    kept = filter_findings(findings, added_lines, root=args.root)
    skipped_count = len(findings) - len(kept)
    print(f"[Apex PR Review] Filtered to added lines: {len(kept)} relevant, {skipped_count} outside diff.")

    # 4. Generate review payload
    review = to_review(kept, max_comments=args.max_comments)

    # 5. Check for ERROR severity on added lines
    has_errors_on_added_lines = any(
        str(f.get("severity", "")).upper() in ("ERROR", "ERR", "CRITICAL", "FATAL")
        for f in kept
    )

    # 6. Dry-Run or Posting
    if args.dry_run:
        print("\n" + "=" * 70)
        print("              APEX PR REVIEW: DRY RUN PREVIEW             ")
        print("=" * 70)
        print(review["body"])
        print("-" * 70)
        print(f"Inline Comments to Post: {len(review['comments'])}")
        for idx, c in enumerate(review["comments"], 1):
            print(f"\n[{idx}] {c['path']}:{c['line']}")
            print(c["body"])
        print("=" * 70 + "\n")
    else:
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
                review_payload=review,
                commit_sha=commit_sha,
                api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            )

    # 7. Handle --fail-on-error
    if args.fail_on_error and has_errors_on_added_lines:
        error_count = sum(
            1 for f in kept if str(f.get("severity", "")).upper() in ("ERROR", "ERR", "CRITICAL", "FATAL")
        )
        sys.stderr.write(f"\n[Apex PR Review] FAILED: {error_count} ERROR severity finding(s) detected on added lines.\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
