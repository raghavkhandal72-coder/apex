import unittest
from pathlib import Path
from apex_council.enterprise.dlp import EnterpriseDLP
from apex_council.enterprise.audit import CryptographicAuditLogger
from apex_council.enterprise.rbac import RBACManager, EnterpriseRole
from apex_council.enterprise.policy import EnterprisePolicyEngine
from apex_council.enterprise.telemetry import EnterpriseTelemetry
import tempfile


class TestEnterpriseSuite(unittest.TestCase):
    def test_dlp_redaction(self):
        dirty_text = "Employee alice@google.com with SSN 000-11-2222 and credit card 4111111111111111"
        res = EnterpriseDLP.sanitize(dirty_text)
        self.assertEqual(res.redactions_count, 3)
        self.assertIn("EMAIL", res.categories_found)
        self.assertIn("SSN", res.categories_found)
        self.assertIn("CREDIT_CARD", res.categories_found)
        self.assertNotIn("alice@google.com", res.clean_text)
        self.assertNotIn("000-11-2222", res.clean_text)

    def test_cryptographic_audit_trail(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            logger = CryptographicAuditLogger(log_path=tmp_path)
            e1 = logger.record_event("ACTION_1", "prompt 1", "code 1", "Gemini", 100.0)
            e2 = logger.record_event("ACTION_2", "prompt 2", "code 2", "Claude", 98.0)

            valid, count, err = logger.verify_integrity()
            self.assertTrue(valid)
            self.assertEqual(count, 2)
            self.assertIsNone(err)

            # Test tamper detection: modify log line 1
            lines = tmp_path.read_text(encoding="utf-8").splitlines()
            tampered_lines = [lines[0].replace("Gemini", "Attacker")] + lines[1:]
            tmp_path.write_text("\n".join(tampered_lines) + "\n", encoding="utf-8")

            valid_tampered, _, err_tampered = logger.verify_integrity()
            self.assertFalse(valid_tampered)
            self.assertIn("Tampered", err_tampered)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_rbac_authorization(self):
        rbac = RBACManager()
        admin_token = "admin-secret-test-token"
        dev_token = "dev-secret-test-token"
        rbac.register_token(admin_token, "admin@corp.com", "tenant-1", EnterpriseRole.ADMIN)
        rbac.register_token(dev_token, "dev@corp.com", "tenant-1", EnterpriseRole.DEVELOPER)

        # Developer can battle, but not redteam or audit-verify
        import os
        os.environ["APEX_AUTH_REQUIRED"] = "true"
        try:
            self.assertTrue(rbac.authorize(admin_token, "redteam"))
            self.assertTrue(rbac.authorize(dev_token, "battle"))
            self.assertFalse(rbac.authorize(dev_token, "redteam"))
        finally:
            os.environ["APEX_AUTH_REQUIRED"] = "false"

    def test_enterprise_policy_engine(self):
        banned_code = """
import pickle
def load_data(x):
    return pickle.loads(x)
"""
        passed, violations = EnterprisePolicyEngine.audit_enterprise_policies(banned_code)
        self.assertFalse(passed)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, "POL-MOD-001")

    def test_telemetry_export(self):
        EnterpriseTelemetry.record_request("test_deliberate", 0.15, "Google Gemini", 2)
        metrics = EnterpriseTelemetry.export_metrics()
        self.assertIn("apex_council_requests_total", metrics)
        self.assertIn("apex_council_model_wins_total", metrics)


if __name__ == "__main__":
    unittest.main()
