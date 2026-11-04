import threading
import time
import unittest

from apex_council.security.fuzzer import (
    BoundaryValueGenerator,
    ConcurrencyStressTester,
    PropertyFuzzer,
)


class TestFuzzerAndConcurrency(unittest.TestCase):
    def test_boundary_generator_types(self) -> None:
        ints = BoundaryValueGenerator.generate_for_type(int)
        self.assertIn(0, ints)
        self.assertIn(2**63 - 1, ints)

        strs = BoundaryValueGenerator.generate_for_type(str)
        self.assertIn("", strs)
        self.assertTrue(any("etc/passwd" in s for s in strs))

    def test_property_fuzzer_catches_zero_division(self) -> None:
        def unsafe_div(x: int, y: int) -> int:
            return x // y

        res = PropertyFuzzer.fuzz(unsafe_div)
        self.assertFalse(res.is_safe)
        crash_types = [c.exception_type for c in res.crashes]
        self.assertIn("ZeroDivisionError", crash_types)

    def test_property_fuzzer_invariant_violation(self) -> None:
        def flawed_abs(x: int) -> int:
            return x if x > 0 else x  # Bug: doesn't negate negative numbers!

        res = PropertyFuzzer.fuzz(flawed_abs, invariant=lambda ret: ret >= 0)
        self.assertFalse(res.is_safe)
        self.assertTrue(any(c.exception_type == "InvariantViolation" for c in res.crashes))

    def test_concurrency_stress_detects_data_race(self) -> None:
        counter = 0

        def racy_worker(tid: int, iteration: int) -> None:
            nonlocal counter
            v = counter
            # Tiny yield to let switchinterval trigger race
            time.sleep(0.000001)
            counter = v + 1

        thread_count = 4
        iters = 50
        res = ConcurrencyStressTester.stress_test(
            worker_fn=racy_worker,
            thread_count=thread_count,
            iterations_per_thread=iters,
            invariant_check=lambda: counter == thread_count * iters,
            timeout_sec=3.0,
        )
        self.assertTrue(res.race_detected)
        self.assertFalse(res.is_thread_safe)

    def test_concurrency_stress_passes_threadsafe_counter(self) -> None:
        lock = threading.Lock()
        counter = 0

        def safe_worker(tid: int, iteration: int) -> None:
            nonlocal counter
            with lock:
                counter += 1

        thread_count = 4
        iters = 50
        res = ConcurrencyStressTester.stress_test(
            worker_fn=safe_worker,
            thread_count=thread_count,
            iterations_per_thread=iters,
            invariant_check=lambda: counter == thread_count * iters,
            timeout_sec=3.0,
        )
        self.assertFalse(res.race_detected)
        self.assertFalse(res.deadlock_detected)
        self.assertTrue(res.is_thread_safe)


if __name__ == "__main__":
    unittest.main()
