from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PolicyViolation:
    rule_id: str
    policy_name: str
    description: str
    remediation: str


PROHIBITED_ENTERPRISE_MODULES = [
    ("POL-MOD-001", "pickle", "Insecure Python deserialization enables Remote Code Execution (RCE)"),
    ("POL-MOD-002", "telnetlib", "Unencrypted legacy protocol insecure for enterprise traffic"),
    ("POL-MOD-003", "pycrypto", "Deprecated cryptographic library with known vulnerabilities (use cryptography)"),
]

PROHIBITED_LICENSES = ["AGPL-3.0", "GPL-3.0", "SSPL", "Commons Clause"]


class EnterprisePolicyEngine:
    """Enforces corporate compliance, legal licensing, and prohibited libraries."""

    @staticmethod
    def audit_enterprise_policies(code: str) -> Tuple[bool, List[PolicyViolation]]:
        violations: List[PolicyViolation] = []

        # 1. Check for prohibited unsafe libraries
        for rule_id, mod, reason in PROHIBITED_ENTERPRISE_MODULES:
            if re.search(rf"\bimport\s+{mod}\b", code) or re.search(rf"\bfrom\s+{mod}\s+import", code):
                violations.append(
                    PolicyViolation(
                        rule_id=rule_id,
                        policy_name="Prohibited Insecure Library",
                        description=f"Import of '{mod}' violates Enterprise Security Baseline: {reason}.",
                        remediation=f"Replace '{mod}' with an approved enterprise alternative (e.g., json, cryptography).",
                    )
                )

        # 2. Check for viral copyleft license headers
        for lic in PROHIBITED_LICENSES:
            if lic.lower() in code.lower():
                violations.append(
                    PolicyViolation(
                        rule_id="POL-LIC-001",
                        policy_name="Forbidden Viral Copyleft License",
                        description=f"Reference to restricted license '{lic}' violates corporate IP policies.",
                        remediation="Use corporate approved permissive licenses: MIT or Apache-2.0.",
                    )
                )

        # 3. Check for mandatory type hints in function declarations
        untyped_funcs = re.findall(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:", code)
        if untyped_funcs and len(untyped_funcs) > 2:
            violations.append(
                PolicyViolation(
                    rule_id="POL-TYP-001",
                    policy_name="Mandatory Enterprise Type Hints",
                    description="Functions detected without explicit return type annotations ('-> Type:').",
                    remediation="Add strict PEP 484 type annotations to all exported functions.",
                )
            )

        passed = len(violations) == 0
        return passed, violations
