import unittest

from apex_council.lint.zero_div_guard import analyze_zero_divisions


class TestApexZeroDivGuard(unittest.TestCase):
    def test_literal_zero_division(self):
        code = "def calc():\n    return 10 / 0\n"
        violations = analyze_zero_divisions(code)
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0].is_literal_zero)
        self.assertEqual(violations[0].operator, "/")

    def test_unguarded_variable_division(self):
        code = (
            "def divide(a, b):\n"
            "    return a // b\n"
        )
        violations = analyze_zero_divisions(code)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].denominator, "b")
        self.assertFalse(violations[0].is_literal_zero)

    def test_guarded_division_passes(self):
        code = (
            "def safe_div(a, b):\n"
            "    if b != 0:\n"
            "        return a / b\n"
            "    return 0.0\n"
        )
        violations = analyze_zero_divisions(code)
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
