from __future__ import annotations

import ast
import re
from typing import List, Tuple


def evaluate_security(code: str) -> Tuple[float, List[str]]:
    """Evaluates security quality of a code snippet (0.0 to 100.0).

    Penalizes dangerous patterns:
    - shell=True or os.system (Command Injection)
    - Unsanitized open() with format strings (Path Traversal)
    - Hardcoded credentials or tokens
    - Dangerous eval/exec usage
    """
    issues: List[str] = []
    penalty = 0.0

    # 1. Check for command injection
    if re.search(r"os\.system\s*\(", code) or re.search(r"os\.popen\s*\(", code):
        issues.append("CWE-78: os.system or os.popen detected (Command Injection hazard)")
        penalty += 35.0

    if re.search(r"subprocess\.[a-zA-Z_]+\s*\(.*shell\s*=\s*True", code):
        issues.append("CWE-78: subprocess execution with shell=True detected")
        penalty += 35.0

    # 2. Check for dangerous eval/exec
    if re.search(r"\b(?:eval|exec)\s*\(", code):
        issues.append("CWE-95: Dangerous use of dynamic eval() or exec()")
        penalty += 40.0

    # 3. Check for hardcoded API keys
    if re.search(r"(?:sk-ant-|sk-proj-|AKIA)[a-zA-Z0-9_\-]{20,}", code):
        issues.append("CWE-798: Hardcoded API credentials detected")
        penalty += 40.0

    # 4. Check for path traversal in open()
    if re.search(r"open\s*\(\s*f[\"'].*\{.*path.*\}", code, re.IGNORECASE):
        issues.append("CWE-22: Naive string-formatted open() vulnerable to path traversal")
        penalty += 25.0

    # 5. Check for bare excepts (bad error masking)
    if re.search(r"except:\s*$", code, re.MULTILINE):
        issues.append("CWE-391: Bare 'except:' masks critical exceptions")
        penalty += 10.0

    score = max(0.0, 100.0 - penalty)
    return score, issues
