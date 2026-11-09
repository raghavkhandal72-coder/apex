"""Tests for Python-to-C99 Systems Transpiler."""

import unittest
from apex_council.transpiler.c_transpiler import PythonToCTranspiler, handle_transpile_cli


class TestCTranspiler(unittest.TestCase):
    def test_transpile_math_function(self):
        code = """
def square(x: int) -> int:
    return x * x
"""
        res = PythonToCTranspiler.transpile_source(code)
        self.assertTrue(res["success"])
        self.assertIn("int64_t square(int64_t x) {", res["c_code"])
        self.assertIn("return (x * x);", res["c_code"])

    def test_transpile_loop_and_bounds(self):
        code = """
def sum_array(arr: list[int]) -> int:
    total = 0
    for i in range(len(arr)):
        total += arr[i]
    return total
"""
        res = PythonToCTranspiler.transpile_source(code)
        self.assertTrue(res["success"])
        self.assertIn("const int64_t* arr, size_t arr_len", res["c_code"])
        self.assertIn("for (int64_t i = 0; i < arr_len; i += 1)", res["c_code"])

    def test_handle_transpile_cli_help(self):
        self.assertEqual(handle_transpile_cli(["--help"]), 0)


if __name__ == "__main__":
    unittest.main()
