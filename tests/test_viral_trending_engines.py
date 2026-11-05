#!/usr/bin/env python3
"""
Unit Test Suite for Trending GitHub Innovation Engines
Inspired by NVIDIA/auto-ontology, github/spec-kit, max-sixty/worktrunk, & garrytan/gstack
100% Pure Python Standard Library | Zero Dependencies
"""

import os
import pathlib
import tempfile
import unittest

from apex_council.ontology.code_ontology import CodeOntologyEngine
from apex_council.spec.sdd_engine import SDDEngine, Requirement, SystemSpec
from apex_council.git_engine.worktrunk import WorktrunkEngine
from apex_council.swarm.executive_stack import ExecutiveStackOrchestrator


class TestViralTrendingEnginesSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="apex_viral_test_")
        self.workspace = pathlib.Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_code_ontology_layer_inference_and_violations(self) -> None:
        # Code where UI directly calls SQL Database repository without service layer
        ui_code = """
class UserViewController:
    def handle_click(self):
        # Direct call to database repository!
        UserRepository.delete_record(42)
"""
        db_code = """
class UserRepository:
    def delete_record(self, record_id: int):
        pass
"""
        engine = CodeOntologyEngine()
        engine.index_source("ui/controller.py", ui_code)
        engine.index_source("database/repo.py", db_code)

        # Check layer inference
        self.assertEqual(engine.entities["controller.UserViewController"].layer, "presentation")
        self.assertEqual(engine.entities["repo.UserRepository"].layer, "data_access")

        # Invariant check: Clean Architecture violation must be caught
        violations = engine.check_invariants()
        self.assertTrue(any(v.rule_id == "ARCH-001" for v in violations))

    def test_code_ontology_transitive_impact_blast_radius(self) -> None:
        code = """
def root_helper():
    return 42

def service_a():
    return root_helper()

def service_b():
    return root_helper()

def controller_c():
    return service_a()
"""
        engine = CodeOntologyEngine()
        engine.index_source("app/services.py", code)

        impact = engine.explain_impact("services.root_helper")
        self.assertGreaterEqual(impact["transitive_impact_count"], 2)
        self.assertIn("services.service_a", impact["impacted_entities"])
        self.assertIn("services.service_b", impact["impacted_entities"])

    def test_sdd_engine_spec_parsing_and_contract_test_generation(self) -> None:
        spec_text = """
# Spec: MathEngine
## Description
Core mathematical verification specification.

### REQ-001: Integer Multiplication
- Target: `multiply`
- Pre: `a >= 0 and b >= 0`
- Post: `result == a * b`
- Input: `{"a": 6, "b": 7}`
- Output: `42`

### REQ-002: Zero Division Guard
- Target: `divide`
- Input: `{"a": 10, "b": 0}`
- Raises: `ZeroDivisionError`
"""
        spec = SDDEngine.parse_spec_text(spec_text)
        self.assertEqual(spec.name, "MathEngine")
        self.assertEqual(len(spec.requirements), 2)
        self.assertEqual(spec.requirements[0].req_id, "REQ-001")
        self.assertEqual(spec.requirements[1].expected_exception, "ZeroDivisionError")

        # Test generation
        suite_code = SDDEngine.generate_contract_test_suite(spec, "math_module")
        self.assertIn("def test_req_001_multiply(self):", suite_code)
        self.assertIn("self.assertEqual(result, 42)", suite_code)
        self.assertIn("with self.assertRaises(ZeroDivisionError):", suite_code)

    def test_sdd_engine_validate_compliance(self) -> None:
        # Create target implementation module
        mod_code = """
def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a // b
"""
        mod_file = self.workspace / "math_module.py"
        mod_file.write_text(mod_code, encoding="utf-8")

        spec = SystemSpec(
            name="MathModule",
            version="1.0.0",
            description="Testing compliance",
            requirements=[
                Requirement(
                    req_id="REQ-001",
                    title="Multiply positive numbers",
                    target_function="multiply",
                    preconditions=[],
                    postconditions=[],
                    sample_inputs={"a": 3, "b": 4},
                    expected_output=12,
                ),
                Requirement(
                    req_id="REQ-002",
                    title="Divide by zero raises error",
                    target_function="divide",
                    preconditions=[],
                    postconditions=[],
                    sample_inputs={"a": 10, "b": 0},
                    expected_output=None,
                    expected_exception="ZeroDivisionError",
                ),
            ],
            global_invariants=[],
        )

        report = SDDEngine.validate_spec_compliance(spec, mod_file)
        self.assertEqual(report.compliance_score, 1.0)
        self.assertEqual(report.passed_requirements, 2)
        self.assertEqual(report.failed_requirements, 0)

    def test_executive_stack_c_suite_review(self) -> None:
        proposal_title = "feat: Add high-throughput memory cache"
        proposal_desc = "Adds LRU cache with TTL support and full unit test coverage. Non-breaking."
        code_diff = """
+ class LRUCache:
+     def __init__(self, capacity: int):
+         self.capacity = capacity
+     def test_cache_hit(self):
+         pass
"""
        consensus = ExecutiveStackOrchestrator.evaluate_proposal(
            proposal_title, proposal_desc, code_diff
        )
        self.assertTrue(consensus.unanimous_approval)
        self.assertGreaterEqual(consensus.aggregate_score, 8.0)
        self.assertEqual(consensus.suggested_semver, "MINOR")
        self.assertEqual(len(consensus.verdicts), 4)

        # Test rejection on dangerous pattern
        dangerous_diff = """
+ def run_user_input(code):
+     eval(code)
"""
        rejected = ExecutiveStackOrchestrator.evaluate_proposal(
            "fix: Execute user query", "Executes input dynamically", dangerous_diff
        )
        self.assertFalse(rejected.unanimous_approval)
        arch_verdict = next(v for v in rejected.verdicts if "Architect" in v.role)
        self.assertFalse(arch_verdict.approved)
        self.assertIn("Security rejection", arch_verdict.action_items[0])

    def test_worktrunk_allocate_and_prune(self) -> None:
        import subprocess
        # Initialize a test git repo
        subprocess.run(["git", "init"], cwd=str(self.workspace), capture_output=True, check=True)
        subprocess.run(["git", "config", "safe.directory", "*"], cwd=str(self.workspace), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(self.workspace), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@apex.local"], cwd=str(self.workspace), capture_output=True)
        # Create initial commit
        init_file = self.workspace / "README.md"
        init_file.write_text("# Test Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=str(self.workspace), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(self.workspace), capture_output=True)

        trunk = WorktrunkEngine(self.workspace)
        session = trunk.allocate_worktree("agent_architect")
        self.assertTrue(session.worktree_path.exists())
        self.assertEqual(len(trunk.list_active_worktrees()), 1)

        # Prune worktree
        trunk.prune_worktree("agent_architect")
        self.assertFalse(session.worktree_path.exists())
        self.assertEqual(len(trunk.list_active_worktrees()), 0)


if __name__ == "__main__":
    unittest.main()
