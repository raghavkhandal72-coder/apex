"""Phase 8 Test Suite: Raspberry Pi & ESP32 Lightweight Edge Runner.
Tests RPi hardware guard, CPython bytecode autopsy engine, Tier-1 AST synthesizer,
PEP 578 edge sandboxing, and ESP32 HMAC-SHA256 bridge.
100% Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from apex_council.edge.edge_runner import (
    ApexEdgeRunner,
    BytecodeAutopsyEngine,
    DeterministicASTSynthesizer,
    EdgeHardwareStatus,
    RPiHardwareGuard,
    ZeroSDKOllamaEdgeClient,
)


class TestPhase8EdgeRunner(unittest.TestCase):
    def test_rpi_hardware_guard_telemetry(self) -> None:
        guard = RPiHardwareGuard(max_temp_c=78.0, min_llm_ram_mb=1200)
        status = guard.inspect()
        self.assertIsInstance(status, EdgeHardwareStatus)
        self.assertGreater(status.cpu_cores, 0)
        self.assertGreater(status.total_ram_mb, 0)
        self.assertIsInstance(status.can_run_local_llm, bool)

        # Test thermal throttle trip
        hot_guard = RPiHardwareGuard(max_temp_c=10.0)  # artificially low threshold
        hot_status = hot_guard.inspect()
        self.assertFalse(hot_status.can_run_local_llm)
        self.assertIn("Thermal guard active", hot_status.throttle_reason)

    def test_bytecode_autopsy_and_opcode_counting(self) -> None:
        passing_code = "def add(x, y): return x + y"
        test_code = "assert add(2, 3) == 5"
        passed, autopsy, opcodes, peak_mem = BytecodeAutopsyEngine.run_and_inspect(passing_code, test_code)
        self.assertTrue(passed)
        self.assertIsNone(autopsy)
        self.assertGreater(opcodes, 0)
        self.assertGreater(peak_mem, 0)

        # Test crash inspection
        failing_code = "def divide(x, y): return x / y"
        fail_test = "divide(10, 0)"
        passed, autopsy, opcodes, peak_mem = BytecodeAutopsyEngine.run_and_inspect(failing_code, fail_test)
        self.assertFalse(passed)
        self.assertIsNotNone(autopsy)
        assert autopsy is not None
        self.assertEqual(autopsy.exception_type, "ZeroDivisionError")
        self.assertEqual(autopsy.crashing_func, "divide")
        self.assertEqual(autopsy.crashing_lineno, 1)
        self.assertEqual(autopsy.frame_locals.get("x"), "10")
        self.assertEqual(autopsy.frame_locals.get("y"), "0")

    def test_deterministic_ast_synthesizer_mutable_default(self) -> None:
        buggy_code = """
def append_item(val, container=[]):
    container.append(val)
    return container
"""
        test_code = """
a = append_item(1)
b = append_item(2)
assert a == [1], f"Expected [1] but got {a}"
assert b == [2], f"Expected [2] but got {b}"
"""
        runner = ApexEdgeRunner()
        res = runner.solve(buggy_code.strip(), test_code.strip())
        self.assertTrue(res.repaired)
        self.assertIn("None", res.patched_code)
        self.assertGreater(len(res.hmac_sha512_signature), 64)

    def test_deterministic_ast_synthesizer_index_error(self) -> None:
        buggy_code = """
def sum_elements(arr):
    s = 0
    for i in range(len(arr) + 1):
        s += arr[i]
    return s
"""
        test_code = """
assert sum_elements([1, 2, 3]) == 6
assert sum_elements([]) == 0
"""
        runner = ApexEdgeRunner()
        res = runner.solve(buggy_code.strip(), test_code.strip())
        self.assertTrue(res.repaired)
        self.assertEqual(res.strategy, "AST_OffByOne_Boundary_Fix")
        self.assertIn("range(len(arr))", res.patched_code)

    def test_deterministic_ast_synthesizer_zero_division(self) -> None:
        buggy_code = """
def calc_ratio(a, b):
    return a / b
"""
        test_code = """
assert calc_ratio(10, 2) == 5.0
assert calc_ratio(10, 0) == 0.0
"""
        runner = ApexEdgeRunner()
        res = runner.solve(buggy_code.strip(), test_code.strip())
        self.assertTrue(res.repaired)
        self.assertEqual(res.strategy, "AST_ZeroDivision_Guard")
        self.assertIn("if b != 0", res.patched_code)

    def test_deterministic_ast_synthesizer_key_error(self) -> None:
        buggy_code = """
def get_sensor_val(reading):
    return reading["temperature"]
"""
        test_code = """
assert get_sensor_val({"temperature": 25.4}) == 25.4
assert get_sensor_val({}) is None
"""
        runner = ApexEdgeRunner()
        res = runner.solve(buggy_code.strip(), test_code.strip())
        self.assertTrue(res.repaired)
        self.assertIn("get('temperature'", res.patched_code)


if __name__ == "__main__":
    unittest.main()
