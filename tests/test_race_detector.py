"""Tests for Concurrency Lock Inversion & Deadlock Prover."""

import unittest
from apex_council.analysis.race_detector import DeadlockProver, handle_race_cli


class TestRaceDetector(unittest.TestCase):
    def test_clean_single_lock_passes(self):
        code = """
import threading
lock = threading.Lock()
def worker():
    with lock:
        pass
"""
        rep = DeadlockProver.analyze_source(code, "clean.py")
        self.assertTrue(rep.is_deadlock_free)
        self.assertEqual(len(rep.deadlock_hazards), 0)

    def test_cyclic_lock_order_detected(self):
        code = """
import threading
l1 = threading.Lock()
l2 = threading.Lock()
def t1():
    with l1:
        with l2:
            pass
def t2():
    with l2:
        with l1:
            pass
"""
        rep = DeadlockProver.analyze_source(code, "deadlock.py")
        self.assertFalse(rep.is_deadlock_free)
        self.assertTrue(len(rep.deadlock_hazards) > 0)
        self.assertIn("l1 -> l2 -> l1", rep.deadlock_hazards[0].explanation)

    def test_handle_race_cli_help(self):
        self.assertEqual(handle_race_cli(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
