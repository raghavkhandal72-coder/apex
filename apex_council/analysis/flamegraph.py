"""
Apex Terminal Flamegraph (Feature #41).
Zero-dependency hierarchical execution profiler and ASCII flamegraph renderer.
Uses Python stdlib `cProfile` and `pstats` (pip = 0).
"""

from __future__ import annotations

import cProfile
import os
import pstats
import sys
from typing import Any, Dict, List, Optional


def profile_function_or_file(
    target_path: Optional[str] = None,
    code_string: Optional[str] = None,
    max_depth: int = 5,
    top_n: int = 8,
) -> str:
    """Profile script or code string and generate terminal flamegraph visualization."""
    profiler = cProfile.Profile()

    from ..security.ast_shield import ASTShield

    if target_path:
        abs_path = os.path.abspath(target_path)
        if not os.path.exists(abs_path):
            return f"Error: Target file not found: {target_path}"
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        ASTShield.inspect_ast_safety(code)
        _trusted_bin = compile(code, abs_path, "exec")
        global_vars = {"__file__": abs_path, "__name__": "__main__"}
        profiler.enable()
        try:
            exec(_trusted_bin, global_vars)
        except Exception as e:
            return f"Error executing target during profiling: {e}"
        finally:
            profiler.disable()
    elif code_string:
        ASTShield.inspect_ast_safety(code_string)
        _trusted_bin = compile(code_string, "<profiled_string>", "exec")
        scope: dict = {}
        profiler.enable()
        try:
            exec(_trusted_bin, scope)
        except Exception as e:
            return f"Error executing code string during profiling: {e}"
        finally:
            profiler.disable()
    else:
        return "Error: Either target_path or code_string must be provided."

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")

    # Format flamegraph
    return render_terminal_flamegraph(stats, top_n=top_n)


def render_terminal_flamegraph(stats: pstats.Stats, top_n: int = 8) -> str:
    """Render pstats into an ASCII hierarchical flamegraph."""
    total_time = stats.total_tt
    if total_time <= 0:
        total_time = 0.000001

    lines = [
        "APEX TERMINAL FLAMEGRAPH",
        "────────────────────────────────────────────────────────────────",
        f"Total Profiled Runtime: {total_time:.4f}s",
        "────────────────────────────────────────────────────────────────",
    ]

    # Collect stats items
    # stats.stats maps (filename, lineno, func_name) -> (cc, nc, tt, ct, callers)
    raw_stats = []
    for (filename, lineno, funcname), (cc, nc, tt, ct, callers) in stats.stats.items():
        base_file = os.path.basename(filename)
        # Skip internal profiler functions
        if base_file.startswith("cProfile") or base_file.startswith("pstats"):
            continue
        pct = (ct / total_time) * 100.0
        raw_stats.append({
            "file": base_file,
            "line": lineno,
            "func": funcname,
            "calls": nc,
            "cumtime": ct,
            "tottime": tt,
            "pct": pct,
        })

    raw_stats.sort(key=lambda x: x["cumtime"], reverse=True)
    top_items = raw_stats[:top_n]

    lines.append("Execution Call Hierarchy & Cumulative Latency:")
    for idx, item in enumerate(top_items):
        bar_len = int(item["pct"] / 5.0)
        bar = "█" * min(bar_len, 20)
        prefix = "├── " if idx < len(top_items) - 1 else "└── "
        lines.append(
            f"  {prefix}{item['pct']:5.1f}% [{bar:<20}] {item['cumtime']:.4f}s | "
            f"{item['func']}() ({item['file']}:{item['line']})"
        )

    lines.append("────────────────────────────────────────────────────────────────")
    lines.append("Top CPU Bottlenecks:")
    bottlenecks = sorted(raw_stats, key=lambda x: x["tottime"], reverse=True)[:5]
    for r, b in enumerate(bottlenecks, 1):
        lines.append(f"  {r}. {b['func']}() - {b['tottime']:.4f}s self-time ({b['pct']:.1f}% cum) in {b['file']}:{b['line']}")
    lines.append("────────────────────────────────────────────────────────────────\n")

    return "\n".join(lines)
