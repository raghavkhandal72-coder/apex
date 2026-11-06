import unittest

from apex_council.instruments.alloc_profiler import profile_memory_allocations


class TestApexAllocProfiler(unittest.TestCase):
    def test_profile_memory_allocations(self):
        code = (
            "def allocate():\n"
            "    data = [str(i) * 100 for i in range(1000)]\n"
            "    return len(data)\n"
            "allocate()\n"
        )
        report = profile_memory_allocations(code_string=code)
        self.assertIn("APEX INSTRUMENTS", report)
        self.assertIn("Peak Heap Footprint", report)
        self.assertIn("Cyclic Object Leaks", report)


if __name__ == "__main__":
    unittest.main()
