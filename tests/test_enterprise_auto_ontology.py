#!/usr/bin/env python3
"""
Unit Test Suite for Enterprise Auto-Ontology & HR Workforce Analytics
Inspired by NVIDIA/auto-ontology
100% Pure Python Standard Library | Zero Dependencies
"""

import unittest
from apex_council.ontology.enterprise_auto_ontology import EnterpriseAutoOntology


class TestEnterpriseAutoOntologySuite(unittest.TestCase):
    def setUp(self) -> None:
        self.ontology = EnterpriseAutoOntology()

        # Schema: Enterprise HR Organization
        self.ontology.register_table(
            "employees",
            [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
                {"name": "email", "type": "TEXT"},
                {"name": "salary", "type": "REAL"},
                {"name": "department_id", "type": "INTEGER"},
                {"name": "manager_id", "type": "INTEGER"},
                {"name": "is_active", "type": "INTEGER"},
            ],
            description="Active and former company employees",
        )

        self.ontology.register_table(
            "departments",
            [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
                {"name": "cost_center", "type": "TEXT"},
            ],
            description="Company organizational divisions",
        )

        self.ontology.register_table(
            "performance_reviews",
            [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "employee_id", "type": "INTEGER"},
                {"name": "rating", "type": "INTEGER"},
                {"name": "review_date", "type": "DATE"},
            ],
            description="Quarterly performance review records",
        )

    def test_table_registration_and_pii_tagging(self) -> None:
        emp = self.ontology.tables["employees"]
        self.assertEqual(emp.business_term, "Employees")
        self.assertTrue(emp.columns["salary"].is_pii)
        self.assertEqual(emp.columns["salary"].pii_category, "COMPENSATION")
        self.assertTrue(emp.columns["email"].is_pii)
        self.assertEqual(emp.columns["email"].pii_category, "CONTACT")
        self.assertFalse(emp.columns["name"].is_pii)

    def test_semantic_foreign_key_inference_and_hierarchy(self) -> None:
        fks = self.ontology.infer_semantic_foreign_keys()
        self.assertGreaterEqual(len(fks), 3)

        # 1. department_id -> departments.id
        dept_fk = next((fk for fk in fks if fk.source_column == "department_id"), None)
        self.assertIsNotNone(dept_fk)
        self.assertEqual(dept_fk.target_table, "departments")
        self.assertEqual(dept_fk.target_column, "id")

        # 2. manager_id -> employees.id (Self-hierarchy)
        mgr_fk = next((fk for fk in fks if fk.source_column == "manager_id"), None)
        self.assertIsNotNone(mgr_fk)
        self.assertEqual(mgr_fk.target_table, "employees")
        self.assertEqual(mgr_fk.target_column, "id")

        # 3. employee_id -> employees.id
        perf_fk = next((fk for fk in fks if fk.source_table == "performance_reviews"), None)
        self.assertIsNotNone(perf_fk)
        self.assertEqual(perf_fk.target_table, "employees")

    def test_shortest_join_path_discovery_bfs(self) -> None:
        self.ontology.infer_semantic_foreign_keys()

        # Direct join: performance_reviews -> employees
        path1 = self.ontology.find_join_path("performance_reviews", "employees")
        self.assertEqual(len(path1), 1)
        self.assertEqual(path1[0][0], "performance_reviews")
        self.assertEqual(path1[0][2], "employees")

        # Multi-hop join: performance_reviews -> employees -> departments
        path2 = self.ontology.find_join_path("performance_reviews", "departments")
        self.assertEqual(len(path2), 2)
        self.assertEqual(path2[0][2], "employees")
        self.assertEqual(path2[1][2], "departments")

    def test_nl_query_plan_and_pii_role_redaction(self) -> None:
        self.ontology.infer_semantic_foreign_keys()

        # Query asking for employee salary in department
        question = "Show employee name and salary in active departments"

        # 1. Non-executive analyst: salary must be redacted!
        plan_analyst = self.ontology.generate_nl_query_plan(question, user_role="HR_ANALYST")
        self.assertIn("salary_masked", plan_analyst.sql)
        self.assertFalse(plan_analyst.governance_cleared)
        self.assertGreaterEqual(len(plan_analyst.join_clauses), 1)
        self.assertTrue("employees" in plan_analyst.sql and "departments" in plan_analyst.sql)

        # 2. Executive: salary clear text permitted
        plan_exec = self.ontology.generate_nl_query_plan(question, user_role="HR_EXECUTIVE")
        self.assertIn("employees.salary", plan_exec.sql)
        self.assertNotIn("REDACTED", plan_exec.sql)
        self.assertTrue(plan_exec.governance_cleared)

    def test_hr_workforce_analytics_audit(self) -> None:
        self.ontology.infer_semantic_foreign_keys()
        audit = self.ontology.hr_workforce_analytics_audit()
        self.assertTrue(audit["hr_schema_ready"])
        self.assertTrue(audit["span_of_control_supported"])
        self.assertGreaterEqual(audit["pii_governed_columns"], 2)
        self.assertGreaterEqual(len(audit["hr_diagnostic_insights"]), 3)


if __name__ == "__main__":
    unittest.main()
