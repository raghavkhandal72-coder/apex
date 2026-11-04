"""Type-Driven Property Boundary Fuzzer and Concurrency Race Stress-Tester.
Enforces edge-case resilience and thread-safety by fuzzing boundary inputs
and maximizing thread preemption via CPython sys.setswitchinterval.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import inspect
import math
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, get_type_hints


class BoundaryValueGenerator:
    """Generates rigorous edge-case, boundary, and hostile inputs for arbitrary types."""

    @staticmethod
    def get_int_boundaries() -> List[int]:
        return [
            0,
            1,
            -1,
            42,
            -42,
            127,
            -128,
            255,
            256,
            32767,
            -32768,
            65535,
            65536,
            2**31 - 1,
            -2**31,
            2**32 - 1,
            2**63 - 1,
            -2**63,
            2**64 - 1,
            10**18,
            -10**18,
        ]

    @staticmethod
    def get_float_boundaries() -> List[float]:
        return [
            0.0,
            -0.0,
            1.0,
            -1.0,
            0.5,
            -0.5,
            1e-7,
            -1e-7,
            1e-15,
            -1e-15,
            1e308,
            -1e308,
            float("inf"),
            float("-inf"),
            float("nan"),
        ]

    @staticmethod
    def get_str_boundaries() -> List[str]:
        return [
            "",
            " ",
            "   ",
            "\t",
            "\n",
            "\r\n",
            "\x00",
            "\x00\x00\x00",
            "A" * 1000,
            "A" * 10000,
            "0",
            "-1",
            "NaN",
            "null",
            "None",
            "undefined",
            "true",
            "false",
            "../../../../../../etc/passwd",
            "..\\..\\..\\..\\windows\\system32",
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "<script>alert(1)</script>",
            "${7*7}",
            "{{7*7}}",
            "🚀🔥💀🤖",
            "مرحبا",
            "コンニチハ",
            "\uffff",
            "\u200b",  # zero-width space
        ]

    @staticmethod
    def get_bytes_boundaries() -> List[bytes]:
        return [
            b"",
            b"\x00",
            b"\x00" * 32,
            b"\xff" * 32,
            b"A" * 1024,
            b"\r\n\r\n",
            b"\x7fELF",
            b"PK\x03\x04",
        ]

    @staticmethod
    def get_bool_boundaries() -> List[bool]:
        return [False, True]

    @classmethod
    def generate_for_type(cls, target_type: Any) -> List[Any]:
        """Resolves type hint and returns comprehensive boundary inputs."""
        if target_type in (int, "int"):
            return cls.get_int_boundaries()
        if target_type in (float, "float"):
            return cls.get_float_boundaries()
        if target_type in (str, "str"):
            return cls.get_str_boundaries()
        if target_type in (bytes, "bytes"):
            return cls.get_bytes_boundaries()
        if target_type in (bool, "bool"):
            return cls.get_bool_boundaries()
        if target_type in (list, "list", List):
            return [[], [None], [0], [""], [1, 2, 3], list(range(100))]
        if target_type in (dict, "dict", Dict):
            return [{}, {"": ""}, {0: 0}, {"key": None}, {"__proto__": {}}, {"admin": True}]
        if target_type in (tuple, "tuple", Tuple):
            return [(), (0,), ("",), (None, None)]

        # Default fallback: broad coverage
        return [None, 0, "", [], {}, True, False]


@dataclass
class FuzzCrash:
    exception_type: str
    message: str
    inputs: Dict[str, Any]
    traceback_str: str


@dataclass
class PropertyFuzzResult:
    function_name: str
    total_runs: int
    passed_count: int
    crashes: List[FuzzCrash] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        return len(self.crashes) == 0


class PropertyFuzzer:
    """Type-driven automated boundary fuzzer that verifies contracts, invariants, and edge-cases."""

    @staticmethod
    def fuzz(
        func: Callable[..., Any],
        invariant: Optional[Callable[[Any], bool]] = None,
        max_cases: int = 150,
    ) -> PropertyFuzzResult:
        sig = inspect.signature(func)
        try:
            type_hints = get_type_hints(func)
        except Exception:
            type_hints = {}

        param_boundaries: Dict[str, List[Any]] = {}
        for param_name, param in sig.parameters.items():
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            hint = type_hints.get(param_name, param.annotation if param.annotation != inspect.Parameter.empty else Any)
            param_boundaries[param_name] = BoundaryValueGenerator.generate_for_type(hint)

        if not param_boundaries:
            # Function takes 0 args
            test_cases = [{}]
        else:
            # Generate cross-product or zipped boundary cases up to max_cases
            test_cases: List[Dict[str, Any]] = []
            keys = list(param_boundaries.keys())

            # 1. Single-parameter boundary variations with default/first values for others
            for k in keys:
                for val in param_boundaries[k]:
                    case = {other_k: param_boundaries[other_k][0] for other_k in keys}
                    case[k] = val
                    test_cases.append(case)
                    if len(test_cases) >= max_cases:
                        break
                if len(test_cases) >= max_cases:
                    break

        total_runs = 0
        passed_count = 0
        crashes: List[FuzzCrash] = []

        for case in test_cases:
            total_runs += 1
            try:
                ret = func(**case)
                if invariant is not None:
                    if not invariant(ret):
                        crashes.append(
                            FuzzCrash(
                                exception_type="InvariantViolation",
                                message="Function return value violated custom property invariant",
                                inputs=case,
                                traceback_str="",
                            )
                        )
                        continue
                passed_count += 1
            except Exception as ex:
                tb = traceback.format_exc()
                crashes.append(
                    FuzzCrash(
                        exception_type=type(ex).__name__,
                        message=str(ex),
                        inputs=case,
                        traceback_str=tb,
                    )
                )

        return PropertyFuzzResult(
            function_name=getattr(func, "__name__", "unknown_func"),
            total_runs=total_runs,
            passed_count=passed_count,
            crashes=crashes,
        )


@dataclass
class ConcurrencyStressResult:
    target_name: str
    thread_count: int
    iterations_per_thread: int
    total_operations: int
    duration_sec: float
    race_detected: bool
    deadlock_detected: bool
    errors: List[str] = field(default_factory=list)

    @property
    def is_thread_safe(self) -> bool:
        return not self.race_detected and not self.deadlock_detected and len(self.errors) == 0


class ConcurrencyStressTester:
    """Stress-tests multithreaded logic by cranking CPython's GIL switch interval to 1e-6 seconds.
    Forces extreme thread preemption to provoke latent race conditions, data races, and deadlocks.
    """

    @staticmethod
    def stress_test(
        worker_fn: Callable[[int, int], None],
        thread_count: int = 8,
        iterations_per_thread: int = 200,
        invariant_check: Optional[Callable[[], bool]] = None,
        timeout_sec: float = 5.0,
    ) -> ConcurrencyStressResult:
        orig_switch = sys.getswitchinterval()
        # Maximize thread interleaving
        sys.setswitchinterval(1e-6)

        errors: List[str] = []
        barrier = threading.Barrier(thread_count)
        threads: List[threading.Thread] = []

        def wrapped_worker(tid: int) -> None:
            try:
                # Synchronize all threads at the starting gate
                barrier.wait(timeout=2.0)
                for i in range(iterations_per_thread):
                    worker_fn(tid, i)
            except Exception as ex:
                errors.append(f"Thread {tid} error: {type(ex).__name__}: {str(ex)}")

        start_time = time.perf_counter()
        try:
            for tid in range(thread_count):
                t = threading.Thread(target=wrapped_worker, args=(tid,), daemon=True)
                threads.append(t)
                t.start()

            for t in threads:
                t.join(timeout=timeout_sec)

            alive = [t for t in threads if t.is_alive()]
            deadlock_detected = len(alive) > 0
            if deadlock_detected:
                errors.append(f"Deadlock detected: {len(alive)} worker threads hung after {timeout_sec}s")

            race_detected = False
            if invariant_check is not None:
                if not invariant_check():
                    race_detected = True
                    errors.append("Concurrency race detected: invariant failed after multithreaded execution")

            duration = time.perf_counter() - start_time
            return ConcurrencyStressResult(
                target_name=getattr(worker_fn, "__name__", "worker_fn"),
                thread_count=thread_count,
                iterations_per_thread=iterations_per_thread,
                total_operations=thread_count * iterations_per_thread,
                duration_sec=duration,
                race_detected=race_detected,
                deadlock_detected=deadlock_detected,
                errors=errors,
            )
        finally:
            sys.setswitchinterval(orig_switch)
