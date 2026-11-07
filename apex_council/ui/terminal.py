"""Cyberpunk Terminal TUI, Braille Sparklines, Split-Pane Dashboard, and Real-Time Event Streamer.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import difflib
import math
import os
import shutil
import sys
from typing import Any, Dict, List, Optional


class TerminalColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Cyberpunk palette
    CYAN = "\033[38;5;51m"
    NEON_GREEN = "\033[38;5;82m"
    MAGENTA = "\033[38;5;198m"
    GOLD = "\033[38;5;220m"
    ORANGE = "\033[38;5;208m"
    RED = "\033[38;5;196m"
    DARK_GRAY = "\033[38;5;240m"
    LIGHT_GRAY = "\033[38;5;250m"
    BG_DARK = "\033[48;5;234m"

    @classmethod
    def strip_ansi(cls, text: str) -> str:
        import re
        return re.sub(r"\033\[[0-9;]*m", "", text)


class CyberpunkTUI:
    """Terminal dashboard for Swarm deliberations, PageRank repo-maps, and diff streams."""

    SPARK_CHARS = (" ", "▂", "▃", "▄", "▅", "▆", "▇", "█")
    BRAILLE_SPINNER = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    @classmethod
    def render_sparkline(cls, values: List[float], width: Optional[int] = None) -> str:
        """Renders an ASCII/Unicode Braille sparkline chart from numeric values."""
        if not values:
            return ""
        min_v = min(values)
        max_v = max(values)
        range_v = max_v - min_v if max_v != min_v else 1.0

        target_vals = values[-width:] if width and len(values) > width else values
        chars = []
        for v in target_vals:
            idx = int(((v - min_v) / range_v) * (len(cls.SPARK_CHARS) - 1))
            idx = max(0, min(len(cls.SPARK_CHARS) - 1, idx))
            chars.append(cls.SPARK_CHARS[idx])
        return "".join(chars)

    @classmethod
    def get_spinner_frame(cls, index: int) -> str:
        return cls.BRAILLE_SPINNER[index % len(cls.BRAILLE_SPINNER)]

    @staticmethod
    def render_banner() -> str:
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 100)
        c = TerminalColors
        inner_width = term_width - 4
        title1 = "🏛️  APEX-SOVEREIGN: AUTONOMOUS SWE SWARM & REPO-GRAPH ENGINE"
        title2 = "Multi-Model Adversarial Swarm × MCTS Test-Time Compute [v2.0]"
        lines = [
            f"{c.CYAN}{c.BOLD}╔═" + "═" * inner_width + "═╗",
            f"║  {title1}" + " " * max(0, inner_width - len(title1) + 2) + "║",
            f"║     {title2}" + " " * max(0, inner_width - len(title2) - 3) + "║",
            f"╚═" + "═" * inner_width + f"═╝{c.RESET}",
        ]
        return "\n".join(lines)

    @classmethod
    def render_split_pane(cls, left_lines: List[str], right_lines: List[str], width: int = 90) -> str:
        """Renders two columns side-by-side with a vertical ANSI divider."""
        c = TerminalColors
        col_width = (width - 3) // 2
        max_rows = max(len(left_lines), len(right_lines))
        out: List[str] = []

        header = f"{c.GOLD}┌{'─' * col_width}┬{'─' * col_width}┐{c.RESET}"
        out.append(header)

        for i in range(max_rows):
            l = left_lines[i] if i < len(left_lines) else ""
            r = right_lines[i] if i < len(right_lines) else ""
            clean_l = c.strip_ansi(l)[:col_width]
            clean_r = c.strip_ansi(r)[:col_width]
            pad_l = " " * (col_width - len(clean_l))
            pad_r = " " * (col_width - len(clean_r))
            out.append(f"{c.GOLD}│{c.RESET} {l}{pad_l} {c.GOLD}│{c.RESET} {r}{pad_r} {c.GOLD}│{c.RESET}")

        footer = f"{c.GOLD}└{'─' * col_width}┴{'─' * col_width}┘{c.RESET}"
        out.append(footer)
        return "\n".join(out)

    @classmethod
    def render_mcts_tree(cls, trajectory: List[str]) -> str:
        """Renders an MCTS winning trajectory as a visual tree."""
        c = TerminalColors
        lines = [f"{c.CYAN}{c.BOLD}🌲 MCTS Rollout Trajectory Spine:{c.RESET}"]
        for i, step in enumerate(trajectory):
            is_last = (i == len(trajectory) - 1)
            prefix = "└── " if is_last else "├── "
            lines.append(f"  {c.GOLD}{prefix}{c.RESET}{step}")
        return "\n".join(lines)

    @staticmethod
    def render_swarm_card(solution: Any) -> str:
        c = TerminalColors
        b = solution.blueprint
        r = solution.reproduction_suite
        m = solution.audit_receipt

        lines = [
            f"{c.GOLD}{c.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c.RESET}",
            f"{c.MAGENTA}{c.BOLD}🏛️  STAFF ARCHITECT BLUEPRINT{c.RESET}",
            f"  {c.CYAN}Target Components:{c.RESET} {', '.join(b.target_components)}",
            f"  {c.CYAN}Primary Symbol:{c.RESET}    {b.primary_symbol}",
            f"  {c.CYAN}Invariants:{c.RESET}        {b.invariants[0]}",
            "",
            f"{c.ORANGE}{c.BOLD}🧪  TEST-FIRST SPECULATOR (TDD){c.RESET}",
            f"  {c.CYAN}Contract Rationale:{c.RESET} {r.rationale}",
            f"  {c.CYAN}Test Assertions:{c.RESET}    {len(r.test_assertions)} verified conditions",
            "",
            f"{c.CYAN}{c.BOLD}🌲  MCTS TEST-TIME COMPUTE SEARCH{c.RESET}",
            f"  {c.CYAN}Explored States:{c.RESET}    {solution.total_nodes_explored} candidate AST trees",
            f"  {c.CYAN}Pruned Branches:{c.RESET}    {m.get('pruned_branches', 0)} invalid/hostile mutations",
            f"  {c.CYAN}Terminal Reward:{c.RESET}    {solution.mcts_score:.2f} (1.0 = Clean Sandbox Pass)",
            "",
            f"{c.NEON_GREEN}{c.BOLD}🔏  SOVEREIGN GATEKEEPER ATTESTATION{c.RESET}",
            f"  {c.CYAN}Execution Status:{c.RESET}   {'PASSED (HERMETIC ISOLATION)' if solution.is_passing else 'FAILED'}",
            f"  {c.CYAN}HMAC-SHA512 Seal:{c.RESET}   {solution.signature[:32]}... [VERIFIED]",
            f"  {c.CYAN}Execution Latency:{c.RESET}  {solution.execution_time_ms:.1f}ms",
            f"{c.GOLD}{c.BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{c.RESET}",
        ]
        return "\n".join(lines)

    @staticmethod
    def render_diff(old_code: str, new_code: str) -> str:
        c = TerminalColors
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="original", tofile="sovereign_patch"))

        if not diff:
            return f"{c.DARK_GRAY}No modifications detected (code identical).{c.RESET}"

        rendered = [f"{c.BOLD}--- Sovereign Git Diff Stream ---{c.RESET}"]
        for line in diff:
            clean = line.rstrip("\r\n")
            if clean.startswith("+++") or clean.startswith("---"):
                rendered.append(f"{c.BOLD}{clean}{c.RESET}")
            elif clean.startswith("@@"):
                rendered.append(f"{c.CYAN}{clean}{c.RESET}")
            elif clean.startswith("+"):
                rendered.append(f"{c.NEON_GREEN}{clean}{c.RESET}")
            elif clean.startswith("-"):
                rendered.append(f"{c.RED}{clean}{c.RESET}")
            else:
                rendered.append(f"  {clean}")
        return "\n".join(rendered)
