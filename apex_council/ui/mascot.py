#!/usr/bin/env python3
"""
Apex-Sovereign: Iconic Re-Designed Pixel Mascot & Sovereign Aesthetics
Inspired by Claude Code (Image 3) & Worktrunk (Image 2) & OmO (Image 1)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from typing import Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class MascotTheme:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Claude Code classic warm terracotta / amber palette
    AMBER = "\033[38;5;208m"
    PEACH = "\033[38;5;215m"

    # Apex Imperial Sovereign Gold
    APEX_GOLD = "\033[38;5;220m"
    APEX_OBSIDIAN = "\033[38;5;236m"

    # Cyberpunk Neon
    NEON_CYAN = "\033[38;5;45m"
    ELECTRIC_BLUE = "\033[38;5;39m"
    VIOLET = "\033[38;5;141m"

    # Sovereign Emerald
    EMERALD = "\033[38;5;48m"

    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;244m"
    DARK_GRAY = "\033[38;5;238m"
    GREEN = "\033[38;5;114m"
    CYAN = "\033[38;5;75m"
    RED = "\033[38;5;203m"


# ============================================================================
# 1. Flagship Apex Sovereign Cyber-Falcon Mascot (Signature Emblem)
# ============================================================================
APEX_SOVEREIGN_FALCON = [
    "   ▄██████▄   ",
    " ▟███▀▀██▀▀███▙ ",
    " ▐███ █▗▖█ ▐███▌",
    "  ████▄▄▄▄████  ",
    "  ▜██████████▛  ",
    "    ▀██  ██▀    ",
]

# ============================================================================
# 2. Sovereign Crowned Mech-Guardian Mascot (Royal Apex Mech)
# ============================================================================
APEX_CROWNED_GUARDIAN = [
    "  █ █  ██  █ █  ",
    "  ▀█▀██████▀█▀  ",
    "  ████████████  ",
    "  ███▗▖██▗▖███  ",
    "  ██▀▀▀▀▀▀▀▀██  ",
    "   ██      ██   ",
]

# ============================================================================
# 3. Sovereign Aegis Citadel Diamond Mascot
# ============================================================================
APEX_CITADEL_AEGIS = [
    "      ▟██▙      ",
    "    ▟██████▙    ",
    "  ▟███▀██▀███▙  ",
    "  ███ █▗▖█ ███  ",
    "  ▜███▄██▄███▛  ",
    "    ▜██████▛    ",
]

# ============================================================================
# 4. Classic Claude Code Terracotta Sprite (Image 3)
# ============================================================================
APEX_RETRO_SPRITE = [
    "  ▟█▙   ▟█▙  ",
    "  █████████  ",
    "  █▗▖█ █▗▖█  ",
    "  █████████  ",
    "  █▀▀▀▀▀▀▀█  ",
    "   █     █   ",
]

# Aliases for backward compatibility
APEX_PIXEL_MASCOT = APEX_RETRO_SPRITE
APEX_FALCON_MASCOT = APEX_SOVEREIGN_FALCON


class MascotRenderer:
    """Renders the iconic re-designed Apex pixel mascot header, prompt boxes, and status bars."""

    MASCOT_STYLES = {
        "falcon": APEX_SOVEREIGN_FALCON,
        "guardian": APEX_CROWNED_GUARDIAN,
        "aegis": APEX_CITADEL_AEGIS,
        "retro": APEX_RETRO_SPRITE,
    }

    THEME_COLORS = {
        "gold": MascotTheme.APEX_GOLD,
        "amber": MascotTheme.AMBER,
        "cyan": MascotTheme.NEON_CYAN,
        "emerald": MascotTheme.EMERALD,
        "violet": MascotTheme.VIOLET,
    }

    @classmethod
    def render_header(
        cls,
        version: str = "v0.9.0",
        model: str = "Claude 3.7 Sonnet · Gemini 2.5 Pro · GPT-4o",
        workspace_path: Optional[str] = None,
        tip: Optional[str] = None,
        style: str = "falcon",
        theme_name: str = "gold",
    ) -> str:
        """
        Renders the iconic pixel mascot header matching Image 3 with Apex re-branding.
        """
        t = MascotTheme
        cwd = workspace_path or os.getcwd()
        if len(cwd) > 42:
            cwd = "..." + cwd[-39:]

        mascot_lines = cls.MASCOT_STYLES.get(style, APEX_SOVEREIGN_FALCON)
        accent_color = cls.THEME_COLORS.get(theme_name, t.APEX_GOLD)

        info_lines = [
            f"{t.BOLD}{t.WHITE}Apex {version}{t.RESET}",
            f"{accent_color}{model}{t.RESET}",
            f"{t.GRAY}{cwd}{t.RESET}",
            f"{t.CYAN}★ MCTS PUCT × CEGIS Inductive Synthesis × OmO DAG Waves{t.RESET}",
            f"{t.GREEN}✓ Worktrunk: Isolated & Clean{t.RESET}  {t.DARK_GRAY}Type /help or /omo for interactive TUI{t.RESET}",
            f"{t.DARK_GRAY}──────────────────────────────────────────────────────────────────{t.RESET}",
        ]

        rendered_header = []
        max_rows = max(len(mascot_lines), len(info_lines))
        for i in range(max_rows):
            m_part = mascot_lines[i] if i < len(mascot_lines) else " " * 16
            i_part = info_lines[i] if i < len(info_lines) else ""
            rendered_header.append(f"{accent_color}{m_part}{t.RESET}   {i_part}")

        if tip:
            rendered_header.append(f"\n{t.DIM}{tip}{t.RESET}")

        return "\n".join(rendered_header)

    @classmethod
    def render_status_bar(
        cls,
        worktree_path: str = "~/w/apex.main",
        pr_num: str = "#6",
        port: str = ":16156",
        model_name: str = "Claude 3.7 Sonnet (Apex Supreme)",
        effort: str = "high /effort",
    ) -> str:
        """Renders bottom status bar matching Image 3 & Image 2."""
        t = MascotTheme
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 100)

        left = f"{t.GRAY}{worktree_path} _ {pr_num} {port} {model_name}{t.RESET}"
        right = f"{t.DARK_GRAY}Ctrl + <n> New Pane{t.RESET}"

        raw_left = re.sub(r"\033\[[0-9;]*m", "", left)
        raw_right = re.sub(r"\033\[[0-9;]*m", "", right)
        spaces = max(2, term_width - len(raw_left) - len(raw_right))

        divider = f"{t.DARK_GRAY}{'─' * term_width}{t.RESET}"
        status_line = f"{left}{' ' * spaces}{right}"
        return f"{divider}\n{status_line}"

    @classmethod
    def render_agent_speech(
        cls,
        persona: str,
        speech_lines: List[str],
        status_tag: str = "DELIBERATING",
    ) -> str:
        """
        Renders an agent's speech box side-by-side with its dedicated pixel art mascot.
        """
        t = MascotTheme
        meta = ApexAgentPersona.METADATA.get(persona, ApexAgentPersona.METADATA["commander"])
        style = meta["style"]
        theme_color = cls.THEME_COLORS.get(meta["theme"], t.APEX_GOLD)
        mascot_lines = cls.MASCOT_STYLES.get(style, APEX_SOVEREIGN_FALCON)

        header_badge = f"{theme_color}{meta['icon']} [{meta['title']}]{t.RESET} {t.DIM}· {status_tag}{t.RESET}"

        dialogue_lines = [header_badge]
        for line in speech_lines:
            dialogue_lines.append(f"{t.WHITE}{line}{t.RESET}")

        rendered = []
        max_rows = max(len(mascot_lines), len(dialogue_lines))
        for i in range(max_rows):
            m_part = mascot_lines[i] if i < len(mascot_lines) else " " * 16
            d_part = dialogue_lines[i] if i < len(dialogue_lines) else ""
            rendered.append(f"{theme_color}{m_part}{t.RESET}   {d_part}")

        return "\n".join(rendered)


class ApexAgentPersona:
    """
    Council Agent Persona with dedicated pixel mascot, color theme,
    and voice/role specialization.
    """
    COMMANDER = "commander"   # Apex Sovereign Falcon (Gold) - Strategic Orchestration
    ARCHITECT = "architect"   # Crowned Mech-Guardian (Cyan) - Structure & Invariants
    SENTINEL = "sentinel"     # Citadel Diamond Aegis (Emerald) - Security & Attestation
    NINJA = "ninja"           # Terracotta Sprite (Amber) - Rapid Bug Localization & Edits

    METADATA = {
        "commander": {
            "title": "APEX SUPREME COMMANDER",
            "icon": "★",
            "style": "falcon",
            "theme": "gold",
            "description": "Multi-Model Orchestrator & MCTS Consensus Search Leader",
        },
        "architect": {
            "title": "SYSTEM ARCHITECT & SYNTHESIZER",
            "icon": "⚡",
            "style": "guardian",
            "theme": "cyan",
            "description": "Deterministic AST Synthesizer & Hoare Logic Boundary Prover",
        },
        "sentinel": {
            "title": "SECURITY SENTINEL & BREAKER",
            "icon": "🛡️",
            "style": "aegis",
            "theme": "emerald",
            "description": "Zero-Trust DLP Sanitizer & Cryptographic Merkle Auditor",
        },
        "ninja": {
            "title": "AUTONOMOUS BUG HUNTER & NINJA",
            "icon": "🥷",
            "style": "retro",
            "theme": "amber",
            "description": "Ochiai Fault Localizer & Atomic Git Worktree Sweeper",
        },
    }
