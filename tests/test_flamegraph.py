import unittest

from apex_council.analysis.flamegraph import profile_function_or_file


class TestApexFlamegraph(unittest.TestCase):
    def test_profile_code_string(self):
        code = (
            "def worker():\n"
            "    total = sum(i * 2 for i in range(5000))\n"
            "    return total\n"
            "worker()\n"
        )
        report = profile_function_or_file(code_string=code)
        self.assertIn("APEX TERMINAL FLAMEGRAPH", report)
        self.assertIn("worker()", report)
        self.assertIn("Top CPU Bottlenecks", report)


if __name__ == "__main__":
    unittest.main()
