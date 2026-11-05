"""Diagnostic reporter and formatters for apex_council.reviewdog.

Supports:
1. Terminal / Console: ANSI color formatted table
2. Markdown: GitHub PR review comment format with suggestions
3. GitHub Actions: Workflow commands (::error, ::warning, ::notice)
4. rdjson: Reviewdog JSON format
5. checkstyle: XML Checkstyle format

Pure Python 3 standard library (zero external dependencies).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from xml.dom import minidom

from .models import Diagnostic, Severity

# ANSI escape sequences for terminal output
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

SEVERITY_COLORS: Dict[Severity, str] = {
    Severity.ERROR: RED,
    Severity.WARNING: YELLOW,
    Severity.INFO: CYAN,
}

SEVERITY_EMOJIS: Dict[Severity, str] = {
    Severity.ERROR: "🔴",
    Severity.WARNING: "🟡",
    Severity.INFO: "🔵",
}


def escape_github_data(s: str) -> str:
    """Escape data for GitHub Actions workflow command message."""
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_github_property(s: str) -> str:
    """Escape property value for GitHub Actions workflow command."""
    return (
        s.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def format_terminal(diagnostics: List[Diagnostic], no_color: bool = False) -> str:
    """Render diagnostics as a terminal ANSI table."""
    if not diagnostics:
        msg = "🐶 [reviewdog] No diagnostics found. Code looks clean!"
        return f"{GREEN}{msg}{RESET}" if not no_color else msg

    c_reset = "" if no_color else RESET
    c_bold = "" if no_color else BOLD
    c_dim = "" if no_color else DIM

    lines: List[str] = []
    lines.append(f"{c_bold}🐶 [reviewdog] Diagnostic Report ({len(diagnostics)} findings){c_reset}")
    lines.append("=" * 80)
    lines.append(
        f"{'Location':<30} | {'Severity':<9} | {'Code':<10} | {'Message'}"
    )
    lines.append("-" * 80)

    error_count = 0
    warning_count = 0
    info_count = 0

    for d in diagnostics:
        loc_str = d.location.path
        start = d.location.range.start
        if start.line:
            loc_str += f":{start.line}"
            if start.column:
                loc_str += f":{start.column}"

        # Truncate location if too long
        if len(loc_str) > 29:
            loc_str = "..." + loc_str[-26:]

        sev = d.severity
        if sev == Severity.ERROR:
            error_count += 1
        elif sev == Severity.WARNING:
            warning_count += 1
        else:
            info_count += 1

        c_sev = "" if no_color else SEVERITY_COLORS.get(sev, WHITE)
        sev_display = f"{c_sev}{sev.value:<9}{c_reset}"

        code_val = d.code.value if d.code else "-"
        if len(code_val) > 9:
            code_val = code_val[:9]

        msg = d.message.replace("\n", " ")
        if len(msg) > 80:
            msg = msg[:77] + "..."

        lines.append(f"{loc_str:<30} | {sev_display} | {code_val:<10} | {msg}")

    lines.append("=" * 80)
    summary = (
        f"Summary: {error_count} error(s), {warning_count} warning(s), {info_count} info(s)"
    )
    lines.append(f"{c_bold}{summary}{c_reset}")

    return "\n".join(lines)


def format_markdown(
    diagnostics: List[Diagnostic],
    title: str = "🐶 Reviewdog Diagnostic Report",
) -> str:
    """Render diagnostics in GitHub PR review comment markdown format."""
    lines: List[str] = []
    lines.append(f"### {title}\n")

    if not diagnostics:
        lines.append("✅ **No findings detected.** All checks passed cleanly!\n")
        return "\n".join(lines)

    lines.append(f"Found **{len(diagnostics)}** diagnostic(s) across reviewed files.\n")
    lines.append("| Severity | Location | Code | Message |")
    lines.append("| :---: | :--- | :--- | :--- |")

    suggestions_list: List[Diagnostic] = []
    error_count = 0
    warning_count = 0
    info_count = 0

    for d in diagnostics:
        sev = d.severity
        if sev == Severity.ERROR:
            error_count += 1
        elif sev == Severity.WARNING:
            warning_count += 1
        else:
            info_count += 1

        emoji = SEVERITY_EMOJIS.get(sev, "⚪")
        sev_badge = f"{emoji} **{sev.value}**"

        loc_str = d.location.path
        start = d.location.range.start
        if start.line:
            loc_str += f":{start.line}"
            if start.column:
                loc_str += f":{start.column}"

        loc_md = f"`{loc_str}`"
        code_md = f"`{d.code.value}`" if d.code else "—"
        
        # Clean markdown table special characters in message
        msg_clean = d.message.replace("|", "\\|").replace("\n", "<br>")

        lines.append(f"| {sev_badge} | {loc_md} | {code_md} | {msg_clean} |")

        if d.suggestions:
            suggestions_list.append(d)

    # Render suggestions accordion if any
    if suggestions_list:
        lines.append("\n<details>")
        lines.append(f"<summary>💡 <b>Code Suggestions ({len(suggestions_list)})</b></summary>\n")
        for d in suggestions_list:
            loc_str = d.location.path
            if d.location.range.start.line:
                loc_str += f":{d.location.range.start.line}"
            lines.append(f"**`{loc_str}`** — *{d.message}*")
            for sug in d.suggestions:
                lines.append("```suggestion")
                lines.append(sug.text)
                lines.append("```")
        lines.append("</details>\n")

    lines.append(
        f"\n*Summary: {error_count} error(s), {warning_count} warning(s), {info_count} info(s)*"
    )

    return "\n".join(lines)


def format_github_annotations(diagnostics: List[Diagnostic]) -> str:
    """Render diagnostics as GitHub Actions workflow commands.

    Format: ::error file={file},line={line},col={col},title={title}::{message}
    """
    lines: List[str] = []

    for d in diagnostics:
        sev = d.severity
        if sev == Severity.ERROR:
            cmd = "error"
        elif sev == Severity.WARNING:
            cmd = "warning"
        else:
            cmd = "notice"

        props: List[str] = []
        if d.location.path:
            props.append(f"file={escape_github_property(d.location.path)}")

        start = d.location.range.start
        if start.line:
            props.append(f"line={start.line}")
        if start.column:
            props.append(f"col={start.column}")

        end = d.location.range.end
        if end and end.line and end.line != start.line:
            props.append(f"endLine={end.line}")
        if end and end.column:
            props.append(f"endColumn={end.column}")

        if d.code and d.code.value:
            props.append(f"title={escape_github_property(d.code.value)}")

        prop_str = f" {','.join(props)}" if props else ""
        escaped_msg = escape_github_data(d.message)
        lines.append(f"::{cmd}{prop_str}::{escaped_msg}")

    return "\n".join(lines)


def format_rdjson(
    diagnostics: List[Diagnostic],
    source_name: str = "apex-council",
) -> str:
    """Render diagnostics into official Reviewdog JSON (rdjson) format."""
    payload = {
        "source": {
            "name": source_name,
            "url": "https://github.com/apex-council",
        },
        "severity": "WARNING",
        "diagnostics": [d.to_dict() for d in diagnostics],
    }
    return json.dumps(payload, indent=2)


def format_checkstyle(diagnostics: List[Diagnostic]) -> str:
    """Render diagnostics into standard Checkstyle XML format."""
    root = ET.Element("checkstyle", attrib={"version": "4.3"})

    # Group by file path
    files_map: Dict[str, List[Diagnostic]] = {}
    for d in diagnostics:
        path = d.location.path or "unknown"
        if path not in files_map:
            files_map[path] = []
        files_map[path].append(d)

    for file_path, diag_list in files_map.items():
        file_elem = ET.SubElement(root, "file", attrib={"name": file_path})
        for d in diag_list:
            attrs = {
                "line": str(d.location.range.start.line or 1),
                "severity": d.severity.value.lower(),
                "message": d.message,
            }
            if d.location.range.start.column is not None:
                attrs["column"] = str(d.location.range.start.column)
            if d.code and d.code.value:
                attrs["source"] = d.code.value
            elif d.source_name:
                attrs["source"] = d.source_name

            ET.SubElement(file_elem, "error", attrib=attrs)

    # Pretty print XML
    xml_str = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def report_diagnostics(
    diagnostics: List[Diagnostic],
    output_format: str = "text",
    no_color: bool = False,
) -> str:
    """Universal diagnostic reporter dispatcher.

    output_format:
    - 'text', 'terminal', 'console': ANSI formatted table
    - 'markdown', 'github-pr', 'md': Markdown review comments
    - 'github-annotations', 'ci', 'annotations', 'github-actions': Workflow commands
    - 'rdjson', 'json': Reviewdog JSON
    - 'checkstyle', 'xml': Checkstyle XML
    """
    fmt = output_format.lower().strip()

    if fmt in ("text", "terminal", "console"):
        return format_terminal(diagnostics, no_color=no_color)
    elif fmt in ("markdown", "github-pr", "md"):
        return format_markdown(diagnostics)
    elif fmt in ("github-annotations", "ci", "annotations", "github-actions"):
        return format_github_annotations(diagnostics)
    elif fmt in ("rdjson", "json"):
        return format_rdjson(diagnostics)
    elif fmt in ("checkstyle", "xml"):
        return format_checkstyle(diagnostics)
    else:
        raise ValueError(
            f"Unknown output format '{output_format}'. Supported: text, markdown, github-annotations, rdjson, checkstyle"
        )


# Compatibility alias
format_report = report_diagnostics
