"""Multi-format diagnostic parser for apex_council.reviewdog.

Supports:
1. Reviewdog Diagnostic JSON (rdjson)
2. Reviewdog JSON Lines (rdjsonl)
3. Checkstyle XML format (via xml.etree.ElementTree)
4. Regex line format (file:line:col: message)

Pure Python 3 standard library (zero external dependencies).
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union

from .models import CodeRule, Diagnostic, Location, Position, Range, Severity, Suggestion

# Common linter output regex patterns
# 1. Standard: [drive:]path:line:col: [severity:] message
STANDARD_LINE_PATTERN = re.compile(
    r"^(?P<path>(?:[a-zA-Z]:[\\/])?[^:\r\n]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?:(?P<severity>error|warning|warn|info|note|hint):\s*)?(?P<message>.*)$",
    re.IGNORECASE,
)

# 2. MSVC/GCC paren style: [drive:]path(line,col): [severity:] message OR path(line): message
PAREN_LINE_PATTERN = re.compile(
    r"^(?P<path>(?:[a-zA-Z]:[\\/])?[^(\r\n]+)\((?P<line>\d+)(?:,\s*(?P<col>\d+))?\)\s*:\s*(?:(?P<severity>error|warning|warn|info|note|hint):\s*)?(?P<message>.*)$",
    re.IGNORECASE,
)

# Rule code extractor: e.g. [E501], (C0111), [flake8:E501]
RULE_CODE_PATTERN = re.compile(r"(?:\[|\()([A-Za-z0-9_\-.:]+)(?:\]|\))")


def parse_rdjson(raw_content: Union[str, Dict[str, Any], List[Any]]) -> List[Diagnostic]:
    print(f"\n[DEBUG parse_rdjson] type={type(raw_content)} content={repr(raw_content)[:300]}")
    if isinstance(raw_content, str):
        content = raw_content.strip()
        if not content:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for rdjson: {e}") from e
    else:
        data = raw_content

    results: List[Diagnostic] = []

    # Case 1: Standard rdjson with top-level wrapper
    if isinstance(data, dict):
        default_source = "apex-council"
        if "source" in data and isinstance(data["source"], dict):
            default_source = data["source"].get("name", "apex-council")

        raw_diagnostics = data.get("diagnostics")
        if raw_diagnostics is not None and isinstance(raw_diagnostics, list):
            for item in raw_diagnostics:
                if isinstance(item, dict):
                    diag = Diagnostic.from_dict(item)
                    if not item.get("source_name") and not item.get("source"):
                        diag.source_name = default_source
                    results.append(diag)
            return results
        
        # Single diagnostic in dict
        if "message" in data and "location" in data:
            results.append(Diagnostic.from_dict(data))
            return results

        return []

    # Case 2: List of diagnostics directly
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                results.append(Diagnostic.from_dict(item))
        return results

    return []


def parse_rdjsonl(raw_content: str) -> List[Diagnostic]:
    """Parse Reviewdog JSON Lines (rdjsonl).

    Each non-empty line is parsed as a JSON object representing a diagnostic
    or a collection of diagnostics.
    """
    results: List[Diagnostic] = []
    lines = raw_content.splitlines()

    for idx, line in enumerate(lines, start=1):
        line_str = line.strip()
        if not line_str:
            continue
        try:
            item = json.loads(line_str)
            if isinstance(item, dict):
                # If a line contains a wrapper object with 'diagnostics'
                if "diagnostics" in item and isinstance(item["diagnostics"], list):
                    for d in item["diagnostics"]:
                        if isinstance(d, dict):
                            results.append(Diagnostic.from_dict(d))
                else:
                    results.append(Diagnostic.from_dict(item))
            elif isinstance(item, list):
                for d in item:
                    if isinstance(d, dict):
                        results.append(Diagnostic.from_dict(d))
        except json.JSONDecodeError:
            # If line is invalid JSON, skip or continue
            continue

    return results


def parse_checkstyle(raw_content: str) -> List[Diagnostic]:
    """Parse Checkstyle XML diagnostic format.

    Structure:
    <checkstyle version="4.3">
      <file name="path/to/file.py">
        <error line="10" column="5" severity="error" message="..." source="..."/>
      </file>
    </checkstyle>
    """
    content = raw_content.strip()
    if not content:
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML format for checkstyle: {e}") from e

    results: List[Diagnostic] = []

    # Find all <file> tags (either directly under root or anywhere)
    for file_elem in root.iter("file"):
        file_path = file_elem.attrib.get("name", "").strip()
        for error_elem in file_elem.iter("error"):
            attrs = error_elem.attrib
            raw_line = attrs.get("line", "1")
            try:
                line = int(raw_line) if raw_line else 1
            except ValueError:
                line = 1

            raw_col = attrs.get("column")
            col: Optional[int] = None
            if raw_col:
                try:
                    col = int(raw_col)
                except ValueError:
                    col = None

            sev_str = attrs.get("severity", "warning")
            msg = attrs.get("message", "").strip()
            source = attrs.get("source")

            code_rule = CodeRule(value=source) if source else None
            
            # If code_rule is not set, attempt to extract bracketed rule from message
            if not code_rule and msg:
                m = RULE_CODE_PATTERN.search(msg)
                if m:
                    code_rule = CodeRule(value=m.group(1))

            diag = Diagnostic(
                message=msg,
                location=Location(
                    path=file_path,
                    range=Range(start=Position(line=line, column=col)),
                ),
                severity=Severity.from_str(sev_str),
                code=code_rule,
                source_name=source or "checkstyle",
            )
            results.append(diag)

    return results


def parse_line_format(
    raw_content: str,
    pattern: Optional[Union[str, re.Pattern]] = None,
) -> List[Diagnostic]:
    """Parse raw line diagnostics (e.g. file:line:col: message).

    If pattern is supplied, it should have named capturing groups:
    'path', 'line', optional 'col'/'column', optional 'severity', 'message', optional 'code'.
    """
    results: List[Diagnostic] = []
    lines = raw_content.splitlines()

    compiled_pattern: Optional[re.Pattern] = None
    if pattern:
        if isinstance(pattern, str):
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
        else:
            compiled_pattern = pattern

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        match = None
        if compiled_pattern:
            match = compiled_pattern.match(line_str)
            if not match:
                continue
        else:
            # Try standard pattern first, then paren pattern
            match = STANDARD_LINE_PATTERN.match(line_str)
            if not match:
                match = PAREN_LINE_PATTERN.match(line_str)
            if not match:
                continue

        groups = match.groupdict()
        path = groups.get("path", "").strip()
        
        # Line number
        line_num = 1
        raw_line = groups.get("line")
        if raw_line:
            try:
                line_num = int(raw_line)
            except ValueError:
                line_num = 1

        # Column
        col_num: Optional[int] = None
        raw_col = groups.get("col") or groups.get("column")
        if raw_col:
            try:
                col_num = int(raw_col)
            except ValueError:
                col_num = None

        # Severity
        sev_str = groups.get("severity")
        severity = Severity.from_str(sev_str)

        # Message
        msg = groups.get("message", "").strip()

        # Code / Rule
        code_str = groups.get("code")
        if not code_str and msg:
            m = RULE_CODE_PATTERN.search(msg)
            if m:
                code_str = m.group(1)

        code_rule = CodeRule(value=code_str) if code_str else None

        diag = Diagnostic(
            message=msg,
            location=Location(
                path=path,
                range=Range(start=Position(line=line_num, column=col_num)),
            ),
            severity=severity,
            code=code_rule,
            source_name="line-parser",
        )
        results.append(diag)

    return results


def parse_diagnostics(
    raw_content: str,
    format_type: str = "auto",
    pattern: Optional[Union[str, re.Pattern]] = None,
) -> List[Diagnostic]:
    """Universal diagnostic parser dispatcher.

    format_type:
    - 'auto': Autodetects XML (starts with '<'), JSON/JSONL (starts with '{' or '['), or text line format
    - 'rdjson', 'json': Reviewdog Diagnostic JSON
    - 'rdjsonl', 'jsonl': Reviewdog JSON Lines
    - 'checkstyle', 'xml': Checkstyle XML
    - 'line', 'regex', 'text', 'errorformat': Regex-based line format
    """
    if not raw_content or not raw_content.strip():
        return []

    stripped = raw_content.strip()
    fmt = format_type.lower().strip()

    if fmt == "auto":
        if stripped.startswith("<"):
            return parse_checkstyle(stripped)
        elif stripped.startswith("{") or stripped.startswith("["):
            # Could be rdjson or first line of rdjsonl
            try:
                return parse_rdjson(stripped)
            except ValueError:
                return parse_rdjsonl(stripped)
        else:
            return parse_line_format(stripped, pattern=pattern)

    if fmt in ("rdjson", "json"):
        return parse_rdjson(stripped)
    elif fmt in ("rdjsonl", "jsonl"):
        return parse_rdjsonl(stripped)
    elif fmt in ("checkstyle", "xml"):
        return parse_checkstyle(stripped)
    elif fmt in ("line", "regex", "text", "errorformat"):
        return parse_line_format(stripped, pattern=pattern)
    else:
        raise ValueError(
            f"Unknown diagnostic format '{format_type}'. Supported: auto, rdjson, rdjsonl, checkstyle, line"
        )
