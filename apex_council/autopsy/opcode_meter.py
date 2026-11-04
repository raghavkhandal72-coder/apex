"""Deterministic CPython VM Opcode Meter and Complexity Delta Profiler.
Uses sys.settrace with frame.f_trace_opcodes=True to count exact bytecode VM instructions executed
alongside tracemalloc peak memory usage with zero external dependencies.
"""

from __future__ import annotations

import sys
import time
import tracemalloc
from collections import Counter
from dataclasses import dataclass, field
from types import FrameType
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass
class OpcodeProfileReport:
    total_opcodes: int
    opcode_distribution: Dict[str, int]
    peak_memory_bytes: int
    duration_ms: float
    return_value: Any = None
    exception_caught: Optional[str] = None


class OpcodeMeter:
    """Deterministic CPython instruction counter and memory profiler."""

    @classmethod
    def count_opcodes(cls, code: str) -> int:
        """Counts the total bytecode instructions in the compiled code string."""
        try:
            import dis
            co = compile(code, "<opcode_meter>", "exec")
            return len(list(dis.get_instructions(co)))
        except Exception:
            return 0

    @classmethod
    def profile_callable(
        cls,
        func: Callable[..., Any],
        *args: Any,
        target_code_name: Optional[str] = None,
        **kwargs: Any,
    ) -> OpcodeProfileReport:
        opcode_counts: Counter[str] = Counter()
        total_opcodes = 0

        def opcode_tracer(frame: FrameType, event: str, arg: Any) -> Any:
            nonlocal total_opcodes
            # Enable per-opcode tracing on frame
            frame.f_trace_opcodes = True
            if event == "opcode":
                if target_code_name is None or frame.f_code.co_name == target_code_name:
                    total_opcodes += 1
                    # Extract opname from bytecode at offset frame.f_lasti
                    code_bytes = frame.f_code.co_code
                    offset = frame.f_lasti
                    if 0 <= offset < len(code_bytes):
                        op_num = code_bytes[offset]
                        import dis
                        op_name = dis.opname[op_num]
                        opcode_counts[op_name] += 1
            return opcode_tracer

        ret_val = None
        exc_str = None
        orig_trace = sys.gettrace()

        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            sys.settrace(opcode_tracer)
            ret_val = func(*args, **kwargs)
        except Exception as ex:
            exc_str = f"{type(ex).__name__}: {str(ex)}"
        finally:
            sys.settrace(orig_trace)
            duration_ms = (time.perf_counter() - start_time) * 1000
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        return OpcodeProfileReport(
            total_opcodes=total_opcodes,
            opcode_distribution=dict(opcode_counts.most_common(15)),
            peak_memory_bytes=peak_mem,
            duration_ms=duration_ms,
            return_value=ret_val,
            exception_caught=exc_str,
        )

    @classmethod
    def compare_solutions(
        cls,
        solution_a: Callable[..., Any],
        solution_b: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Compares two candidate implementations to prove algorithmic complexity delta."""
        rep_a = cls.profile_callable(solution_a, *args, **kwargs)
        rep_b = cls.profile_callable(solution_b, *args, **kwargs)

        opcode_delta = rep_b.total_opcodes - rep_a.total_opcodes
        mem_delta = rep_b.peak_memory_bytes - rep_a.peak_memory_bytes

        return {
            "solution_a": {
                "opcodes": rep_a.total_opcodes,
                "peak_bytes": rep_a.peak_memory_bytes,
                "duration_ms": rep_a.duration_ms,
            },
            "solution_b": {
                "opcodes": rep_b.total_opcodes,
                "peak_bytes": rep_b.peak_memory_bytes,
                "duration_ms": rep_b.duration_ms,
            },
            "opcode_delta": opcode_delta,
            "memory_delta_bytes": mem_delta,
            "winner": "solution_a" if rep_a.total_opcodes <= rep_b.total_opcodes else "solution_b",
        }
