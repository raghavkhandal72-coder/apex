"""Linux Kernel Static Code & checkpatch.pl Compliance Auditor.
Zero external dependencies (pip = 0). Standard library only.
Grounded in Linux Kernel Documentation/process/coding-style.rst.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class KernelViolation:
    line_no: int
    rule: str
    severity: str  # ERROR, WARNING, CHECK
    message: str
    line_text: str = ""


@dataclass
class CheckpatchReport:
    file_path: str
    total_lines: int
    errors: int
    warnings: int
    checks: int
    violations: List[KernelViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.errors == 0


class LinuxCheckpatchAuditor:
    """Static Analyzer enforcing Linus Torvalds' Linux Kernel Coding Style."""

    BANNED_FUNCTIONS = {
        "strcpy": "Use strscpy() or strscpy_pad() instead of unsafe strcpy()",
        "strcat": "Use strlcat() instead of strcat()",
        "sprintf": "Use snprintf() or scnprintf() to avoid buffer overflows",
        "vsprintf": "Use vsnprintf() instead of vsprintf()",
        "gets": "gets() is forbidden; use safe bounds-checked input",
    }

    @classmethod
    def audit_source(cls, source_code: str, file_path: str = "<memory>") -> CheckpatchReport:
        lines = source_code.splitlines()
        violations: List[KernelViolation] = list()

        in_spinlock = False
        has_spdx = False
        has_signed_off = False

        for idx, line in enumerate(lines, 1):
            # 1. Check SPDX license header
            if "SPDX-License-Identifier:" in line:
                has_spdx = True

            # 2. Check Signed-off-by trailer
            if re.search(r"^\s*Signed-off-by:\s+[\w\s\.-]+<.+@.+>", line, re.IGNORECASE):
                has_signed_off = True

            # 3. Line length check (Linus: 80 cols preferred, max 100)
            expanded_len = len(line.expandtabs(8))
            if expanded_len > 100 and not any(k in line for k in ["http://", "https://", "PTRACE_", "MODULE_PARM_DESC"]):
                violations.append(KernelViolation(
                    line_no=idx,
                    rule="LINE_SPACING_100",
                    severity="WARNING",
                    message=f"Line exceeds 100 characters ({expanded_len} chars)",
                    line_text=line.strip()[:60] + "...",
                ))

            # 4. Indentation: Linux kernel strictly mandates 8-char tabs
            leading_spaces = len(line) - len(line.lstrip(" "))
            if leading_spaces >= 4 and not line.strip().startswith("*") and not line.strip().startswith("/*"):
                if re.match(r"^ {2,8}[a-zA-Z0-9_]", line):
                    violations.append(KernelViolation(
                        line_no=idx,
                        rule="CODE_STYLE_TABS",
                        severity="ERROR",
                        message="Linux kernel mandates 8-space tabs for indentation, spaces detected",
                        line_text=line.strip()[:60],
                    ))

            # 5. Trailing whitespace
            if line.endswith(" ") or line.endswith("\t"):
                violations.append(KernelViolation(
                    line_no=idx,
                    rule="TRAILING_WHITESPACE",
                    severity="WARNING",
                    message="Trailing whitespace detected",
                    line_text=line.strip()[:60],
                ))

            # 6. Banned unsafe C string functions
            for banned, advice in cls.BANNED_FUNCTIONS.items():
                if re.search(rf"\b{banned}\s*\(", line):
                    violations.append(KernelViolation(
                        line_no=idx,
                        rule=f"BANNED_FN_{banned.upper()}",
                        severity="ERROR",
                        message=advice,
                        line_text=line.strip()[:60],
                    ))

            # 7. Atomic context & GFP_KERNEL deadlock detection
            if re.search(r"\bspin_lock(_irqsave|_bh|_irq)?\s*\(", line):
                in_spinlock = True
            if re.search(r"\bspin_unlock(_irqrestore|_bh|_irq)?\s*\(", line):
                in_spinlock = False

            if in_spinlock and "GFP_KERNEL" in line and ("kmalloc" in line or "kzalloc" in line):
                violations.append(KernelViolation(
                    line_no=idx,
                    rule="ATOMIC_GFP_KERNEL_DEADLOCK",
                    severity="ERROR",
                    message="Cannot use GFP_KERNEL in atomic spinlock context! Potential kernel sleep/deadlock. Use GFP_ATOMIC.",
                    line_text=line.strip()[:60],
                ))

            # 8. Missing IS_ERR check after kernel functions returning ERR_PTR
            if re.search(r"\b(device_create|class_create|kthread_run)\s*\(", line):
                # Lookahead next 5 lines for IS_ERR
                lookahead = "\n".join(lines[idx:idx + 5])
                if "IS_ERR" not in lookahead and "PTR_ERR" not in lookahead and "IS_ERR_OR_NULL" not in lookahead:
                    violations.append(KernelViolation(
                        line_no=idx,
                        rule="UNCHECKED_ERR_PTR",
                        severity="WARNING",
                        message="Kernel pointer function returns ERR_PTR. Must check with IS_ERR() before dereferencing.",
                        line_text=line.strip()[:60],
                    ))

            # 9. Assignment inside if condition: if ((ret = func())) -> frowned upon
            if re.search(r"\bif\s*\(\s*\([a-zA-Z0-9_]+\s*=\s*[^=]", line):
                violations.append(KernelViolation(
                    line_no=idx,
                    rule="ASSIGN_IN_IF",
                    severity="CHECK",
                    message="Do not assign in if condition: separate assignment from predicate check.",
                    line_text=line.strip()[:60],
                ))

        if not has_spdx and len(lines) > 5:
            violations.append(KernelViolation(
                line_no=1,
                rule="MISSING_SPDX_HEADER",
                severity="ERROR",
                message="Missing required SPDX-License-Identifier header (e.g. // SPDX-License-Identifier: GPL-2.0)",
            ))

        errors = sum(1 for v in violations if v.severity == "ERROR")
        warnings = sum(1 for v in violations if v.severity == "WARNING")
        checks = sum(1 for v in violations if v.severity == "CHECK")

        return CheckpatchReport(
            file_path=file_path,
            total_lines=len(lines),
            errors=errors,
            warnings=warnings,
            checks=checks,
            violations=violations,
        )

    @classmethod
    def audit_file(cls, path: str | Path) -> CheckpatchReport:
        p = Path(path)
        if not p.exists():
            return CheckpatchReport(str(p), 0, 1, 0, 0, [KernelViolation(0, "FILE_NOT_FOUND", "ERROR", f"File '{p}' does not exist")])
        code = p.read_text(encoding="utf-8", errors="replace")
        return cls.audit_source(code, file_path=str(p))
