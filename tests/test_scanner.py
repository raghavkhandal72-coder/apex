import unittest

from apex_council.security.scanner import (
    ASTTaintTracker,
    ReDoSAnalyzer,
    ShannonEntropyScanner,
    SovereignSecurityScanner,
)


class TestSecurityScannerSuite(unittest.TestCase):
    def test_shannon_entropy_detects_high_entropy_secret(self) -> None:
        raw_code = 'AWS_KEY = "AKIA1234567890ABCDEF"'
        findings = SovereignSecurityScanner.scan_code(raw_code)
        self.assertTrue(any(f.category == "SECRET_LEAK" and "AWS Access Key" in f.description for f in findings))

    def test_shannon_entropy_detects_random_token(self) -> None:
        # High entropy 32-char hex/b64 string
        raw_code = 'TOKEN = "q9Z#vK2$mX8!pL1@wR5^yT3*bN7&"'
        findings = SovereignSecurityScanner.scan_code(raw_code)
        self.assertTrue(any(f.category == "SECRET_LEAK" for f in findings))

    def test_shannon_entropy_ignores_plain_prose(self) -> None:
        raw_code = 'MESSAGE = "This is just a simple documentation sentence for our library."'
        findings = SovereignSecurityScanner.scan_code(raw_code)
        self.assertEqual(len(findings), 0)

    def test_redos_catches_nested_quantifiers(self) -> None:
        code_with_redos = 'import re\npattern = re.compile(r"([a-zA-Z]+)+$")'
        findings = SovereignSecurityScanner.scan_code(code_with_redos)
        self.assertTrue(any(f.category == "REDOS" for f in findings))

    def test_taint_tracker_detects_command_injection(self) -> None:
        vuln_code = """
import os, sys
user_input = sys.argv[1]
cmd = "ls " + user_input
os.system(cmd)
"""
        findings = SovereignSecurityScanner.scan_code(vuln_code)
        taint_findings = [f for f in findings if f.category == "TAINT_FLOW"]
        self.assertGreater(len(taint_findings), 0)
        self.assertIn("os.system", taint_findings[0].description)

    def test_taint_tracker_detects_sql_injection(self) -> None:
        vuln_code = """
import sqlite3
conn = sqlite3.connect(":memory:")
cur = conn.cursor()
user_name = "admin"
cur.execute(f"SELECT * FROM accounts WHERE name = '{user_name}'")
"""
        findings = SovereignSecurityScanner.scan_code(vuln_code)
        sql_findings = [f for f in findings if f.category == "SQL_INJECTION"]
        self.assertGreater(len(sql_findings), 0)
        self.assertIn(".execute", sql_findings[0].description)


if __name__ == "__main__":
    unittest.main()
