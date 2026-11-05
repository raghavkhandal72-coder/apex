"""Reverse Engineering and Analysis (REA) subsystem for Apex Sovereign.
Provides binary format inspection, Python bytecode & multi-arch disassembly heuristics,
and an immutable cryptographic Evidence Ledger (ev_<sha256>).
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

from .disassembler import (
    analyze_native_binary_heuristics,
    disassemble_code,
    disassemble_source,
    disassemble_target,
    extract_strings,
)
from .evidence import EvidenceLedger
from .inspector import (
    detect_format,
    inspect_artifact,
    inspect_bytes,
)
from .models import (
    ArtifactInspection,
    DisassemblyResult,
    EvidenceRecord,
)

__all__ = [
    "ArtifactInspection",
    "DisassemblyResult",
    "EvidenceRecord",
    "EvidenceLedger",
    "inspect_artifact",
    "inspect_bytes",
    "detect_format",
    "disassemble_source",
    "disassemble_target",
    "disassemble_code",
    "extract_strings",
    "analyze_native_binary_heuristics",
]

__version__ = "1.0.0"
