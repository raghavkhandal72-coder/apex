import os
import tempfile
import unittest
from pathlib import Path

from apex_council.security.ast_shield import ASTBombDetected, ASTShield
from apex_council.security.integrity import CodeIntegritySigner
from apex_council.security.jail import FilesystemJail, SecurityJailBreach
from apex_council.security.sandbox import HermeticExecutionSandbox, get_hermetic_environment


class TestMilitaryGradeSecurity(unittest.TestCase):
    def test_hermetic_sandbox_scrubs_env_secrets(self):
        # Set fake sensitive environment variables
        os.environ["AWS_SECRET_ACCESS_KEY"] = "super-secret-aws-key"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-secret"
        os.environ["OPENAI_API_KEY"] = "sk-openai-secret"
        os.environ["DATABASE_PASSWORD"] = "db_pass_123"

        clean_env = get_hermetic_environment()

        # Verify completely stripped
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", clean_env)
        self.assertNotIn("ANTHROPIC_API_KEY", clean_env)
        self.assertNotIn("OPENAI_API_KEY", clean_env)
        self.assertNotIn("DATABASE_PASSWORD", clean_env)

        # Run code inside the sandbox checking if it can access the secret
        probe_code = """
import os
assert "AWS_SECRET_ACCESS_KEY" not in os.environ, "Leak: AWS key exposed!"
assert "ANTHROPIC_API_KEY" not in os.environ, "Leak: Anthropic key exposed!"
"""
        passed, _, output = HermeticExecutionSandbox.execute_isolated(probe_code)
        self.assertTrue(passed, f"Sandbox failed leak probe: {output}")

    def test_filesystem_jail_blocks_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir).resolve()

            # Normal path passes
            safe_p = FilesystemJail.resolve_safe_path(base, "sub/file.txt")
            self.assertTrue(safe_p.is_relative_to(base))

            # Traversal attempt ../../ fails with SecurityJailBreach
            with self.assertRaises(SecurityJailBreach):
                FilesystemJail.resolve_safe_path(base, "../../../etc/passwd")

            # Null-byte attempt fails
            with self.assertRaises(SecurityJailBreach):
                FilesystemJail.resolve_safe_path(base, "file.txt\0.exe")

    def test_code_integrity_signing_and_tamper_detection(self):
        original_code = "def secure_function():\n    return 42"
        signed = CodeIntegritySigner.sign_code(original_code)

        # Verified clean
        valid, msg = CodeIntegritySigner.verify_signature(signed)
        self.assertTrue(valid)
        self.assertIn("verified", msg.lower())

        # Malicious modification: attacker alters 42 to 999
        tampered = signed.replace("42", "999")
        valid_tampered, err = CodeIntegritySigner.verify_signature(tampered)
        self.assertFalse(valid_tampered)
        self.assertIn("Tampered", err)

    def test_ast_shield_recursion_protection(self):
        # Safe code passes
        safe_code = "a = 1 + 2 * 3"
        self.assertTrue(ASTShield.inspect_ast_safety(safe_code))

        # Malicious AST with excessive call depth (> 200 nested calls)
        deep_expr = ("f(" * 220) + "1" + (")" * 220)
        with self.assertRaises(ASTBombDetected):
            ASTShield.inspect_ast_safety(deep_expr)

    def test_pep578_audit_hook_blocks_subprocess(self):
        hostile_code = """
import subprocess
subprocess.Popen(["echo", "exploit"])
"""
        passed, _, output = HermeticExecutionSandbox.execute_isolated(hostile_code)
        self.assertFalse(passed)
        self.assertIn("APEX-PEP578-BLOCK", output)
        self.assertIn("Subprocess execution", output)

    def test_pep578_audit_hook_blocks_network_socket(self):
        hostile_code = """
import socket
s = socket.socket()
s.connect(("127.0.0.1", 80))
"""
        passed, _, output = HermeticExecutionSandbox.execute_isolated(hostile_code)
        self.assertFalse(passed)
        self.assertIn("APEX-PEP578-BLOCK", output)
        self.assertIn("Network exfiltration", output)

    def test_pep578_audit_hook_blocks_unauthorized_write(self):
        hostile_code = """
with open("/root_unauthorized_test_file.txt", "w") as f:
    f.write("exploit")
"""
        passed, _, output = HermeticExecutionSandbox.execute_isolated(hostile_code)
        self.assertFalse(passed)
        self.assertIn("APEX-PEP578-BLOCK", output)
        self.assertIn("Unauthorized file write", output)


if __name__ == "__main__":
    unittest.main()
