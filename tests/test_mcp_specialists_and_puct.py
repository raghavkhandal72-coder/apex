"""Unit tests for Apex-Council MCP Specialist Tools and AlphaZero PUCT Search Mechanics.
100% Pure Python Standard Library | Zero Dependencies | Zero Mocks.
"""

import json
import unittest

from apex_council.mcp_server import ApexCouncilMCPServer
from apex_council.search.sovereign_mcts import SovereignMCTSNode, SovereignMCTSEngine


class TestMCPSpecialistsAndPUCT(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ApexCouncilMCPServer(force_offline=True)

    def test_mcp_tools_list_contains_all_specialists(self) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}

        expected_tools = {
            "convene_council",
            "audit_code",
            "collaborative_relay",
            "repomap",
            "ochiai_localize",
            "bytecode_autopsy",
            "synthesize_fix",
            "verify_proof",
            "apex_solve",
            "apex_perf",
            "apex_chaos",
            "apex_appsec",
            "apex_db_tune",
            "apex_modernize",
            "apex_release",
            "apex_sbfl_triad",
            "apex_shapley_consensus",
            "apex_hoare_verify",
        }
        for expected in expected_tools:
            self.assertIn(expected, tool_names, f"Missing MCP tool: {expected}")

    def test_mcp_call_apex_sbfl_triad(self) -> None:
        src = "def add(a, b):\n    return a - b\n"
        tests = "assert add(1, 1) == 2\n"
        req = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "apex_sbfl_triad",
                "arguments": {"source_code": src, "test_code": tests},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["failed_tests"], 1)
        self.assertIsNotNone(payload["top_suspicious_line"])
        self.assertGreater(len(payload["ranked_lines"]), 0)

    def test_mcp_call_apex_shapley_consensus(self) -> None:
        evals = [
            {"agent_id": "a1", "role": "SDET", "confidence": 0.9, "vote": "APPROVE", "metric_score": 1.0},
            {"agent_id": "a2", "role": "AppSec", "confidence": 0.9, "vote": "APPROVE", "metric_score": 1.0},
        ]
        req = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {
                "name": "apex_shapley_consensus",
                "arguments": {"evaluations": evals},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertTrue(payload["quorum_passed"])
        self.assertEqual(payload["consensus_verdict"], "APPROVED")

    def test_mcp_call_apex_hoare_verify(self) -> None:
        src = "def divide(a, b):\n    return a / b\n"
        req = {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {
                "name": "apex_hoare_verify",
                "arguments": {"source_code": src},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertFalse(payload["is_provably_safe"])
        self.assertGreaterEqual(len(payload["violations"]), 1)

    def test_mcp_call_apex_perf(self) -> None:
        code = (
            "def slow_func(items):\n"
            "    res = ''\n"
            "    for i in items:\n"
            "        for j in items:\n"
            "            res += str(j)\n"
            "    return res\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "apex_perf",
                "arguments": {"code": code},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("antipatterns_detected", payload)
        self.assertGreaterEqual(len(payload["antipatterns_detected"]), 1)
        self.assertIn("optimized_code", payload)

    def test_mcp_call_apex_chaos(self) -> None:
        code = (
            "import time\n"
            "def process_data(data):\n"
            "    if not data:\n"
            "        return None\n"
            "    return [x * 2 for x in data]\n"
        )
        tests = (
            "assert process_data([1, 2, 3]) == [2, 4, 6]\n"
            "assert process_data([]) is None\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "apex_chaos",
                "arguments": {"code": code, "tests": tests},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("total_experiments", payload)
        self.assertIn("resilience_score", payload)
        self.assertGreater(payload["total_experiments"], 0)

    def test_mcp_call_apex_appsec(self) -> None:
        code = (
            "import sys\n"
            "def run_user_cmd():\n"
            "    user_input = sys.argv[1]\n"
            "    return eval(user_input)\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "apex_appsec",
                "arguments": {"code": code, "remediate": True},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertFalse(payload["is_airtight"])
        self.assertGreaterEqual(len(payload["vulnerabilities"]), 1)
        self.assertIn("ast.literal_eval", payload["remediated_code"])

    def test_mcp_call_apex_db_tune(self) -> None:
        code = (
            "def get_user_posts(users, cursor):\n"
            "    res = []\n"
            "    for u in users:\n"
            "        cursor.execute(f'SELECT * FROM posts WHERE user_id = {u.id}')\n"
            "        res.extend(cursor.fetchall())\n"
            "    return res\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "apex_db_tune",
                "arguments": {"code": code},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertFalse(payload["is_optimized"])
        self.assertGreaterEqual(len(payload["antipatterns"]), 1)
        self.assertGreaterEqual(len(payload["recommended_indexes"]), 1)

    def test_mcp_call_apex_modernize(self) -> None:
        code = (
            "from typing import Union, Optional\n"
            "def open_and_read(path: Union[str, None]) -> Optional[str]:\n"
            "    if path is None: return None\n"
            "    f = open(path, 'r')\n"
            "    data = f.read()\n"
            "    f.close()\n"
            "    return data\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "apex_modernize",
                "arguments": {"code": code},
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("transformations_applied", payload)
        self.assertGreaterEqual(len(payload["transformations_applied"]), 1)

    def test_mcp_call_apex_release(self) -> None:
        base_code = (
            "def calculate(a: int, b: int) -> int:\n"
            "    return a + b\n"
        )
        cand_code = (
            "def calculate(a: int, b: int, mode: str = 'sum') -> int:\n"
            "    return a + b\n"
            "def multiply(a: int, b: int) -> int:\n"
            "    return a * b\n"
        )
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "apex_release",
                "arguments": {
                    "base_code": base_code,
                    "candidate_code": cand_code,
                    "current_version": "1.0.0",
                },
            },
        }
        resp = self.server.handle_request(req)
        self.assertIsNotNone(resp)
        self.assertIn("result", resp)
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["current_version"], "1.0.0")
        self.assertEqual(payload["next_version"], "1.1.0")
        self.assertEqual(payload["bump_type"], "MINOR")
        self.assertFalse(payload["is_breaking"])
        self.assertIn("release_merkle_root", payload)
        self.assertIn("release_signature", payload)

    def test_puct_dynamic_scaling_and_normalization(self) -> None:
        root = SovereignMCTSNode(state="def root(): pass")
        root.visits = 100
        root.total_value = 50.0

        child = SovereignMCTSNode(state="def child(): pass", parent=root)
        child.visits = 10
        child.total_value = 8.0
        child.prior = 0.5

        # Standard PUCT calculation with dynamic c_puct
        puct_val = child.puct()
        self.assertGreater(puct_val, child.average_value)

        # Min-max Q normalized calculation
        puct_norm = child.puct(q_min=0.0, q_max=1.0)
        self.assertGreater(puct_norm, 0.0)

    def test_composite_value_evaluation(self) -> None:
        # Full pass
        v_pass = SovereignMCTSEngine.evaluate_composite_value(test_passed=True, syntax_valid=True)
        self.assertGreater(v_pass, 0.7)

        # Syntax failure
        v_syntax = SovereignMCTSEngine.evaluate_composite_value(test_passed=False, syntax_valid=False)
        self.assertLess(v_syntax, 0.0)

        # Complexity penalty
        v_complex = SovereignMCTSEngine.evaluate_composite_value(
            test_passed=True, syntax_valid=True, complexity_delta=5
        )
        self.assertLess(v_complex, v_pass)


if __name__ == "__main__":
    unittest.main()
