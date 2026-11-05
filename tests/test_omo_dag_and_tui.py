#!/usr/bin/env python3
"""
Unit Test Suite for OmO Task DAG Wave Engine & Re-Designed Apex Pixel Mascot
100% Pure Python Standard Library | Zero Dependencies
"""

import unittest
from apex_council.omo.dag_compiler import DagCompiler, DagNodeInput, DagRoute
from apex_council.omo.dag_executor import DagExecutor
from apex_council.omo.dag_tui import DagTuiRenderer
from apex_council.ui.mascot import MascotRenderer, MascotTheme


class TestOmODagAndMascotSuite(unittest.TestCase):

    def test_dag_compilation_and_wave_partitioning(self):
        nodes = [
            DagNodeInput(id="step_a", prompt="Step A", category="plan"),
            DagNodeInput(id="step_b", prompt="Step B", category="code"),
            DagNodeInput(id="step_c", prompt="Step C", category="test", depends_on=["step_a", "step_b"]),
            DagNodeInput(id="step_d", prompt="Step D", category="deploy", depends_on=["step_c"]),
        ]
        result = DagCompiler.compile(nodes)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.nodes), 4)
        self.assertEqual(len(result.waves), 3)

        # Wave 0 must contain step_a and step_b
        self.assertEqual(sorted(result.waves[0].node_ids), ["step_a", "step_b"])
        # Wave 1 must contain step_c
        self.assertEqual(result.waves[1].node_ids, ["step_c"])
        # Wave 2 must contain step_d
        self.assertEqual(result.waves[2].node_ids, ["step_d"])

    def test_dag_cycle_detection(self):
        nodes = [
            DagNodeInput(id="node_x", prompt="X", depends_on=["node_y"]),
            DagNodeInput(id="node_y", prompt="Y", depends_on=["node_z"]),
            DagNodeInput(id="node_z", prompt="Z", depends_on=["node_x"]),
        ]
        result = DagCompiler.compile(nodes)
        self.assertFalse(result.ok)
        self.assertTrue(any("cycle detected" in err.lower() for err in result.errors))

    def test_dag_critical_path_and_bottleneck_detection(self):
        nodes = [
            DagNodeInput(id="init", prompt="Init"),
            DagNodeInput(id="task_1", prompt="Task 1", depends_on=["init"]),
            DagNodeInput(id="task_2", prompt="Task 2", depends_on=["init"]),
            DagNodeInput(id="join_point", prompt="Join Point", depends_on=["task_1", "task_2"]),
            DagNodeInput(id="finish", prompt="Finish", depends_on=["join_point"]),
        ]
        result = DagCompiler.compile(nodes)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.critical_path), 4)
        self.assertIn("join_point", result.bottlenecks)

    def test_dag_executor_telemetry(self):
        nodes = [
            DagNodeInput(id="worker_1", prompt="Work 1"),
            DagNodeInput(id="worker_2", prompt="Work 2"),
            DagNodeInput(id="aggregator", prompt="Aggregate", depends_on=["worker_1", "worker_2"]),
        ]
        comp = DagCompiler.compile(nodes)
        executor = DagExecutor(comp)

        waves_started = []
        waves_completed = []

        telemetry = executor.execute_all(
            on_wave_start=lambda idx, nids: waves_started.append(idx),
            on_wave_complete=lambda idx, nids: waves_completed.append(idx),
        )

        self.assertEqual(telemetry.completed_nodes_count, 3)
        self.assertEqual(len(waves_started), 2)
        self.assertEqual(len(waves_completed), 2)
        self.assertGreater(telemetry.total_tokens, 0)
        self.assertGreater(telemetry.total_cost_usd, 0.0)

    def test_dag_tui_rendering_image1_parity(self):
        nodes = [
            DagNodeInput(id="navigation", prompt="Nav", category="quick"),
            DagNodeInput(id="gate-wiring", prompt="Gates", category="quick"),
            DagNodeInput(id="test-coverage", prompt="Coverage", category="quick"),
            DagNodeInput(id="verify-evidence", prompt="Evidence", category="quick", depends_on=["navigation", "gate-wiring", "test-coverage"]),
        ]
        res = DagCompiler.compile(nodes)
        rendered = DagTuiRenderer.render_full_screen(res, task_title="Linear gates integration evidence 1/1")

        self.assertIn("DAG · 01a97526", rendered)
        self.assertIn("Linear gates integration evidence", rendered)
        self.assertIn("navigation", rendered)
        self.assertIn("gate-wiring", rendered)
        self.assertIn("test-coverage", rendered)
        self.assertIn("verify-evidence", rendered)
        self.assertIn("AUTOTEST-GROUP", rendered)
        self.assertIn("Connected 1-40/49", rendered)

    def test_apex_redesigned_mascots(self):
        # All 4 mascot styles should render cleanly
        for style in ["falcon", "guardian", "aegis", "retro"]:
            for color in ["gold", "amber", "cyan", "emerald"]:
                hdr = MascotRenderer.render_header(style=style, theme_name=color)
                self.assertIn("Apex-Sovereign", hdr)
                self.assertIn("MCTS PUCT", hdr)

        status_bar = MascotRenderer.render_status_bar("~/w/acme.billing", "#6", ":16156", "Opus 4.6")
        self.assertIn("~/w/acme.billing", status_bar)
        self.assertIn("#6", status_bar)


if __name__ == "__main__":
    unittest.main()
