"""Data models for Reverse Engineering and Analysis (REA) subsystem.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ArtifactInspection:
    """Inspection report for a target binary, package, or source artifact."""
    target_path: str
    size_bytes: int
    sha256: str
    format: str  # "ELF", "PE", "ZIP", "PYC", "TEXT", "UNKNOWN"
    is_binary: bool
    mime_type: str = "application/octet-stream"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def path(self) -> str:
        """Alias for target_path."""
        return self.target_path

    @property
    def size(self) -> int:
        """Alias for size_bytes to satisfy various interface callers."""
        return self.size_bytes

    @property
    def file_size(self) -> int:
        """Alias for size_bytes."""
        return self.size_bytes

    @property
    def detected_format(self) -> str:
        """Alias for format."""
        return self.format

    def to_dict(self) -> Dict[str, Any]:
        """Convert inspection to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert inspection to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class DisassemblyResult:
    """Disassembly and opcode analysis result for bytecode or binary code."""
    target_path: str
    target_format: str  # "PYC", "PYTHON_SOURCE", "BINARY_HEURISTICS", "RAW"
    architecture: str  # "cpython-bytecode", "x86_64", "arm64", "generic"
    instructions: List[Dict[str, Any]] = field(default_factory=list)
    symbols: List[str] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    opcode_counts: Dict[str, int] = field(default_factory=dict)
    complexity_score: int = 1
    heuristics: Dict[str, Any] = field(default_factory=dict)
    raw_listing: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert disassembly result to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert disassembly result to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class EvidenceRecord:
    """Immutable cryptographically-hashed evidence record (ev_<sha256>)."""
    evidence_id: str  # Format: "ev_<64-hex>"
    claim: str
    artifact_path: str
    sha256: str
    timestamp: float
    iso_timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)
    inferences: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    parent_evidence_id: Optional[str] = None
    signature: Optional[str] = None

    @property
    def target_sha256(self) -> str:
        """Alias for sha256 to support multiple caller conventions."""
        return self.sha256

    def to_dict(self) -> Dict[str, Any]:
        """Convert evidence record to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert evidence record to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
