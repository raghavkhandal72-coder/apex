"""
Apex Secret Masker (Feature #70).
Scans logs, crash tracebacks, and terminal output to automatically redact sensitive credentials.
Protects Google API keys, OpenAI tokens, AWS keys, GitHub tokens, JWTs, and database URLs.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

import re
from typing import List, Pattern, Tuple


SECRET_PATTERNS: List[Tuple[str, Pattern[str]]] = [
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("AWS_KEY_ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_PAT", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("JWT_TOKEN", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),
    ("DB_CONN_STR", re.compile(r"(postgres|mysql|mongodb|redis)://[^:]+:([^@]+)@")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC )?PRIVATE KEY-----")),
]


def mask_secrets(text: str) -> Tuple[str, int]:
    """Scan and redact all sensitive credentials from text.
    
    Returns:
        (sanitized_text, count_of_redactions)
    """
    if not text:
        return text, 0

    sanitized = text
    total_redacted = 0

    for name, pattern in SECRET_PATTERNS:
        if name == "DB_CONN_STR":
            # For connection strings, redact only the password group
            matches = list(pattern.finditer(sanitized))
            if matches:
                total_redacted += len(matches)
                sanitized = pattern.sub(r"\1://***:***@\3" if False else r"\1://user:***[REDACTED_PASSWORD]***@", sanitized)
        else:
            matches = list(pattern.finditer(sanitized))
            if matches:
                total_redacted += len(matches)
                sanitized = pattern.sub(f"***[REDACTED_{name}]***", sanitized)

    return sanitized, total_redacted
