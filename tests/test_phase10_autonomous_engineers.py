import unittest

from apex_council.swarm.specialists.appsec_engineer import AppSecPenetrationTester
from apex_council.swarm.specialists.chaos_engineer import ChaosResilienceEngineer
from apex_council.swarm.specialists.codebase_modernizer import CodebaseModernizer
from apex_council.swarm.specialists.database_architect import DatabaseArchitect
from apex_council.swarm.specialists.performance_engineer import PerformanceOptimizer
from apex_council.swarm.specialists.release_captain import ReleaseCaptain


class TestPhase10AutonomousEngineers(unittest.TestCase):
    def test_performance_optimizer_detects_antipatterns(self) -> None:
        code = """
def aggregate_logs(logs):
    result = ""
    for entry in logs:
        result += entry  # In-loop string concat
        for sub in logs: # Nested O(N^2) loop
            pass
    return result
"""
        report = PerformanceOptimizer.profile_and_optimize(code)
        self.assertGreater(len(report.antipatterns_detected), 0)
        categories = {a.category for a in report.antipatterns_detected}
        self.assertIn("LOOP_STRING_CONCAT", categories)
        self.assertIn("NESTED_LOOP_O_N2", categories)
        self.assertGreater(report.peak_memory_bytes, 0)

    def test_chaos_resilience_fault_injection(self) -> None:
        resilient_code = """
def robust_read_write(filename, content):
    try:
        with open(filename, "w") as f:
            f.write(content)
        return True
    except OSError:
        return False
"""
        report = ChaosResilienceEngineer.run_chaos_experiments(resilient_code)
        self.assertEqual(report.total_experiments, 4)
        self.assertGreaterEqual(report.resilience_score, 75.0)
        self.assertTrue(report.is_production_ready)

    def test_appsec_taint_propagation_and_remediation(self) -> None:
        vuln_code = """
import os
import sys

raw_input = sys.argv[1]
cmd = "ls " + raw_input
os.system(cmd)  # Command injection!
data = eval("{'key': 123}")  # Dangerous eval!
"""
        report = AppSecPenetrationTester.audit_and_remediate(vuln_code)
        self.assertFalse(report.is_airtight)
        self.assertGreater(len(report.taint_flows), 0)
        self.assertTrue(any(v.category == "COMMAND_INJECTION" for v in report.vulnerabilities))
        self.assertTrue(any(v.category == "CODE_EXECUTION" for v in report.vulnerabilities))

        # Check automated remediation
        self.assertIn("ast.literal_eval", report.remediated_code)

    def test_database_architect_n_plus_one_and_indexes(self) -> None:
        db_code = """
import sqlite3

def fetch_details(user_ids):
    conn = sqlite3.connect("app.db")
    results = []
    for uid in user_ids:
        # N+1 query inside loop
        cur = conn.execute("SELECT * FROM orders WHERE user_id = ?", (uid,))
        results.extend(cur.fetchall())
    return results
"""
        report = DatabaseArchitect.analyze_and_tune(db_code)
        self.assertGreater(len(report.antipatterns), 0)
        categories = {a.category for a in report.antipatterns}
        self.assertIn("N_PLUS_ONE_QUERY", categories)
        self.assertIn("MISSING_WAL_MODE", categories)
        self.assertGreater(len(report.recommended_indexes), 0)
        self.assertTrue(any("idx_records_user_id" in idx for idx in report.recommended_indexes))

    def test_codebase_modernizer_pathlib_and_pep604(self) -> None:
        legacy_code = """
import os
from typing import Optional, Union

def resolve_path(base: str, leaf: Optional[str]) -> Union[str, int]:
    return os.path.join(base, leaf)
"""
        report = CodebaseModernizer.modernize_code(legacy_code)
        self.assertTrue(report.is_fully_modernized)
        self.assertGreater(len(report.transformations_applied), 0)
        # Verify Path / division operator and PEP 604 pipe union
        self.assertIn("Path", report.modernized_code)
        self.assertIn("|", report.modernized_code)
        self.assertNotIn("os.path.join", report.modernized_code)

    def test_release_captain_semver_and_changelog(self) -> None:
        base_api = """
def deploy(app_name, environment):
    return True
"""
        breaking_api = """
def deploy(app_name, environment, cluster_id):  # Added required argument -> BREAKING!
    return True
"""
        report = ReleaseCaptain.evaluate_release(base_api, breaking_api, current_version="1.0.0")
        self.assertTrue(report.is_breaking)
        self.assertEqual(report.bump_type, "MAJOR")
        self.assertEqual(report.next_version, "2.0.0")
        self.assertIn("Breaking Changes", report.changelog_markdown)
        self.assertEqual(len(report.release_signature), 128)  # HMAC-SHA512 hex string


if __name__ == "__main__":
    unittest.main()
