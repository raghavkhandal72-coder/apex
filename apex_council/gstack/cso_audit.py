#!/usr/bin/env python3
"""
Apex-Sovereign: Chief Security Officer (CSO) Threat Modeling & OWASP Audit
Inspired by garrytan/gstack (cso skill: OWASP + STRIDE threat analysis)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import ast
import dataclasses
import re
from typing import Any, Dict, List, Optional


@dataclasses.dataclass(frozen=True)
class CSOThreatFinding:
    stride_category: str  # Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation
    owasp_top10: str       # e.g., A03:2021-Injection
    severity: str          # CRITICAL, HIGH, MEDIUM, LOW
    line_number: Optional[int]
    description: str
    remediation: str


@dataclasses.dataclass(frozen=True)
class CSOSecurityAuditReport:
    target_name: str
    security_score: float  # 0.0 to 10.0
    passed: bool
    findings: List[CSOThreatFinding]
    summary: str


class ChiefSecurityOfficerEngine:
    """
    Simulates Garry Tan's gstack /cso: Static security auditing and
    STRIDE threat modeling over source code and diffs.
    """

    DANGEROUS_PATTERNS = [
        # (pattern, stride, owasp, severity, description, remediation)
        (r"\beval\s*\(", "Elevation of Privilege", "A03:2021-Injection", "CRITICAL", "Dynamic eval() invocation detected", "Replace eval() with ast.literal_eval() or explicit parser"),
        (r"\bexec\s*\(", "Elevation of Privilege", "A03:2021-Injection", "CRITICAL", "Dynamic exec() invocation detected", "Eliminate exec() in favor of deterministic function dispatch"),
        (r"\bos\.system\s*\(", "Elevation of Privilege", "A03:2021-Injection", "HIGH", "os.system shell execution detected", "Use subprocess.run with shell=False and validated argv list"),
        (r"\bpickle\.loads?\b", "Tampering", "A08:2021-Software and Data Integrity Failures", "HIGH", "Insecure deserialization via pickle", "Use json or safe serialization protocols"),
        (r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]", "Information Disclosure", "A07:2021-Identification and Authentication Failures", "HIGH", "Hardcoded credential/secret detected", "Load secrets via environment variables or secret store"),
        (r"cursor\.execute\s*\(\s*['\"].*?%s", "Tampering", "A03:2021-Injection", "HIGH", "Potential SQL string formatting injection", "Use parameterized queries with prepared statements"),
        (r"(?:while\s+True|for\s+.*in\s+iter)\b(?!.*(?:break|return|sleep))", "Denial of Service", "A04:2021-Insecure Design", "MEDIUM", "Unbounded loop without explicit break or timeout", "Ensure loop termination guarantees and timeout guards"),
        (r"except\s*:\s*(?:pass|continue)", "Repudiation", "A09:2021-Security Logging and Monitoring Failures", "MEDIUM", "Bare except swallowing all exceptions silently", "Log exception details and handle specific exception types"),
    ]

    @classmethod
    def audit_code(cls, source_code: str, target_name: str = "source_code") -> CSOSecurityAuditReport:
        findings: List[CSOThreatFinding] = []
        lines = source_code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # Skip comments

            for pattern, stride, owasp, severity, desc, remed in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, line):
                    findings.append(
                        CSOThreatFinding(
                            stride_category=stride,
                            owasp_top10=owasp,
                            severity=severity,
                            line_number=idx,
                            description=f"{desc} at line {idx}",
                            remediation=remed,
                        )
                    )

        # Calculate score: start at 10.0, deduct based on severity
        score = 10.0
        for f in findings:
            if f.severity == "CRITICAL":
                score -= 3.5
            elif f.severity == "HIGH":
                score -= 2.0
            elif f.severity == "MEDIUM":
                score -= 1.0
            elif f.severity == "LOW":
                score -= 0.5
        score = max(0.0, min(10.0, score))

        passed = not any(f.severity in {"CRITICAL", "HIGH"} for f in findings)
        summary = (
            f"CSO Security Audit PASSED ({score:.1f}/10.0). No critical STRIDE threat vectors detected."
            if passed
            else f"CSO Security Audit FAILED ({score:.1f}/10.0). {len(findings)} threats identified requiring remediation."
        )

        return CSOSecurityAuditReport(
            target_name=target_name,
            security_score=score,
            passed=passed,
            findings=findings,
            summary=summary,
        )
