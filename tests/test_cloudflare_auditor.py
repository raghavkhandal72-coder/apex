import json
import tempfile
import unittest
from pathlib import Path

from apex_council.security.cloudflare_auditor import (
    ATTACK_CLASSES,
    CloudflareFinding,
    CloudflareSecurityAuditor,
    handle_security_audit_cli,
)


class TestCloudflareSecurityAuditor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_attack_classes_defined(self):
        self.assertIn("AI_AND_LLM", ATTACK_CLASSES)
        self.assertIn("MEMORY_SAFETY_AND_BINARY", ATTACK_CLASSES)
        self.assertIn("SUPPLY_CHAIN_AND_RELEASE", ATTACK_CLASSES)
        self.assertIn("WEB_PROTOCOL_AND_AUTH", ATTACK_CLASSES)
        self.assertIn("RESOURCE_EXHAUSTION_AND_AVAILABILITY", ATTACK_CLASSES)

    def test_detects_llm_sink_eval(self):
        vulnerable_code = (
            "def handle_ai_task(llm_response):\n"
            "    # Dangerous execution of LLM output\n"
            "    return eval(llm_response)\n"
        )
        test_file = self.dir_path / "ai_service.py"
        test_file.write_text(vulnerable_code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        findings = auditor.audit()

        llm_findings = [f for f in findings if f.attack_class == "AI_AND_LLM"]
        self.assertTrue(len(llm_findings) >= 1)
        finding = llm_findings[0]
        self.assertEqual(finding.severity, "CRITICAL")
        self.assertEqual(finding.cwe, "CWE-95")
        self.assertEqual(finding.verdict, "confirmed")

    def test_detects_hardcoded_aws_secret(self):
        vulnerable_code = (
            "AWS_KEY = 'AKIA1234567890ABCDEF'\n"
            "def connect(): pass\n"
        )
        test_file = self.dir_path / "cloud_config.py"
        test_file.write_text(vulnerable_code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        findings = auditor.audit()

        secret_findings = [f for f in findings if f.cwe == "CWE-798"]
        self.assertTrue(len(secret_findings) >= 1)
        self.assertEqual(secret_findings[0].severity, "CRITICAL")
        self.assertEqual(secret_findings[0].verdict, "confirmed")

    def test_detects_insecure_tempfile_mktemp(self):
        vulnerable_code = (
            "import tempfile\n"
            "def make_scratch():\n"
            "    path = tempfile.mktemp()\n"
            "    return path\n"
        )
        test_file = self.dir_path / "temp_util.py"
        test_file.write_text(vulnerable_code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        findings = auditor.audit()

        temp_findings = [f for f in findings if f.cwe == "CWE-377"]
        self.assertTrue(len(temp_findings) >= 1)
        self.assertEqual(temp_findings[0].attack_class, "DATA_ISOLATION_AND_LIFECYCLE")

    def test_detects_pickle_deserialization(self):
        vulnerable_code = (
            "import pickle\n"
            "def load_user(data):\n"
            "    return pickle.loads(data)\n"
        )
        test_file = self.dir_path / "session.py"
        test_file.write_text(vulnerable_code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        findings = auditor.audit()

        pickle_findings = [f for f in findings if f.cwe == "CWE-502"]
        self.assertTrue(len(pickle_findings) >= 1)
        self.assertEqual(pickle_findings[0].severity, "CRITICAL")

    def test_detects_timing_attack_on_secret(self):
        vulnerable_code = (
            "def verify_auth(user_token, secret_token):\n"
            "    if user_token == secret_token:\n"
            "        return True\n"
            "    return False\n"
        )
        test_file = self.dir_path / "auth.py"
        test_file.write_text(vulnerable_code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        findings = auditor.audit()

        timing_findings = [f for f in findings if f.cwe == "CWE-208"]
        self.assertTrue(len(timing_findings) >= 1)
        self.assertIn("hmac.compare_digest", timing_findings[0].remediation.patch)

    def test_generates_cloudflare_compliant_artifacts(self):
        code = "def foo(): eval(llm_response)\n"
        (self.dir_path / "foo.py").write_text(code, encoding="utf-8")

        auditor = CloudflareSecurityAuditor(target_path=str(self.dir_path))
        auditor.audit()

        # Check findings.json compliance
        findings_json_str = auditor.generate_findings_json()
        findings_data = json.loads(findings_json_str)
        self.assertIsInstance(findings_data, list)
        self.assertTrue(len(findings_data) >= 1)

        f0 = findings_data[0]
        self.assertIn("verdict", f0)
        self.assertIn("fingerprint", f0)
        self.assertIn("title", f0)
        self.assertIn("description", f0)
        self.assertIn("root_cause", f0)
        self.assertIn("intended_behavior", f0)
        self.assertIn("trace", f0)
        self.assertIn("evidence", f0)
        self.assertIn("remediation", f0)

        # Check coverage-ledger.json
        ledger_json_str = auditor.generate_coverage_ledger_json()
        ledger_data = json.loads(ledger_json_str)
        self.assertEqual(ledger_data["audit_engine"], "Apex Sovereign Security Auditor (Cloudflare Framework)")
        self.assertIn("files_scanned_count", ledger_data)
        self.assertIn("findings_summary", ledger_data)

        # Check markdown report
        md_report = auditor.generate_markdown_report()
        self.assertIn("# Apex Sovereign Security Audit Report", md_report)
        self.assertIn("Executive Summary", md_report)

        # Write artifacts
        out_dir = self.dir_path / "audit_output"
        auditor.write_artifacts(output_dir=out_dir)
        self.assertTrue((out_dir / "findings.json").exists())
        self.assertTrue((out_dir / "coverage-ledger.json").exists())
        self.assertTrue((out_dir / "SECURITY-AUDIT-REPORT.md").exists())

    def test_cli_execution(self):
        ret = handle_security_audit_cli([str(self.dir_path), "--format", "json"])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
