import os
import sys
import tempfile
import unittest

from apex_council.repair.autonomous_loop import run_autonomous_loop


class TestApexAutonomousLoop(unittest.TestCase):
    def test_autonomous_loop_passing(self):
        cmd = f'"{sys.executable}" -c "exit(0)"'
        res = run_autonomous_loop(test_command=cmd, max_iterations=2)
        self.assertTrue(res["success"])
        self.assertEqual(res["iterations"], 1)

    def test_autonomous_loop_repairs_buggy_code(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_py = os.path.join(tmp_dir, "calc.py")
            test_py = os.path.join(tmp_dir, "test_calc.py")

            # Buggy implementation in calc.py
            with open(target_py, "w", encoding="utf-8") as f:
                f.write(
                    "def get_element(arr, idx):\n"
                    "    if idx > len(arr):\n" # Bug: should be idx >= len(arr)
                    "        raise IndexError('Out of bounds')\n"
                    "    return arr[idx]\n"
                )

            with open(os.path.join(tmp_dir, "tests.txt"), "w", encoding="utf-8") as f:
                f.write("assert get_element([10, 20], 1) == 20\n")

            with open(test_py, "w", encoding="utf-8") as f:
                f.write(
                    f"import sys; sys.path.insert(0, r'{tmp_dir}')\n"
                    "from calc import get_element\n"
                    "get_element([10, 20], 2)\n" # raises IndexError in calc.py!
                )

            # Test command that triggers the crash
            cmd = f'"{sys.executable}" "{test_py}"'
            # First verify it detects traceback and attempts repair
            from apex_council.repair.autonomous_loop import run_autonomous_loop
            res = run_autonomous_loop(test_command=cmd, max_iterations=2)
            self.assertIn("repaired_files", res)


if __name__ == "__main__":
    unittest.main()
