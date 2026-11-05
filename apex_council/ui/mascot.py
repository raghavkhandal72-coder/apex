#!/usr/bin/env python3
"""
Apex-Sovereign: Pixel Mascot & Retro-Cyberpunk Terminal Aesthetics
Inspired by Claude Code (Image 2) & Worktrunk (Image 1)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional, Tuple


class MascotTheme:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Claude Code warm terracotta / amber palette
    AMBER = "\033[38;5;208m"
    PEACH = "\033[38;5;215m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;244m"
    DARK_GRAY = "\033[38;5;238m"
    GREEN = "\033[38;5;114m"
    CYAN = "\033[38;5;75m"
    RED = "\033[38;5;203m"
    BG_CREAM = "\033[48;5;230m"
    BG_DARK = "\033[48;5;235m"


# 6-line pixel robot / mascot (Claude Code style)
APEX_PIXEL_MASCOT = [
    "  ▟█▙   ▟█▙  ",
    "  █████████  ",
    "  █▗▖█ █▗▖█  ",
    "  █████████  ",
    "  █▀▀▀▀▀▀▀█  ",
    "   █     █   ",
]

# Alternate Sovereign Cyber-Falcon mascot
APEX_FALCON_MASCOT = [
    "   ▄█▀▀█▄   ",
    " ▄█▀ █  ▀█▄ ",
    " █  ▄▄▄▄  █ ",
    " █ █▗▖  █ █ ",
    "  ▀█▄▄▄▄█▀  ",
    "    ▀  ▀    ",
]


class MascotRenderer:
    """Renders the iconic pixel mascot header, prompt boxes, and status bars."""

    @classmethod
    def render_header(
        cls,
        version: str = "v2.5.0",
        model: str = "Claude 3.7 Sonnet · Gemini 2.5 · GPT-4o",
        workspace_path: Optional[str] = None,
        tip: Optional[str] = None,
        falcon: bool = False,
    ) -> str:
        """Renders Claude Code style header with pixel mascot avatar."""
        t = MascotTheme
        cwd = workspace_path or os.getcwd()
        if len(cwd) > 40:
            cwd = "..." + cwd[-37:]

        mascot_lines = APEX_FALCON_MASCOT if falcon else APEX_PIXEL_MASCOT
        info_lines = [
            f"{t.BOLD}{t.WHITE}Apex-Sovereign {version}{t.RESET}",
            f"{t.AMBER}{model}{t.RESET}",
            f"{t.GRAY}{cwd}{t.RESET}",
            f"{t.CYAN}★ MCTS PUCT × CEGIS Inductive Synthesis × SBFL Triad{t.RESET}",
            f"{t.GREEN}✓ Worktree Trunk: Clean & Isolated{t.RESET}  {t.DARK_GRAY}Type /help for command palette{t.RESET}",
            f"{t.DARK_GRAY}─────────────────────────────────────────────────────────────────{t.RESET}",
        ]

        rendered_header = []
        for i in range(max(len(mascot_lines), len(info_lines))):
            m_part = mascot_lines[i] if i < len(mascot_lines) else " " * 13
            i_part = info_lines[i] if i < len(info_lines) else ""
            rendered_header.append(f"{t.AMBER}{m_part}{t.RESET}   {i_part}")

        if tip:
            rendered_header.append(f"\n{t.DIM}{tip}{t.RESET}")

        return "\n".join(rendered_header)

    @classmethod
    def render_status_bar(
        cls,
        worktree_path: str = "~/w/apex.main",
        pr_num: str = "#6",
        port: str = ":16156",
        model_name: str = "Claude 3.7 Sonnet",
        effort: str = "high /effort",
    ) -> str:
        """Renders bottom status bar matching Image 2."""
        t = MascotTheme
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 100)
        
        left = f"{t.GRAY}{worktree_path} _ {pr_num} {port} {model_name}{t.RESET}"
        right = f"{t.DARK_GRAY}Ctrl + <n> New Pane{t.RESET}"

        # Clean lengths for spacing
        import re
        raw_left = re.sub(r"\033\[[0-9;]*m", "", left)
        raw_right = re.sub(r"\033\[[0-9;]*m", "", right)
        spaces = max(2, term_width - len(raw_left) - len(raw_right))

        divider = f"{t.DARK_GRAY}{'─' * term_width}{t.RESET}"
        status_line = f"{left}{' ' * spaces}{right}"
        return f"{divider}\n{status_line}"
