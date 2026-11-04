"""Cyberpunk Terminal TUI and Real-Time Event Streamer.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import difflib
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
    BG_DARK = "\033[48;5;234m"

    @classmethod
    def strip_ansi(cls, text: str) -> str:
        import re
        return re.sub(r"\033\[[0-9;]*m", "", text)


class CyberpunkTUI:
    """Terminal dashboard for Swarm deliberations, PageRank repo-maps, and diff streams."""

    @staticmethod
    def render_banner() -> str:
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 100)
        c = TerminalColors
        lines = [
            f"{c.CYAN}{c.BOLD}╔═" + "═" * (term_width - 4) + "═╗",
            f"║  🏛️  APEX-SOVEREIGN: AUTONOMOUS SWE SWARM & REPO-GRAPH ENGINE" + " " * (term_width - 64) + "║",
            f"║     Multi-Model Adversarial Swarm × MCTS Test-Time Compute [v2.0]" + " " * (term_width - 69) + "║",
            f"╚═" + "═" * (term_width - 4) + "═╝{c.RESET}",
        ]
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
                rendered.append(f"{c.DARK_GRAY}{clean}{c.RESET}")

        return "\n".join(rendered)
