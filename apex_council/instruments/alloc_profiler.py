"""
Apex Instruments: Apple-Grade Memory Allocation & Leak Tracker.
Line-by-line heap allocation hotspots, peak RAM footprint, and circular reference detection.
Pure Python standard library (tracemalloc, gc). Zero dependencies (pip = 0).
"""

from __future__ import annotations

import gc
import os
import sys
import tracemalloc
from typing import Any, Dict, List, Optional, Tuple


def profile_memory_allocations(
    target_path: Optional[str] = None,
    code_string: Optional[str] = None,
    top_n: int = 6,
) -> str:
    """Run target under tracemalloc and gc to capture memory allocations and leak telemetry."""
    if not target_path and not code_string:
        return "Error: Provide target script path or code string to profile."

    # 1. Clean garbage collection state
    gc.collect()
    initial_objects = len(gc.get_objects())

    # 2. Start tracemalloc
    tracemalloc.start()
    snapshot_start = tracemalloc.take_snapshot()

    global_env = {"__name__": "__main__"}
    if target_path:
        abs_p = os.path.abspath(target_path)
        if not os.path.exists(abs_p):
            tracemalloc.stop()
            return f"Error: Target file not found: {target_path}"
        global_env["__file__"] = abs_p
        with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
            code_to_exec = f.read()
    else:
        abs_p = "<memory>"
        code_to_exec = code_string or ""

    try:
        compiled = compile(code_to_exec, abs_p, "exec")
        exec(compiled, global_env)
    except Exception as e:
        tracemalloc.stop()
        return f"Error during memory profiling execution: {e}"

    # 3. Take post-execution snapshots
    snapshot_end = tracemalloc.take_snapshot()
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 4. Analyze circular references via gc
    gc.collect()
    unreachable_cycles = len(gc.garbage)
    post_objects = len(gc.get_objects())

    # 5. Compute line-by-line stats
    stats = snapshot_end.compare_to(snapshot_start, "lineno")
    alloc_items: List[Dict[str, Any]] = []

    for stat in stats[:top_n]:
        frame = stat.traceback[0]
        base_f = os.path.basename(frame.filename)
        # Skip internal python interpreter frames
        if base_f.startswith("<") or base_f.startswith("tracemalloc"):
            continue
        size_kb = stat.size_diff / 1024.0
        if size_kb > 0:
            alloc_items.append({
                "file": base_f,
                "line": frame.lineno,
                "size_kb": size_kb,
                "count": stat.count_diff,
            })

    return render_instruments_report(
        peak_kb=peak_mem / 1024.0,
        current_kb=current_mem / 1024.0,
        objects_count=post_objects - initial_objects,
        cyclic_leaks=unreachable_cycles,
        allocations=alloc_items,
        target_name=os.path.basename(abs_p),
    )


def render_instruments_report(
    peak_kb: float,
    current_kb: float,
    objects_count: int,
    cyclic_leaks: int,
    allocations: List[Dict[str, Any]],
    target_name: str,
) -> str:
    """Format an Apple Instruments-styled visual memory report."""
    leak_badge = "0 [HEALTHY]" if cyclic_leaks == 0 else f"{cyclic_leaks} [LEAK DETECTED]"
    peak_str = f"{peak_kb / 1024.0:.2f} MB" if peak_kb >= 1024 else f"{peak_kb:.1f} KB"
    current_str = f"{current_kb / 1024.0:.2f} MB" if current_kb >= 1024 else f"{current_kb:.1f} KB"

    lines = [
        "╭─────────────────────────────────────────────────────────────╮",
        f"│  🍎 APEX INSTRUMENTS: MEMORY & OBJECT ALLOCATIONS           │",
        f"│  Target: {target_name:<50} │",
        "├─────────────────────────────────────────────────────────────┤",
        f"│  Peak Heap Footprint : {peak_str:<36} │",
        f"│  Retained Footprint  : {current_str:<36} │",
        f"│  Net Heap Objects    : {objects_count:<36} │",
        f"│  Cyclic Object Leaks : {leak_badge:<36} │",
        "├─────────────────────────────────────────────────────────────┤",
        "│  Top Allocation Hotspots by Line:                           │",
    ]

    total_tracked_kb = sum(a["size_kb"] for a in allocations) or 0.0001
    for a in allocations:
        pct = (a["size_kb"] / total_tracked_kb) * 100.0
        bar_len = int(pct / 5.0)
        bar = "█" * min(bar_len, 16)
        loc = f"L{a['line']:02d} in {a['file']}"
        size_fmt = f"{a['size_kb']:.1f} KB"
        lines.append(f"│    {loc:<16} [{bar:<16}] {size_fmt:>9} ({pct:5.1f}%) │")

    if not allocations:
        lines.append("│    Zero persistent allocations recorded (stack-only).       │")

    lines.extend([
        "╰─────────────────────────────────────────────────────────────╯",
        "",
    ])
    return "\n".join(lines)
