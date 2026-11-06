import unittest

from apex_council.formal.slicer import compute_backward_slice, format_slice_report


class TestApexSlicer(unittest.TestCase):
    def test_minimal_data_flow_slice(self):
        code = (
            "def compute():\n"
            "    a = 10\n"        # L2
            "    b = 20\n"        # L3 (irrelevant)
            "    c = a + 5\n"     # L4
            "    d = b * 2\n"     # L5 (irrelevant)
            "    return c\n"      # L6
        )
        slice_lines, sliced_code = compute_backward_slice(code, target_line=6)
        
        # Line 6 (return c) depends on c (L4), which depends on a (L2)
        self.assertIn(6, slice_lines)
        self.assertIn(4, slice_lines)
        self.assertIn(2, slice_lines)

        # L3 and L5 must NOT be in the slice
        self.assertNotIn(3, slice_lines)
        self.assertNotIn(5, slice_lines)

    def test_control_dependency_slice(self):
        code = (
            "def test(cond):\n"
            "    x = 0\n"
            "    if cond:\n"
            "        x = 42\n"
            "    return x\n"
        )
        slice_lines, _ = compute_backward_slice(code, target_line=5)
        # return x depends on x=42 and x=0, and x=42 is controlled by if cond
        self.assertIn(5, slice_lines)
        self.assertIn(4, slice_lines)
        self.assertIn(3, slice_lines)
        self.assertIn(2, slice_lines)

    def test_format_slice_report(self):
        code = "a = 1\nb = 2\nc = a + 1\n"
        slice_lines, _ = compute_backward_slice(code, target_line=3)
        report = format_slice_report("test.py", 3, slice_lines, code)
        self.assertIn("APEX SLICE", report)
        self.assertIn(">>> L003: c = a + 1", report)


if __name__ == "__main__":
    unittest.main()
