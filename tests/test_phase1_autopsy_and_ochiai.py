import unittest

from apex_council.autopsy.bytecode_inspector import BytecodeInspector
from apex_council.autopsy.ochiai import OchiaiFaultLocalizer
from apex_council.autopsy.opcode_meter import OpcodeMeter


class TestPhase1AutopsyAndOchiai(unittest.TestCase):
    def test_bytecode_inspector_pinpoints_zerodivision_opcode(self) -> None:
        def buggy_divide(a: int, b: int) -> int:
            numerator = a * 2
            denominator = b
            return numerator // denominator  # Crashing opcode: BINARY_OP / BINARY_FLOOR_DIVIDE

        ret, report = BytecodeInspector.execute_and_autopsy(buggy_divide, 10, 0)
        self.assertIsNone(ret)
        self.assertIsNotNone(report)
        self.assertTrue(report.crashed)
        self.assertEqual(report.exception_type, "ZeroDivisionError")
        self.assertIn("buggy_divide", report.crashing_function)
        self.assertIsNotNone(report.crashing_instruction)
        # Verify opcode is division related
        opname = report.crashing_instruction.opname
        self.assertTrue("BINARY" in opname or "DIVIDE" in opname or "OP" in opname)
        # Verify locals snapshot captured denominator=0
        self.assertIn("denominator", report.local_variables)
        self.assertEqual(report.local_variables["denominator"]["repr"], "0")

    def test_bytecode_inspector_pinpoints_index_error(self) -> None:
        def buggy_index(items: list[int]) -> int:
            idx = 100
            return items[idx]

        ret, report = BytecodeInspector.execute_and_autopsy(buggy_index, [1, 2, 3])
        self.assertIsNotNone(report)
        self.assertEqual(report.exception_type, "IndexError")
        self.assertIn("items", report.local_variables)
        self.assertEqual(report.local_variables["idx"]["repr"], "100")

    def test_ochiai_fault_localization_ranks_bug_top(self) -> None:
        source = """
def calculate_discount(price, is_member):
    discount = 0.0
    if is_member:
        discount = price * 0.10
    else:
        discount = price / 0  # Buggy line!
    return price - discount
"""
        localizer = OchiaiFaultLocalizer()
        # Test 1: Passing test
        localizer.trace_execution(source, "assert calculate_discount(100, True) == 90.0")
        # Test 2: Failing test
        localizer.trace_execution(source, "assert calculate_discount(100, False) == 100.0")

        ranked = localizer.rank_suspicious_statements()
        self.assertGreater(len(ranked), 0)
        # Top suspicious statement must be the division by zero line
        top = ranked[0]
        self.assertIn("discount = price / 0", top.source_code)
        self.assertAlmostEqual(top.suspiciousness, 1.0, places=2)

    def test_opcode_meter_complexity_comparison(self) -> None:
        def constant_lookup(n: int) -> int:
            return 42

        def linear_sum(n: int) -> int:
            total = 0
            for i in range(n):
                total += i
            return total

        comparison = OpcodeMeter.compare_solutions(constant_lookup, linear_sum, 100)
        self.assertEqual(comparison["winner"], "solution_a")
        self.assertGreater(comparison["opcode_delta"], 50)


if __name__ == "__main__":
    unittest.main()
