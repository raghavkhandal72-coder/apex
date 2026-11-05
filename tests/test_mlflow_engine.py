#!/usr/bin/env python3
"""
Unit Test Suite for MLflow-Native Agent Observability, Tracing, & LLMOps Engine
100% Pure Python Standard Library | Zero Dependencies
"""

import json
import pathlib
import tempfile
import unittest

from apex_council.mlflow_engine.tracer import AgentTracer
from apex_council.mlflow_engine.tracker import MLflowExperimentTracker
from apex_council.mlflow_engine.evaluator import LLMJudgeEvaluator
from apex_council.mlflow_engine.gateway import AIGatewayRouter


class TestMLflowEngineSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="apex_mlflow_test_")
        self.workspace = pathlib.Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_agent_tracer_spans_and_export(self) -> None:
        tracer = AgentTracer("test_swarm_workflow")

        # Root agent span
        with tracer.span("architect.plan", span_type="AGENT", inputs={"task": "Add auth"}) as s1:
            s1.outputs = {"plan": ["step1", "step2"]}

            # Child tool span
            with tracer.span("tool.git_diff", span_type="TOOL", inputs={"file": "auth.py"}) as s2:
                s2.outputs = {"diff_lines": 14}

        self.assertEqual(len(tracer.spans), 2)
        root = tracer.spans[0]
        child = tracer.spans[1]
        self.assertEqual(child.parent_id, root.span_id)
        self.assertEqual(root.status, "OK")

        # Export OpenTelemetry / MLflow format
        export_file = self.workspace / "trace.json"
        raw_json = tracer.export_json(str(export_file))
        self.assertTrue(export_file.exists())
        parsed = json.loads(raw_json)
        self.assertEqual(parsed["session_name"], "test_swarm_workflow")
        self.assertEqual(len(parsed["spans"]), 2)

    def test_mlflow_experiment_tracker(self) -> None:
        tracker = MLflowExperimentTracker(self.workspace / "mlruns")
        run = tracker.start_run(experiment_id="0", run_name="unit_test_run")
        self.assertIsNotNone(run.run_id)

        # Log parameters
        tracker.log_param("model", "claude-3-7-sonnet")
        tracker.log_param("mcts_simulations", 100)

        # Log metrics
        tracker.log_metric("accuracy", 0.98, step=1)
        tracker.log_metric("accuracy", 0.99, step=2)

        # Log artifact
        artifact_file = self.workspace / "test_artifact.txt"
        artifact_file.write_text("Hello MLflow Artifact", encoding="utf-8")
        tracker.log_artifact(artifact_file)

        tracker.end_run("FINISHED")

        # Verify filesystem layout (standard MLflow layout)
        run_dir = self.workspace / "mlruns" / "0" / run.run_id
        self.assertTrue((run_dir / "meta.yaml").exists())
        self.assertTrue((run_dir / "params" / "model").exists())
        self.assertTrue((run_dir / "metrics" / "accuracy").exists())
        self.assertTrue((run_dir / "artifacts" / "test_artifact.txt").exists())

    def test_llm_judge_evaluator(self) -> None:
        clean_code = """
def compute_sum(a: int, b: int) -> int:
    \"\"\"Calculates sum safely.\"\"\"
    return a + b
"""
        res = LLMJudgeEvaluator.evaluate_code("Compute sum", clean_code, tests_passed=True)
        self.assertTrue(res.passed)
        self.assertGreaterEqual(res.overall_score, 0.95)

        # Insecure code with eval
        insecure_code = """
def run_code(user_input):
    return eval(user_input)
"""
        bad_res = LLMJudgeEvaluator.evaluate_code("Run code", insecure_code, tests_passed=True)
        self.assertFalse(bad_res.passed)
        sec_metric = next(m for m in bad_res.metrics if m.name == "security_safety")
        self.assertFalse(sec_metric.passed)

    def test_ai_gateway_router(self) -> None:
        gateway = AIGatewayRouter()
        res = gateway.route_request("Hello Apex AI Gateway")
        self.assertEqual(res.provider_used, "gemini")
        self.assertGreater(res.estimated_cost_usd, 0.0)
        self.assertGreaterEqual(gateway.total_requests, 1)


if __name__ == "__main__":
    unittest.main()
