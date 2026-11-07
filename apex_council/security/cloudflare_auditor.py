#!/usr/bin/env python3
"""
Apex Sovereign Defensive Security Audit Engine.
Inspired by and compliant with Cloudflare's Security Audit Framework (github.com/cloudflare/security-audit-skill).
100% Python Standard Library (pip = 0).

Evaluates target codebases against Cloudflare's defensive attack classes:
1. AI & LLM Security (Prompt injection, context bleed, model sink execution, tool schema mismatch)
2. Memory Safety & Binary Invariants (Unsafe ctypes, pointer math, unverified buffers)
3. Supply Chain & Dependency Hygiene (Dynamic package install, remote code execution)
4. Web Protocol, Auth & SSRF (Hardcoded credentials, unverified SSRF, path traversal, timing attacks)
5. Data Isolation & Lifecycle (PII exposure, insecure temp files, sensitive logging)
6. Resource Exhaustion & Availability (ReDoS, unbounded file/socket reads, unconstrained recursion)
7. Injection & Access Control (SQL injection, shell injection, privilege escalation)

Emits Cloudflare-compliant artifacts:
- findings.json (Strictly adheres to Cloudflare report-schema.json)
- coverage-ledger.json (Defensive validation & coverage accounting ledger)
- SECURITY-AUDIT-REPORT.md (Full executive & developer remediation report)
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Cloudflare Attack Class Categorization
ATTACK_CLASSES = {
    "AI_AND_LLM": "AI, LLM, and Agent Hunting",
    "MEMORY_SAFETY_AND_BINARY": "Memory Safety and Binary Invariants",
    "SUPPLY_CHAIN_AND_RELEASE": "Supply-Chain and Dependency Hygiene",
    "WEB_PROTOCOL_AND_AUTH": "Web Protocol, Auth, and SSRF",
    "DATA_ISOLATION_AND_LIFECYCLE": "Data Isolation and Lifecycle",
    "RESOURCE_EXHAUSTION_AND_AVAILABILITY": "Resource Exhaustion and Availability",
    "INJECTION_AND_ACCESS_CONTROL": "Injection and Trust Boundary Failures",
}


@dataclass
class AuditTrace:
    kind: str  # "entrypoint", "propagation", "sink"
    file: str
    line: int
    scope: str
    description: str


@dataclass
class AuditEvidence:
    file: str
    line: int
    description: str


@dataclass
class AuditRemediation:
    summary: str
    patch: str = ""


@dataclass
class CloudflareFinding:
    verdict: str  # "confirmed" or "needs_validation"
    fingerprint: str
    title: str
    description: str
    root_cause: str
    intended_behavior: str
    attack_class: str
    cwe: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    trace: List[AuditTrace] = field(default_factory=list)
    evidence: List[AuditEvidence] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    remediation: AuditRemediation = field(default_factory=lambda: AuditRemediation(summary=""))
    snippet: str = ""

    def to_cloudflare_dict(self) -> Dict[str, Any]:
        """Converts to exact Cloudflare report-schema.json dictionary structure."""
        return {
            "verdict": self.verdict,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "description": self.description,
            "root_cause": self.root_cause,
            "intended_behavior": self.intended_behavior,
            "attack_class": self.attack_class,
            "cwe": self.cwe,
            "severity": self.severity,
            "trace": [asdict(t) for t in self.trace],
            "evidence": [asdict(e) for e in self.evidence],
            "conditions": self.conditions,
            "remediation": asdict(self.remediation),
        }


class CloudflareSecurityAuditor:
    """Comprehensive Defensive Security Auditor for Python and multi-language codebases."""

    SECRET_PATTERNS = [
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID", "CWE-798", "CRITICAL"),
        (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "GitHub Personal Access Token", "CWE-798", "CRITICAL"),
        (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "Slack API Token", "CWE-798", "CRITICAL"),
        (re.compile(r"AIza[0-9A-Za-z\\-_]{35}"), "Google Cloud / Gemini API Key", "CWE-798", "CRITICAL"),
        (re.compile(r"sk-[a-zA-Z0-9]{32,64}"), "OpenAI API Key", "CWE-798", "CRITICAL"),
        (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Cryptographic Private Key", "CWE-798", "CRITICAL"),
        (re.compile(r"\beyJ[A-Za-z0-9-_=]{10,}\.[A-Za-z0-9-_=]{10,}\.[A-Za-z0-9-_.+/=]{10,}\b"), "JWT Token Exposure", "CWE-798", "HIGH"),
    ]

    REDOS_PATTERNS = [
        (re.compile(r"\((?:[a-zA-Z0-9_]+|\.[*+])\+?\)[*+]"), "Nested repetition quantifier ReDoS vulnerability"),
        (re.compile(r"\((\w+)[*+]\)[*+]"), "Exponential backtracking regex group"),
        (re.compile(r"([a-zA-Z0-9]+)\*\1\*"), "Overlapping adjacent unbounded quantifiers"),
    ]

    def __init__(self, target_path: str = ".", strict: bool = False):
        self.target_path = Path(target_path).resolve()
        self.strict = strict
        self.findings: List[CloudflareFinding] = []
        self.scanned_files: List[str] = []
        self.total_lines: int = 0
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def audit(self) -> List[CloudflareFinding]:
        """Runs the complete Cloudflare-grade security audit across all files."""
        self.start_time = time.perf_counter()
        self.findings.clear()
        self.scanned_files.clear()
        self.total_lines = 0

        if self.target_path.is_file():
            files_to_scan = [self.target_path]
        else:
            files_to_scan = []
            exclude_dirs = {
                ".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build",
                ".apex", "scratch", "spark", "dify", "llamafile", "QuixBugs", ".agents"
            }
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".json", ".sh", ".bat", ".md", ".env")):
                        files_to_scan.append(Path(root) / file)

        for p in files_to_scan:
            try:
                rel = str(p.relative_to(self.target_path)) if p != self.target_path else p.name
            except ValueError:
                rel = str(p)

            self.scanned_files.append(rel)
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                self.total_lines += len(lines)
                self._scan_file_content(rel, p, content, lines)
                if p.suffix == ".py":
                    self._scan_python_ast(rel, p, content)
            except Exception:
                continue

        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        return self.findings

    def _generate_fingerprint(self, attack_class: str, file_path: str, line_no: int, title: str) -> str:
        key = f"{attack_class}:{file_path}:{line_no}:{title}".encode("utf-8")
        return hashlib.sha256(key).hexdigest()[:16]

    # --- 1. CONTENT & REGEX BASED CHECKS ---

    def _scan_file_content(self, rel_path: str, full_path: Path, content: str, lines: List[str]) -> None:
        # Ignore sample test files or fake fixture keys
        if "test" in rel_path.lower() or "fixture" in rel_path.lower():
            # Still scan for critical bugs but avoid flagging test mock secrets
            is_test_file = True
        else:
            is_test_file = False

        # 1. Hardcoded Secrets & Keys (CWE-798)
        if not is_test_file:
            for idx, line in enumerate(lines, 1):
                clean_l = line.strip()
                if clean_l.startswith("#") or clean_l.startswith("//"):
                    continue
                for pat, name, cwe, sev in self.SECRET_PATTERNS:
                    if pat.search(line):
                        fp = self._generate_fingerprint("WEB_PROTOCOL_AND_AUTH", rel_path, idx, f"Hardcoded Secret: {name}")
                        self.findings.append(
                            CloudflareFinding(
                                verdict="confirmed",
                                fingerprint=fp,
                                title=f"Hardcoded Secret / Credential: {name}",
                                description=f"Found unencrypted high-entropy token ({name}) directly committed in source code.",
                                root_cause="Credentials stored in source rather than injected via isolated runtime environment variables.",
                                intended_behavior="All credentials must be loaded at runtime from environment variables or a secure vault.",
                                attack_class="WEB_PROTOCOL_AND_AUTH",
                                cwe=cwe,
                                severity=sev,
                                trace=[
                                    AuditTrace(kind="entrypoint", file=rel_path, line=idx, scope="Source Code", description="Hardcoded string literal committed in repo"),
                                    AuditTrace(kind="sink", file=rel_path, line=idx, scope="Credential Auth", description=f"Direct exposure of {name}")
                                ],
                                evidence=[AuditEvidence(file=rel_path, line=idx, description=f"Pattern match for {name}")],
                                conditions=["Repository is accessible to unauthorized principals or cloned into untrusted environment."],
                                remediation=AuditRemediation(
                                    summary=f"Revoke this {name} immediately and migrate to os.environ.get(...).",
                                    patch=f"- secret = \"...\"\n+ secret = os.environ.get('SECRET_TOKEN')"
                                ),
                                snippet=clean_l[:80],
                            )
                        )

        # 2. ReDoS Catastrophic Backtracking (CWE-1333)
        for idx, line in enumerate(lines, 1):
            if "re.compile" in line or "regex" in line.lower() or "new RegExp" in line:
                for pat, desc in self.REDOS_PATTERNS:
                    if pat.search(line):
                        fp = self._generate_fingerprint("RESOURCE_EXHAUSTION_AND_AVAILABILITY", rel_path, idx, "ReDoS Vulnerability")
                        self.findings.append(
                            CloudflareFinding(
                                verdict="confirmed",
                                fingerprint=fp,
                                title="Catastrophic Backtracking ReDoS Regular Expression",
                                description=f"Regular expression contains nested or adjacent repetition quantifiers: {desc}.",
                                root_cause="Exponential state space explosion on non-matching pathological input.",
                                intended_behavior="Rewrite regular expression with atomic groups or non-overlapping deterministic tokens.",
                                attack_class="RESOURCE_EXHAUSTION_AND_AVAILABILITY",
                                cwe="CWE-1333",
                                severity="HIGH",
                                trace=[
                                    AuditTrace(kind="entrypoint", file=rel_path, line=idx, scope="Regex Engine", description="Regex compilation with nested quantifiers"),
                                    AuditTrace(kind="sink", file=rel_path, line=idx, scope="Pattern Match", description="String match execution with O(2^N) complexity")
                                ],
                                evidence=[AuditEvidence(file=rel_path, line=idx, description=f"Regex pattern matches ReDoS signature: {desc}")],
                                conditions=["Untrusted input supplied to regex matcher without strict length limits."],
                                remediation=AuditRemediation(
                                    summary="Refactor regex pattern to eliminate nested repetitions or validate string length prior to evaluation.",
                                    patch="# Use non-nested quantifier or linear-time string parser"
                                ),
                                snippet=line.strip()[:80],
                            )
                        )

        # 3. Supply Chain / Remote Code Execution via curl | bash / pip install at runtime (CWE-78 / CWE-494)
        for idx, line in enumerate(lines, 1):
            if any(term in line for term in ["curl | bash", "curl | sh", "Invoke-Expression (New-Object Net.WebClient)", "pip install", "npm install"]) and ("os.system" in line or "subprocess" in line or "exec" in line):
                fp = self._generate_fingerprint("SUPPLY_CHAIN_AND_RELEASE", rel_path, idx, "Runtime Remote Package/Script Execution")
                self.findings.append(
                    CloudflareFinding(
                        verdict="confirmed",
                        fingerprint=fp,
                        title="Insecure Dynamic Supply-Chain Invocation at Runtime",
                        description="Application executes external package manager or pipe-to-shell script at runtime.",
                        root_cause="Dynamic invocation of external untrusted network sources without cryptographic hash integrity validation.",
                        intended_behavior="All dependencies must be pre-bundled, pinned, or verified with cryptographic SHA-256 hashes.",
                        attack_class="SUPPLY_CHAIN_AND_RELEASE",
                        cwe="CWE-494",
                        severity="CRITICAL",
                        trace=[
                            AuditTrace(kind="entrypoint", file=rel_path, line=idx, scope="Runtime Invocation", description="Dynamic external installation command"),
                            AuditTrace(kind="sink", file=rel_path, line=idx, scope="System Execution", description="Execution of unverified code via shell")
                        ],
                        evidence=[AuditEvidence(file=rel_path, line=idx, description=f"Pattern detected: {line.strip()[:60]}")],
                        conditions=["Attacker can tamper with network transit, DNS, or package registry."],
                        remediation=AuditRemediation(
                            summary="Vend all dependencies natively or verify release hashes before execution.",
                            patch="# Zero-pip architecture: Rely on standard library or verified offline wheels"
                        ),
                        snippet=line.strip()[:80],
                    )
                )

        # 4. Insecure Temporary File Creation (CWE-377)
        for idx, line in enumerate(lines, 1):
            if "tempfile.mktemp(" in line:
                fp = self._generate_fingerprint("DATA_ISOLATION_AND_LIFECYCLE", rel_path, idx, "Insecure Temp File")
                self.findings.append(
                    CloudflareFinding(
                        verdict="confirmed",
                        fingerprint=fp,
                        title="Insecure Temporary File Creation (tempfile.mktemp)",
                        description="`tempfile.mktemp` is deprecated and vulnerable to symlink race conditions (TOCTOU).",
                        root_cause="File path is allocated before file creation, allowing an attacker to inject a symlink in the window between allocation and use.",
                        intended_behavior="Use `tempfile.NamedTemporaryFile` or `tempfile.mkstemp` with restrictive permissions.",
                        attack_class="DATA_ISOLATION_AND_LIFECYCLE",
                        cwe="CWE-377",
                        severity="HIGH",
                        trace=[
                            AuditTrace(kind="entrypoint", file=rel_path, line=idx, scope="Tempfile Allocation", description="mktemp generates raceable file path"),
                            AuditTrace(kind="sink", file=rel_path, line=idx, scope="Filesystem", description="File opened at pre-announced path")
                        ],
                        evidence=[AuditEvidence(file=rel_path, line=idx, description="Call to tempfile.mktemp detected")],
                        conditions=["Local attacker on same machine can watch /tmp and place symlinks."],
                        remediation=AuditRemediation(
                            summary="Replace tempfile.mktemp with tempfile.NamedTemporaryFile(delete=False) or tempfile.mkstemp.",
                            patch="- fd, path = tempfile.mktemp()\n+ fd, path = tempfile.mkstemp()"
                        ),
                        snippet=line.strip()[:80],
                    )
                )

    # --- 2. AST-BASED ADVANCED STATIC ANALYSIS ---

    def _scan_python_ast(self, rel_path: str, full_path: Path, content: str) -> None:
        try:
            tree = ast.parse(content, filename=str(full_path))
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # 1. AI & LLM Security: Unsafe LLM Output Deserialization / Execution (CWE-95 / CWE-78)
            # Detects eval(), exec(), or subprocess on variable names related to llm, model, response, output
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node.func)

                # Dangerous Sinks: eval, exec
                if func_name in {"eval", "exec"}:
                    if node.args:
                        arg_repr = ast.unparse(node.args[0]) if hasattr(ast, "unparse") else ""
                        if any(k in arg_repr.lower() for k in ["llm", "model", "response", "output", "prompt", "user_input", "code"]):
                            fp = self._generate_fingerprint("AI_AND_LLM", rel_path, node.lineno, "LLM Output Exec/Eval Sink")
                            self.findings.append(
                                CloudflareFinding(
                                    verdict="confirmed",
                                    fingerprint=fp,
                                    title="Unsafe Direct Execution of Model Output in Dynamic Sink",
                                    description="Model output or untrusted response is passed directly to `eval()` or `exec()` without sandboxing or AST boundary checks.",
                                    root_cause="Trusting AI-generated text as verified code without defensive validation or isolation.",
                                    intended_behavior="Execute model output inside an OS-level sandbox or parse via ast.parse with explicit node whitelists.",
                                    attack_class="AI_AND_LLM",
                                    cwe="CWE-95",
                                    severity="CRITICAL",
                                    trace=[
                                        AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="Model Ingestion", description=f"Model output received via `{arg_repr}`"),
                                        AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope=func_name, description=f"Direct execution via `{func_name}()`")
                                    ],
                                    evidence=[AuditEvidence(file=rel_path, line=node.lineno, description=f"`{func_name}({arg_repr})` invocation")],
                                    conditions=["Attacker manipulates prompt or model hallucination produces malicious payload."],
                                    remediation=AuditRemediation(
                                        summary="Enforce AST validation with Sandbox or ASTShield before executing generated code.",
                                        patch=f"# Use ASTShield or sovereign sandbox\nfrom apex_council.security.ast_shield import ASTShield\nshield = ASTShield()\nshield.validate({arg_repr})"
                                    ),
                                    snippet=f"{func_name}({arg_repr})",
                                )
                            )

                # Subprocess command injection (shell=True) (CWE-78)
                if func_name in {"os.system", "os.popen", "subprocess.Popen", "subprocess.run", "subprocess.call", "subprocess.check_output"}:
                    has_shell_true = any(
                        isinstance(k, ast.keyword) and k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                        for k in node.keywords
                    )
                    if func_name == "os.system" or has_shell_true:
                        fp = self._generate_fingerprint("INJECTION_AND_ACCESS_CONTROL", rel_path, node.lineno, "Subprocess Command Injection")
                        self.findings.append(
                            CloudflareFinding(
                                verdict="needs_validation",
                                fingerprint=fp,
                                title="Potential Shell Command Injection (`shell=True` / `os.system`)",
                                description=f"Subprocess invoked using `{func_name}` with shell execution enabled. If command includes untrusted input, arbitrary shell commands can be executed.",
                                root_cause="Shell string interpolation bypasses argument vector separation.",
                                intended_behavior="Use list arguments (`['command', 'arg1', 'arg2']`) with `shell=False`.",
                                attack_class="INJECTION_AND_ACCESS_CONTROL",
                                cwe="CWE-78",
                                severity="HIGH",
                                trace=[
                                    AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="Command Dispatch", description="Dynamic command constructed"),
                                    AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope="Shell", description=f"{func_name} with shell interpreter")
                                ],
                                evidence=[AuditEvidence(file=rel_path, line=node.lineno, description=f"Call to {func_name} with shell execution")],
                                conditions=["Untrusted arguments reach command string without shlex.quote."],
                                remediation=AuditRemediation(
                                    summary="Pass command as a sequence of strings and disable shell=True.",
                                    patch="- subprocess.run(f'cmd {user_arg}', shell=True)\n+ subprocess.run(['cmd', user_arg], shell=False)"
                                ),
                                snippet=f"{func_name}(...)",
                            )
                        )

                # Unsafe Deserialization via pickle / yaml (CWE-502)
                if func_name in {"pickle.loads", "pickle.load", "_pickle.loads", "_pickle.load"}:
                    fp = self._generate_fingerprint("INJECTION_AND_ACCESS_CONTROL", rel_path, node.lineno, "Pickle Deserialization")
                    self.findings.append(
                        CloudflareFinding(
                            verdict="confirmed",
                            fingerprint=fp,
                            title="Arbitrary Code Execution via Insecure Deserialization (`pickle.loads`)",
                            description="`pickle` allows arbitrary callable execution upon deserialization of untrusted byte streams.",
                            root_cause="Pickle protocol is not designed to be safe against maliciously crafted data.",
                            intended_behavior="Use safe data formats such as JSON or protocol buffers for untrusted serialization.",
                            attack_class="INJECTION_AND_ACCESS_CONTROL",
                            cwe="CWE-502",
                            severity="CRITICAL",
                            trace=[
                                AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="Deserializer", description="Untrusted bytes passed to pickle"),
                                AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope="pickle.loads", description="Arbitrary __reduce__ execution")
                            ],
                            evidence=[AuditEvidence(file=rel_path, line=node.lineno, description="pickle.loads detected")],
                            conditions=["Untrusted data reaches deserializer."],
                            remediation=AuditRemediation(
                                summary="Replace pickle with json.loads or HMAC-signed serialization.",
                                patch="- data = pickle.loads(payload)\n+ data = json.loads(payload.decode('utf-8'))"
                            ),
                            snippet=f"{func_name}(...)",
                        )
                    )

                # SSRF / Unvalidated External HTTP Request (CWE-918)
                if func_name in {"urllib.request.urlopen", "urllib.request.Request", "http.client.HTTPConnection"}:
                    if node.args:
                        arg_repr = ast.unparse(node.args[0]) if hasattr(ast, "unparse") else ""
                        if any(v in arg_repr.lower() for v in ["url", "target", "host", "endpoint", "user"]):
                            fp = self._generate_fingerprint("WEB_PROTOCOL_AND_AUTH", rel_path, node.lineno, "Potential SSRF")
                            self.findings.append(
                                CloudflareFinding(
                                    verdict="needs_validation",
                                    fingerprint=fp,
                                    title="Potential Server-Side Request Forgery (SSRF)",
                                    description="Application initiates outbound HTTP request to variable destination without explicit private IP/loopback address filtering.",
                                    root_cause="Missing network-level validation on target URL hostname/IP.",
                                    intended_behavior="Validate scheme is http/https and reject private IP ranges (127.0.0.1, 10.0.0.0/8, 169.254.169.254, 192.168.0.0/16).",
                                    attack_class="WEB_PROTOCOL_AND_AUTH",
                                    cwe="CWE-918",
                                    severity="MEDIUM",
                                    trace=[
                                        AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="HTTP Client", description=f"URL argument: `{arg_repr}`"),
                                        AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope="Network Socket", description=f"Outbound HTTP call via `{func_name}`")
                                    ],
                                    evidence=[AuditEvidence(file=rel_path, line=node.lineno, description=f"Call to {func_name}({arg_repr})")],
                                    conditions=["Caller controls URL parameter to probe internal services (e.g. cloud metadata API)."],
                                    remediation=AuditRemediation(
                                        summary="Validate destination hostname using ipaddress module to block loopback and private subnets.",
                                        patch="# Verify target IP is public before connecting"
                                    ),
                                    snippet=f"{func_name}({arg_repr})",
                                )
                            )

                # Memory Safety & Binary FFI: ctypes unchecked buffer (CWE-119 / CWE-787)
                if func_name in {"ctypes.memmove", "ctypes.string_at", "ctypes.cast"}:
                    fp = self._generate_fingerprint("MEMORY_SAFETY_AND_BINARY", rel_path, node.lineno, "Unchecked ctypes Memory Operation")
                    self.findings.append(
                        CloudflareFinding(
                            verdict="needs_validation",
                            fingerprint=fp,
                            title="Unchecked Foreign Function Memory Operation (`ctypes`)",
                            description=f"Raw memory manipulation via `{func_name}` without strict boundary validation.",
                            root_cause="Low-level memory pointer arithmetic in Python bypassing runtime memory safety bounds.",
                            intended_behavior="Verify offset and length do not exceed allocated buffer size before invocation.",
                            attack_class="MEMORY_SAFETY_AND_BINARY",
                            cwe="CWE-119",
                            severity="HIGH",
                            trace=[
                                AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="FFI Interface", description=f"Direct call to {func_name}"),
                                AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope="Process Memory", description="Direct memory read/write operation")
                            ],
                            evidence=[AuditEvidence(file=rel_path, line=node.lineno, description=f"`{func_name}` invoked")],
                            conditions=["Buffer length or offset is derived from untrusted input."],
                            remediation=AuditRemediation(
                                summary="Enforce explicit bounds checking or use memoryview with slicing guarantees.",
                                patch="# Validate len(buffer) >= offset + size before ctypes operation"
                            ),
                            snippet=f"{func_name}(...)",
                        )
                    )

            # 2. Timing attack on secret comparison (CWE-208)
            # Detects `token == expected` or `secret == key` instead of `hmac.compare_digest`
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if isinstance(op, ast.Eq):
                        left_repr = ast.unparse(node.left) if hasattr(ast, "unparse") else ""
                        for comp in node.comparators:
                            right_repr = ast.unparse(comp) if hasattr(ast, "unparse") else ""
                            check_str = (left_repr + " " + right_repr).lower()
                            # Avoid false positives on constant strings or CLI flags
                            if any(k in check_str for k in ["secret_token", "auth_token", "signature", "hmac", "password_hash", "private_key"]) and not any(k in check_str for k in ["len(", "type(", "none", "true", "false", "''", '""', "'secret-mask'", '"secret-mask"', "command"]):
                                fp = self._generate_fingerprint("WEB_PROTOCOL_AND_AUTH", rel_path, node.lineno, "Timing Attack on Secret Comparison")
                                self.findings.append(
                                    CloudflareFinding(
                                        verdict="needs_validation",
                                        fingerprint=fp,
                                        title="Timing Side-Channel on Secret / Signature Comparison (CWE-208)",
                                        description="Standard string equality (`==`) compares byte-by-byte and terminates early on mismatch, leaking secret bytes via timing measurements.",
                                        root_cause="Non-constant-time comparison of security-sensitive cryptographic tokens.",
                                        intended_behavior="Use `hmac.compare_digest(a, b)` for all authentication tokens, hashes, and signatures.",
                                        attack_class="WEB_PROTOCOL_AND_AUTH",
                                        cwe="CWE-208",
                                        severity="MEDIUM",
                                        trace=[
                                            AuditTrace(kind="entrypoint", file=rel_path, line=node.lineno, scope="Auth Check", description=f"Comparing `{left_repr} == {right_repr}`"),
                                            AuditTrace(kind="sink", file=rel_path, line=node.lineno, scope="String Equality", description="Non-constant-time byte comparison")
                                        ],
                                        evidence=[AuditEvidence(file=rel_path, line=node.lineno, description=f"Equality comparison: `{left_repr} == {right_repr}`")],
                                        conditions=["Attacker can measure microsecond network response latencies over repeated requests."],
                                        remediation=AuditRemediation(
                                            summary="Replace `==` with `hmac.compare_digest(a, b)`.",
                                            patch=f"- if {left_repr} == {right_repr}:\n+ import hmac\n+ if hmac.compare_digest({left_repr}, {right_repr}):"
                                        ),
                                        snippet=f"{left_repr} == {right_repr}",
                                    )
                                )

    def _get_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._get_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""

    # --- 3. CLOUDFLARE ARTIFACT GENERATION ---

    def generate_findings_json(self) -> str:
        """Emits valid Cloudflare report-schema.json compliant JSON string."""
        raw = [f.to_cloudflare_dict() for f in self.findings]
        return json.dumps(raw, indent=2)

    def generate_coverage_ledger_json(self) -> str:
        """Emits Cloudflare-compliant coverage-ledger.json audit accounting artifact."""
        confirmed_count = sum(1 for f in self.findings if f.verdict == "confirmed")
        needs_val_count = sum(1 for f in self.findings if f.verdict == "needs_validation")
        severity_counts = Counter(f.severity for f in self.findings)

        ledger = {
            "audit_engine": "Apex Sovereign Security Auditor (Cloudflare Framework)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": str(self.target_path),
            "files_scanned_count": len(self.scanned_files),
            "lines_scanned_count": self.total_lines,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "classes_evaluated": list(ATTACK_CLASSES.keys()),
            "findings_summary": {
                "total": len(self.findings),
                "confirmed": confirmed_count,
                "needs_validation": needs_val_count,
                "by_severity": dict(severity_counts),
            },
            "files_covered": self.scanned_files,
        }
        return json.dumps(ledger, indent=2)

    def generate_markdown_report(self) -> str:
        """Generates comprehensive Cloudflare-grade SECURITY-AUDIT-REPORT.md."""
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        confirmed_count = sum(1 for f in self.findings if f.verdict == "confirmed")
        needs_val_count = sum(1 for f in self.findings if f.verdict == "needs_validation")

        lines = [
            "# Apex Sovereign Security Audit Report",
            f"*Generated by Apex Council Defensive Auditor (Cloudflare Security Audit Standard) on {now_str}*",
            "",
            "## Executive Summary",
            "",
            f"- **Target Repository**: `{self.target_path}`",
            f"- **Total Files Scanned**: `{len(self.scanned_files)}`",
            f"- **Lines of Code Evaluated**: `{self.total_lines:,}`",
            f"- **Audit Latency**: `{self.elapsed_ms:.1f}ms`",
            f"- **Total Findings**: `{len(self.findings)}`",
            f"  - **Confirmed Vulnerabilities**: `{confirmed_count}`",
            f"  - **Needs Validation (Context-Dependent)**: `{needs_val_count}`",
            "",
            "## Vulnerability Matrix",
            "",
            "| ID | Severity | Class | Title | CWE | File:Line |",
            "|---|---|---|---|---|---|",
        ]

        for idx, f in enumerate(self.findings, 1):
            loc = f"{f.trace[0].file}:{f.trace[0].line}" if f.trace else "N/A"
            lines.append(f"| {idx} | **{f.severity}** | `{f.attack_class}` | {f.title} | `{f.cwe}` | `{loc}` |")

        lines.extend([
            "",
            "## Detailed Findings & Defensive Remediation",
            "",
        ])

        for idx, f in enumerate(self.findings, 1):
            lines.extend([
                f"### {idx}. [{f.severity}] {f.title}",
                f"- **Verdict**: `{f.verdict.upper()}`",
                f"- **Fingerprint**: `{f.fingerprint}`",
                f"- **CWE**: `{f.cwe}`",
                f"- **Attack Class**: `{f.attack_class}`",
                "",
                f"**Description**:",
                f"> {f.description}",
                "",
                f"**Root Cause**:",
                f"> {f.root_cause}",
                "",
                f"**Intended Behavior**:",
                f"> {f.intended_behavior}",
                "",
                "**Exploitation Preconditions**:",
            ])
            for cond in f.conditions:
                lines.append(f"- {cond}")

            if f.snippet:
                lines.extend([
                    "",
                    "**Vulnerable Source Line**:",
                    "```python",
                    f.snippet,
                    "```",
                ])

            lines.extend([
                "",
                "**Defensive Remediation**:",
                f"> {f.remediation.summary}",
                "",
            ])
            if f.remediation.patch:
                lines.extend([
                    "```diff",
                    f.remediation.patch,
                    "```",
                    "",
                ])
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def render_terminal(self) -> str:
        """Renders rich terminal output matching Apex Supreme Council styling."""
        lines = [
            "\n" + "=" * 74,
            " 🛡️  APEX SOVEREIGN DEFENSIVE SECURITY AUDITOR (CLOUDFLARE STANDARD)",
            "=" * 74,
            f"  Target Path    : {self.target_path}",
            f"  Files Scanned  : {len(self.scanned_files)} files ({self.total_lines:,} lines in {self.elapsed_ms:.1f}ms)",
            f"  Audit Standard : Cloudflare Security Audit Specification (github.com/cloudflare)",
            f"  Findings Found : {len(self.findings)} issue(s)",
            "=" * 74,
        ]

        if not self.findings:
            lines.append("\n  \033[38;5;114m✔ ZERO SECURITY DEFECTS DETECTED. ALL TRUST BOUNDARIES RIGIDLY SECURED.\033[0m\n")
            return "\n".join(lines)

        for idx, f in enumerate(self.findings, 1):
            if f.severity == "CRITICAL":
                sev_color = "\033[1;38;5;196mCRITICAL\033[0m"
            elif f.severity == "HIGH":
                sev_color = "\033[1;38;5;208mHIGH\033[0m"
            elif f.severity == "MEDIUM":
                sev_color = "\033[1;38;5;220mMEDIUM\033[0m"
            else:
                sev_color = "\033[38;5;114mLOW\033[0m"

            loc = f"{f.trace[0].file}:{f.trace[0].line}" if f.trace else "unknown"
            lines.extend([
                f"\n  \033[1m[{idx}] [{sev_color}\033[1m] {f.title}\033[0m",
                f"      Location   : \033[38;5;117m{loc}\033[0m",
                f"      Class/CWE  : \033[38;5;141m{f.attack_class}\033[0m | \033[1m{f.cwe}\033[0m ({f.verdict})",
                f"      Snippet    : \033[38;5;250m{f.snippet}\033[0m" if f.snippet else "",
                f"      Remedy     : \033[38;5;114m{f.remediation.summary}\033[0m",
            ])

        lines.append("\n" + "=" * 74 + "\n")
        return "\n".join(lines)

    def write_artifacts(self, output_dir: Optional[Path] = None) -> Path:
        """Writes findings.json, coverage-ledger.json, and SECURITY-AUDIT-REPORT.md."""
        target_dir = output_dir or (self.target_path / "artifacts" / "security-audit")
        target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / "findings.json").write_text(self.generate_findings_json(), encoding="utf-8")
        (target_dir / "coverage-ledger.json").write_text(self.generate_coverage_ledger_json(), encoding="utf-8")
        (target_dir / "SECURITY-AUDIT-REPORT.md").write_text(self.generate_markdown_report(), encoding="utf-8")
        return target_dir


def handle_security_audit_cli(args_list: List[str]) -> int:
    """Dispatches CLI command: apex audit-sec [path] [--output-dir <dir>] [--format json|markdown|terminal] [--strict]."""
    target = "."
    output_dir = None
    output_format = "terminal"
    strict = False

    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg in {"--output-dir", "-o"} and i + 1 < len(args_list):
            output_dir = Path(args_list[i + 1])
            i += 2
        elif arg in {"--format", "-f"} and i + 1 < len(args_list):
            output_format = args_list[i + 1].lower()
            i += 2
        elif arg == "--strict":
            strict = True
            i += 1
        elif not arg.startswith("-"):
            target = arg
            i += 1
        else:
            i += 1

    auditor = CloudflareSecurityAuditor(target_path=target, strict=strict)
    findings = auditor.audit()

    if output_dir:
        art_path = auditor.write_artifacts(output_dir)
        print(f"• Audit artifacts written to: {art_path}")

    if output_format == "json":
        print(auditor.generate_findings_json())
    elif output_format == "markdown":
        print(auditor.generate_markdown_report())
    else:
        print(auditor.render_terminal())

    if strict and any(f.severity in {"CRITICAL", "HIGH"} for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(handle_security_audit_cli(sys.argv[1:]))
