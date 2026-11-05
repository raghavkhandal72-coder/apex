"""apex_council.reviewdog — Automated code review and multi-format diagnostic bridge.

Pure Python 3 standard library implementation (zero external dependencies).
"""

from __future__ import annotations

from typing import List, Optional

from .filter import DiffFileInfo, filter_diagnostics, parse_unified_diff, paths_match
from .models import (
    CodeRule,
    Diagnostic,
    Location,
    Position,
    Range,
    ReviewResult,
    Severity,
    Suggestion,
)
from .parser import (
    parse_checkstyle,
    parse_diagnostics,
    parse_line_format,
    parse_rdjson,
    parse_rdjsonl,
)
from .reporter import (
    format_checkstyle,
    format_github_annotations,
    format_markdown,
    format_rdjson,
    format_report,
    format_terminal,
    report_diagnostics,
)


def review(
    diagnostics_source: str,
    diff_text: Optional[str] = None,
    format: str = "auto",
    filter_mode: str = "added",
    reporter: str = "text",
    pattern: Optional[str] = None,
    no_color: bool = False,
) -> ReviewResult:
    """Execute end-to-end reviewdog review pipeline.

    1. Parse raw diagnostics in any supported format (rdjson, rdjsonl, checkstyle, line)
    2. Filter against git unified diff (if diff_text provided and filter_mode != 'nofilter')
    3. Render formatted report in chosen output format (text table, markdown, CI annotations, rdjson, checkstyle)
    4. Return structured ReviewResult

    Args:
        diagnostics_source: Raw string containing diagnostics.
        diff_text: Optional unified git diff string.
        format: Input format ('auto', 'rdjson', 'rdjsonl', 'checkstyle', 'line').
        filter_mode: Diff filter mode ('added', 'diff-context', 'file', 'nofilter').
        reporter: Output report format ('text', 'markdown', 'github-annotations', 'rdjson', 'checkstyle').
        pattern: Optional regex pattern for line format parsing.
        no_color: Disable ANSI colors in text output.

    Returns:
        ReviewResult containing total findings, filtered findings, diagnostics, and formatted output.
    """
    # 1. Parse diagnostics
    parsed_diagnostics = parse_diagnostics(diagnostics_source, format_type=format, pattern=pattern)
    total_count = len(parsed_diagnostics)

    # 2. Filter diagnostics if diff provided
    if diff_text is not None and filter_mode != "nofilter":
        active_diagnostics = filter_diagnostics(parsed_diagnostics, diff_text, mode=filter_mode)
    else:
        active_diagnostics = parsed_diagnostics

    reported_count = len(active_diagnostics)

    # 3. Format output
    rendered_output = report_diagnostics(active_diagnostics, output_format=reporter, no_color=no_color)

    return ReviewResult(
        total_findings=total_count,
        reported_findings=reported_count,
        filter_mode=filter_mode,
        diagnostics=active_diagnostics,
        raw_output=rendered_output,
    )


__all__ = [
    # Models
    "Severity",
    "Position",
    "Range",
    "Location",
    "CodeRule",
    "Suggestion",
    "Diagnostic",
    "ReviewResult",
    # Parsers
    "parse_diagnostics",
    "parse_rdjson",
    "parse_rdjsonl",
    "parse_checkstyle",
    "parse_line_format",
    # Filters
    "filter_diagnostics",
    "parse_unified_diff",
    "DiffFileInfo",
    "paths_match",
    # Reporters
    "report_diagnostics",
    "format_report",
    "format_terminal",
    "format_markdown",
    "format_github_annotations",
    "format_rdjson",
    "format_checkstyle",
    # Pipeline
    "review",
]

__version__ = "1.0.0"
