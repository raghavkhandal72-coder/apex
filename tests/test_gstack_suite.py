#!/usr/bin/env python3
"""
Unit Test Suite for Garry Tan gstack Virtual Engineering Team
Inspired by garrytan/gstack (23 Opinionated Engineering Tools)
100% Pure Python Standard Library | Zero Dependencies
"""

import unittest
from apex_council.gstack.office_hours import GarryTanOfficeHoursEngine
from apex_council.gstack.cso_audit import ChiefSecurityOfficerEngine
from apex_council.gstack.pre_landing_review import PreLandingReviewEngine
from apex_council.gstack.ship_engine import ReleaseShippingEngine
from apex_council.gstack.gstack_orchestrator import GStackOrchestrator


class TestGStackSuite(unittest.TestCase):

    def test_office_hours_planning(self):
        plan = GarryTanOfficeHoursEngine.conduct_session("Fix critical memory leak in background worker that causes crashes")
        self.assertIn("PAINKILLER", plan.painkiller_verdict)
        self.assertGreater(len(plan.scope_cuts), 0)
        self.assertIn("Design Doc", plan.design_doc_markdown)

    def test_cso_owasp_stride_audit_catches_flaws(self):
        dangerous_code = """
import os
def run_command(user_input):
    os.system(user_input)
    eval(user_input)
"""
        report = ChiefSecurityOfficerEngine.audit_code(dangerous_code, "api.py")
        self.assertFalse(report.passed)
        self.assertLess(report.security_score, 8.0)
        self.assertTrue(any(f.stride_category == "Elevation of Privilege" for f in report.findings))
        self.assertTrue(any("eval" in f.description for f in report.findings))

    def test_cso_owasp_stride_audit_rewards_clean_code(self):
        clean_code = """
import json
from pathlib import Path

def parse_config(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)
"""
        report = ChiefSecurityOfficerEngine.audit_code(clean_code, "config.py")
        self.assertTrue(report.passed)
        self.assertEqual(report.security_score, 10.0)
        self.assertEqual(len(report.findings), 0)

    def test_pre_landing_review_and_pr_classification(self):
        # Test PR type classifications
        self.assertEqual(PreLandingReviewEngine.classify_pr_type(["README.md", "docs/api.md"]), "docs-only")
        self.assertEqual(PreLandingReviewEngine.classify_pr_type([".github/workflows/ci.yml", "Dockerfile"]), "CI/infra")
        self.assertEqual(PreLandingReviewEngine.classify_pr_type(["scripts/deploy.sh"]), "scripts/tooling")
        self.assertEqual(PreLandingReviewEngine.classify_pr_type(["src/main.py"]), "application")

        # Test pre-landing review checks
        dirty_diff = """
subprocess.run("rm -rf /", shell=True)
# TODO: fix this later
"""
        report = PreLandingReviewEngine.review_diff(["worker.py"], dirty_diff)
        self.assertFalse(report.passed)
        self.assertFalse(report.checklist_status["Shell Injection & Security"])
        self.assertTrue(any("shell=True" in i.message for i in report.issues))
        self.assertTrue(any("TODO" in i.message for i in report.issues))

    def test_release_shipping_engine(self):
        # Minor bump
        receipt = ReleaseShippingEngine.prepare_shipment(
            current_version="v3.0.0",
            commit_messages=["feat: add distributed tracing support", "test: add tracer unittests"],
        )
        self.assertEqual(receipt.version_bump, "MINOR")
        self.assertEqual(receipt.new_version, "v3.1.0")
        self.assertIn("Added", receipt.changelog_snippet)

        # Major bump
        receipt_major = ReleaseShippingEngine.prepare_shipment(
            current_version="v3.1.0",
            commit_messages=["feat!: breaking changes to public API"],
        )
        self.assertEqual(receipt_major.version_bump, "MAJOR")
        self.assertEqual(receipt_major.new_version, "v4.0.0")

    def test_gstack_orchestrator_pipeline(self):
        clean_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = GStackOrchestrator.run_full_pipeline(
            task_concept="Build mathematical arithmetic engine",
            file_paths=["math_engine.py"],
            source_code=clean_code,
        )
        self.assertTrue(result.passed)
        self.assertIsNotNone(result.ship_receipt)
        self.assertEqual(len(result.transcript_speeches), 4)
        # Check that all 4 agents spoke
        joined_speeches = "\n".join(result.transcript_speeches)
        self.assertIn("APEX SUPREME COMMANDER", joined_speeches)
        self.assertIn("SYSTEM ARCHITECT", joined_speeches)
        self.assertIn("SECURITY SENTINEL", joined_speeches)
        self.assertIn("AUTONOMOUS BUG HUNTER", joined_speeches)


if __name__ == "__main__":
    unittest.main()
