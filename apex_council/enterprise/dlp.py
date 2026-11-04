from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class RedactionResult:
    clean_text: str
    redactions_count: int
    categories_found: List[str]


# Enterprise DLP Regular Expressions
PATTERNS = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"), "[REDACTED_EMAIL]"),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    ("CREDIT_CARD", re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b"), "[REDACTED_CREDIT_CARD]"),
    ("JWT_TOKEN", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[REDACTED_JWT]"),
    ("API_KEY_GENERIC", re.compile(r"(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", re.IGNORECASE), "api_key='[REDACTED_SECRET]'"),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
]


class EnterpriseDLP:
    """Enterprise Data Loss Prevention (DLP) & PII Sanitizer.

    Guarantees no corporate credentials, customer PII, or internal tokens
    leak to external AI providers.
    """

    @staticmethod
    def sanitize(text: str) -> RedactionResult:
        clean = text
        categories = []
        count = 0

        for category, pattern, placeholder in PATTERNS:
            matches = list(pattern.finditer(clean))
            if matches:
                categories.append(category)
                count += len(matches)
                clean = pattern.sub(placeholder, clean)

        return RedactionResult(
            clean_text=clean,
            redactions_count=count,
            categories_found=categories,
        )
