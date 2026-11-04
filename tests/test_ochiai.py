import unittest
from pathlib import Path

from apex_council.graph.ochiai import OchiaiFaultLocalizer
from apex_council.graph.parser import SymbolParser


class TestOchiaiAndAdvancedGraph(unittest.TestCase):
    def test_advanced_parser_call_graph_and_exceptions(self) -> None:
        code = """
class Calculator:
    def add(self, a: int, b: int) -> int:
        x = a + b
        return x

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        try:
            return a / b
        except Exception:
            return 0.0
"""
        syms = SymbolParser.parse_python_source(code, filepath="calc.py")
        self.assertEqual(len(syms.definitions), 3)  # Calculator, add, divide

        # Def-use chains
        vars_defined = {d.variable for d in syms.def_use_chains}
        self.assertIn("x", vars_defined)

        # Exception flow
        raised = [e[0] for e in syms.exception_flow.raised_exceptions]
        handled = [e[0] for e in syms.exception_flow.handled_exceptions]
        self.assertIn("ZeroDivisionError", raised)
        self.assertIn("Exception", handled)

    def test_ochiai_fault_localization_pinpoints_bug(self) -> None:
        # Define buggy module logic
        def target_func(val: int) -> int:
            if val < 0:
                return -1  # Normal branch
            if val == 42:
                return 999  # BUGGY LINE: should be 42!
            return val * 2

        localizer = OchiaiFaultLocalizer()

        # Passing tests
        def test_pass_1():
            assert target_func(-5) == -1

        def test_pass_2():
            assert target_func(10) == 20

        def test_pass_3():
            assert target_func(3) == 6

        # Failing test (hits val == 42, expects 42 but gets 999)
        def test_fail():
            assert target_func(42) == 42

        localizer.trace_test_execution(test_pass_1)
        localizer.trace_test_execution(test_pass_2)
        localizer.trace_test_execution(test_pass_3)
        localizer.trace_test_execution(test_fail)

        self.assertEqual(localizer.total_passed_tests, 3)
        self.assertEqual(localizer.total_failed_tests, 1)

        scores = localizer.compute_ochiai_scores()
        self.assertGreater(len(scores), 0)

        # The buggy line was ONLY executed by the failing test, so Ochiai score is 1.0!
        top_bug = scores[0]
        self.assertEqual(top_bug.failed_executions, 1)
        self.assertEqual(top_bug.ochiai_score, 1.0)


if __name__ == "__main__":
    unittest.main()
