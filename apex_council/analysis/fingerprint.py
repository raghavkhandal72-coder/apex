"""
Apex Crash Fingerprint Engine (Feature #14).
Generates deterministic, normalized SHA-256 crash fingerprints from Python tracebacks.
Normalizes away fluctuating line numbers, memory addresses, and timestamps to deduplicate bugs.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
LINE_NO_RE = re.compile(r", line \d+,")
FILE_PATH_RE = re.compile(r'File "([^"]+)"')


@dataclass(frozen=True)
class CrashFingerprint:
    sha256_hash: str
    error_type: str
    error_message: str
    crash_file: str
    crash_function: str
    normalized_signature: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.sha256_hash,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "crash_file": self.crash_file,
            "crash_function": self.crash_function,
            "signature": self.normalized_signature,
        }


def compute_crash_fingerprint(traceback_text: str) -> Optional[CrashFingerprint]:
    """Parse traceback, normalize variable tokens, and calculate deterministic hash."""
    if not traceback_text or not traceback_text.strip():
        return None

    # 1. Extract error type and message
    err_match = re.search(r"([\w\.]+Error|Exception):\s*(.*)", traceback_text)
    if err_match:
        err_type = err_match.group(1).split(".")[-1]
        err_msg = err_match.group(2).strip()
    else:
        err_type = "UnknownException"
        err_msg = ""

    # 2. Extract stack frames: (file, function)
    frames: List[tuple[str, str]] = []
    for line in traceback_text.splitlines():
        # Match: File "foo.py", line 42, in my_func
        m = re.search(r'File\s+"([^"]+)",\s+line\s+\d+,\s+in\s+([A-Za-z0-9_<>]+)', line)
        if m:
            filepath = os.path.basename(m.group(1))
            func = m.group(2)
            frames.append((filepath, func))

    if not frames:
        # Fallback if standard traceback frame not detected
        crash_file = "unknown"
        crash_func = "unknown"
    else:
        crash_file, crash_func = frames[-1]

    # 3. Create normalized signature
    # Format: ERROR_TYPE | (file:func) -> (file:func)
    chain = " -> ".join([f"{f}:{fn}" for f, fn in frames])
    normalized_signature = f"{err_type}:{chain}"
    # Strip any memory pointers
    normalized_signature = HEX_ADDR_RE.sub("0xADDR", normalized_signature)

    # 4. Compute SHA-256
    sha256 = hashlib.sha256(normalized_signature.encode("utf-8")).hexdigest()

    return CrashFingerprint(
        sha256_hash=sha256,
        error_type=err_type,
        error_message=HEX_ADDR_RE.sub("0xADDR", err_msg),
        crash_file=crash_file,
        crash_function=crash_func,
        normalized_signature=normalized_signature,
    )


def format_fingerprint_report(fp: CrashFingerprint) -> str:
    """Format human-readable fingerprint report for terminal or CI/CD logs."""
    return (
        f"APEX CRASH FINGERPRINT\n"
        f"────────────────────────────────────────────────────────────────\n"
        f"Fingerprint ID : {fp.sha256_hash[:16]} ({fp.sha256_hash})\n"
        f"Error Type     : {fp.error_type}\n"
        f"Crash Location : {fp.crash_file} :: {fp.crash_function}\n"
        f"Normalized Sig : {fp.normalized_signature}\n"
        f"Message        : {fp.error_message}\n"
        f"────────────────────────────────────────────────────────────────\n"
        f"Deduplication  : Identical crashes produce identical fingerprint.\n"
    )
