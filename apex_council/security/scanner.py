"""AST Taint Tracker, ReDoS Regex Vulnerability Detector, and Shannon Entropy Secret Scanner.
Provides military-grade static application security testing (SAST) with zero external dependencies.
Pure Python standard library implementation.
"""

from __future__ import annotations

import ast
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SecurityFinding:
    category: str  # TAINT_FLOW, REDOS, SECRET_LEAK, SQL_INJECTION
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    file_path: str = ""
    line_number: int = 0
    column_number: int = 0
    snippet: str = ""
    remediation: str = ""


# --- 1. SHANNON ENTROPY & SECRET SCANNER ---

class ShannonEntropyScanner:
    """Calculates Shannon information entropy H = -sum(p * log2(p)) to detect hardcoded secrets and high-entropy keys."""

    KNOWN_PATTERNS = [
        (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID", "CRITICAL"),
        (re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"), "GitHub Personal Access Token", "CRITICAL"),
        (re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"), "Slack API Token", "CRITICAL"),
        (re.compile(r"AIza[0-9A-Za-z\\-_]{35}"), "Google Cloud / Gemini API Key", "CRITICAL"),
        (re.compile(r"sk-[a-zA-Z0-9]{32,64}"), "OpenAI API Key", "CRITICAL"),
        (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"), "Cryptographic Private Key", "CRITICAL"),
        (re.compile(r"ey[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*"), "JWT Web Token", "HIGH"),
    ]

    @staticmethod
    def calculate_entropy(data: str) -> float:
        """Calculates Shannon entropy in bits per symbol."""
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        counts = Counter(data)
        for count in counts.values():
            p_x = count / length
            if p_x > 0:
                entropy += -p_x * math.log2(p_x)
        return entropy

    @classmethod
    def scan_string(cls, text: str, line_no: int = 1, file_path: str = "") -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []

        # 1. Regex Match for Well-Known Patterns
        for pattern, desc, severity in cls.KNOWN_PATTERNS:
            for match in pattern.finditer(text):
                matched_val = match.group(0)
                masked = matched_val[:4] + "*" * (len(matched_val) - 8) + matched_val[-4:] if len(matched_val) > 8 else "***"
                findings.append(
                    SecurityFinding(
                        category="SECRET_LEAK",
                        severity=severity,
                        description=f"Hardcoded {desc} detected: {masked}",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=masked,
                        remediation="Move secret credentials to environment variables or secret vaults.",
                    )
                )

        # 2. Shannon Entropy Threshold Check
        # Check quoted string literals and raw alphanumeric tokens with length >= 12
        quoted = re.findall(r'["\']([^"\']{12,})["\']', text)
        raw_tokens = re.findall(r"[A-Za-z0-9_/\+=-]{16,}", text)
        candidates = set(quoted + raw_tokens)

        for token in candidates:
            # Skip prose containing spaces or newlines
            if " " in token or "\t" in token or "\n" in token:
                continue
            # Skip low variety tokens (e.g. padding like "AAAAAAA...")
            if len(set(token)) < 8:
                continue
            entropy = cls.calculate_entropy(token)
            # High entropy threshold: >= 4.0 bits/char for contiguous tokens indicates high randomness/cryptographic secret
            if entropy >= 4.0:
                # Exclude if already matched known patterns
                if any(f.snippet.startswith(token[:4]) for f in findings):
                    continue
                masked = token[:3] + "*" * (len(token) - 6) + token[-3:] if len(token) > 6 else "***"
                findings.append(
                    SecurityFinding(
                        category="SECRET_LEAK",
                        severity="HIGH",
                        description=f"High Shannon entropy ({entropy:.2f} bits) secret candidate detected",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=masked,
                        remediation="Ensure this high-entropy string is not a secret or private credential.",
                    )
                )

        return findings


# --- 2. REDOS REGEX VULNERABILITY ANALYZER ---

class ReDoSAnalyzer:
    """Detects catastrophic polynomial and exponential backtracking patterns in regular expressions.
    Catches nested quantifiers like (a+)+, (.*)*, and overlapping alternation like (a|a)+.
    """

    # Nested quantifier patterns
    CATASTROPHIC_PATTERNS = [
        (re.compile(r"\([^()]*[+*][^()]*\)[+*{]"), "Nested quantifiers (e.g., (x+)+ or (x*)*) cause exponential backtracking"),
        (re.compile(r"\([^()]*\w+\|[^()]*\w+\)[+*{]"), "Ambiguous alternation with repetition"),
        (re.compile(r"(\.[*+]){2,}"), "Adjacent unbounded wildcards cause catastrophic state explosion"),
        (re.compile(r"\(\.\*\)\+"), "Wildcard repetition `(.*)+` causes polynomial/exponential blowup"),
    ]

    @classmethod
    def analyze_regex(cls, pattern_str: str, line_no: int = 1, file_path: str = "") -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []

        for pat, reason in cls.CATASTROPHIC_PATTERNS:
            if pat.search(pattern_str):
                findings.append(
                    SecurityFinding(
                        category="REDOS",
                        severity="HIGH",
                        description=f"Potential ReDoS Vulnerability in regex: {reason}",
                        file_path=file_path,
                        line_number=line_no,
                        snippet=pattern_str,
                        remediation="Rewrite regular expression with atomic groups, possessive quantifiers, or linear parsing.",
                    )
                )
                break  # avoid multiple warnings per regex

        return findings


# --- 3. AST TAINT TRACKER ---

class ASTTaintTracker(ast.NodeVisitor):
    """Tracks intra-procedural data flow from untrusted sources to dangerous sinks."""

    TAINT_SOURCES = {
        "request.args",
        "request.form",
        "request.json",
        "request.values",
        "request.GET",
        "request.POST",
        "sys.argv",
        "os.environ",
        "input",
        "socket.recv",
    }

    COMMAND_SINKS = {
        "os.system",
        "os.popen",
        "os.spawn",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_output",
        "pty.spawn",
    }

    CODE_SINKS = {"eval", "exec", "compile", "__import__"}

    def __init__(self, file_path: str = "") -> None:
        self.file_path = file_path
        self.tainted_vars: Set[str] = set()
        self.findings: List[SecurityFinding] = []

    def _get_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = self._get_call_name(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        return ""

    def _is_tainted_expr(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name) and node.id in self.tainted_vars:
            return True
        if isinstance(node, ast.Attribute):
            name = self._get_call_name(node)
            if any(name.startswith(src) for src in self.TAINT_SOURCES):
                return True
        if isinstance(node, ast.Subscript):
            return self._is_tainted_expr(node.value)
        if isinstance(node, ast.BinOp):
            return self._is_tainted_expr(node.left) or self._is_tainted_expr(node.right)
        if isinstance(node, ast.JoinedStr):  # f-string
            return any(
                isinstance(v, ast.FormattedValue) and self._is_tainted_expr(v.value)
                for v in node.values
            )
        if isinstance(node, ast.Call):
            name = self._get_call_name(node.func)
            if any(name.startswith(src) for src in self.TAINT_SOURCES):
                return True
            return any(self._is_tainted_expr(arg) for arg in node.args)
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        is_tainted = self._is_tainted_expr(node.value)
        if is_tainted:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.tainted_vars.add(target.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._get_call_name(node.func)

        # 1. Check Command Execution Sinks
        if call_name in self.COMMAND_SINKS:
            for arg in node.args:
                if self._is_tainted_expr(arg):
                    self.findings.append(
                        SecurityFinding(
                            category="TAINT_FLOW",
                            severity="CRITICAL",
                            description=f"Untrusted input reaches shell command execution sink `{call_name}`",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                            snippet=f"{call_name}(...)",
                            remediation="Do not pass untrusted strings to shell execution. Use parameterized argv list with shell=False.",
                        )
                    )

        # 2. Check Code Execution Sinks
        if call_name in self.CODE_SINKS:
            for arg in node.args:
                if self._is_tainted_expr(arg):
                    self.findings.append(
                        SecurityFinding(
                            category="TAINT_FLOW",
                            severity="CRITICAL",
                            description=f"Untrusted input reaches dynamic code evaluation sink `{call_name}`",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                            snippet=f"{call_name}(...)",
                            remediation="Avoid dynamic code execution with untrusted data; use ast.literal_eval or json.loads.",
                        )
                    )

        # 3. Check SQL Formatting Sinks
        if call_name.endswith(".execute") or call_name.endswith(".executemany"):
            if node.args:
                query_arg = node.args[0]
                if isinstance(query_arg, (ast.JoinedStr, ast.BinOp)) or self._is_tainted_expr(query_arg):
                    self.findings.append(
                        SecurityFinding(
                            category="SQL_INJECTION",
                            severity="CRITICAL",
                            description=f"Potentially formatted SQL query in `{call_name}` prone to SQL Injection",
                            file_path=self.file_path,
                            line_number=node.lineno,
                            column_number=node.col_offset,
                            snippet=f"{call_name}(...)",
                            remediation="Use parameterized queries with placeholder placeholders (`?` or `:name`) instead of string formatting.",
                        )
                    )

        # 4. Check ReDoS in re.compile / re.search / re.match
        if call_name.startswith("re.") and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                redos_issues = ReDoSAnalyzer.analyze_regex(
                    first_arg.value,
                    line_no=node.lineno,
                    file_path=self.file_path,
                )
                self.findings.extend(redos_issues)

        self.generic_visit(node)


# --- 4. COMPREHENSIVE SECURITY SCANNER SUITE ---

class SovereignSecurityScanner:
    """Unified static security scanner combining AST Taint, ReDoS, and Shannon Secret Scanning."""

    @classmethod
    def scan_code(cls, source_code: str, file_path: str = "<source>") -> List[SecurityFinding]:
        findings: List[SecurityFinding] = []

        # 1. Line-by-line Secret and Shannon Entropy Scan
        for line_no, line in enumerate(source_code.splitlines(), start=1):
            findings.extend(ShannonEntropyScanner.scan_string(line, line_no=line_no, file_path=file_path))

        # 2. AST-Based Taint and Semantic Analysis
        try:
            tree = ast.parse(source_code)
            tracker = ASTTaintTracker(file_path=file_path)
            tracker.visit(tree)
            findings.extend(tracker.findings)
        except Exception:
            pass

        return findings
