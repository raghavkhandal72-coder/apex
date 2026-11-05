"""Data models for apex_council.reviewdog subsystem.

Codifies the Reviewdog diagnostic object model:
- Severity (INFO, WARNING, ERROR)
- Position (line, column)
- Range (start, end)
- Location (path, range)
- CodeRule (value, url)
- Suggestion (range, text)
- Diagnostic (message, location, severity, code, suggestions, source_name)
- ReviewResult (total_findings, reported_findings, filter_mode, diagnostics, raw_output)

Pure Python 3 standard library (zero external dependencies).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """Diagnostic severity level."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    @classmethod
    def from_str(cls, val: str | None) -> Severity:
        """Parse severity from string flexibly."""
        if not val:
            return cls.WARNING
        s = str(val).strip().upper()
        if s in ("ERROR", "ERR", "FATAL", "CRITICAL"):
            return cls.ERROR
        if s in ("INFO", "NOTE", "HINT", "SUGGESTION", "NOTICE"):
            return cls.INFO
        if s in ("WARNING", "WARN"):
            return cls.WARNING
        return cls.WARNING


@dataclass
class Position:
    """1-indexed source code position."""
    line: int
    column: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"line": self.line}
        if self.column is not None:
            d["column"] = self.column
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        if not isinstance(data, dict):
            return cls(line=1)
        line = int(data.get("line", 1))
        col_val = data.get("column")
        col = int(col_val) if col_val is not None else None
        return cls(line=line, column=col)


@dataclass
class Range:
    """Source code range with start and optional end position."""
    start: Position
    end: Optional[Position] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"start": self.start.to_dict()}
        if self.end is not None:
            d["end"] = self.end.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Range:
        if not isinstance(data, dict):
            return cls(start=Position(line=1))
        start_data = data.get("start", {"line": 1})
        start = Position.from_dict(start_data)
        end_data = data.get("end")
        end = Position.from_dict(end_data) if end_data else None
        return cls(start=start, end=end)


@dataclass
class Location:
    """File path and line/column range."""
    path: str
    range: Range

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "range": self.range.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        if not isinstance(data, dict):
            return cls(path="", range=Range(start=Position(line=1)))
        return cls(
            path=str(data.get("path", "")),
            range=Range.from_dict(data.get("range", {})),
        )


@dataclass
class CodeRule:
    """Lint rule or diagnostic code identifier."""
    value: str
    url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"value": self.value}
        if self.url:
            d["url"] = self.url
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> CodeRule:
        if isinstance(data, str):
            return cls(value=data)
        if isinstance(data, dict):
            return cls(
                value=str(data.get("value", "")),
                url=data.get("url"),
            )
        return cls(value=str(data))


@dataclass
class Suggestion:
    """Code replacement suggestion for a diagnostic."""
    range: Range
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "range": self.range.to_dict(),
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Suggestion:
        if not isinstance(data, dict):
            return cls(range=Range(start=Position(line=1)), text="")
        return cls(
            range=Range.from_dict(data.get("range", {})),
            text=str(data.get("text", "")),
        )


@dataclass
class Diagnostic:
    """Unified Reviewdog diagnostic report item."""
    message: str
    location: Location
    severity: Severity = Severity.WARNING
    code: Optional[CodeRule] = None
    suggestions: List[Suggestion] = field(default_factory=list)
    source_name: str = "apex-council"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "message": self.message,
            "location": self.location.to_dict(),
            "severity": self.severity.value,
            "source_name": self.source_name,
        }
        if self.code:
            d["code"] = self.code.to_dict()
        if self.suggestions:
            d["suggestions"] = [s.to_dict() for s in self.suggestions]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnostic:
        loc_data = data.get("location", {})
        loc = Location.from_dict(loc_data)
        code_data = data.get("code")
        code = CodeRule.from_dict(code_data) if code_data else None
        suggestions = [
            Suggestion.from_dict(s) for s in data.get("suggestions", [])
        ]
        
        # Determine source_name: check direct, or inside 'source' dict
        source = data.get("source_name")
        if not source and isinstance(data.get("source"), dict):
            source = data["source"].get("name")
        if not source:
            source = "apex-council"

        return cls(
            message=str(data.get("message", "")),
            location=loc,
            severity=Severity.from_str(data.get("severity")),
            code=code,
            suggestions=suggestions,
            source_name=source,
        )

    @classmethod
    def create(
        cls,
        path: str,
        line: int,
        message: str,
        column: Optional[int] = None,
        severity: str = "WARNING",
        code: Optional[str] = None,
        source: str = "apex-council",
        suggestions: Optional[List[Suggestion]] = None,
    ) -> Diagnostic:
        """Convenience factory method to build a Diagnostic in one call."""
        pos = Position(line=line, column=column)
        loc = Location(path=path, range=Range(start=pos))
        rule = CodeRule(value=code) if code else None
        return cls(
            message=message,
            location=loc,
            severity=Severity.from_str(severity),
            code=rule,
            suggestions=suggestions or [],
            source_name=source,
        )


@dataclass
class ReviewResult:
    """Summary of a reviewdog review execution."""
    total_findings: int
    reported_findings: int
    filter_mode: str
    diagnostics: List[Diagnostic]
    raw_output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_findings": self.total_findings,
            "reported_findings": self.reported_findings,
            "filter_mode": self.filter_mode,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "raw_output": self.raw_output,
        }
