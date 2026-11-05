#!/usr/bin/env python3
"""
Apex-Sovereign: OmO Multi-Pane TUI & Interactive DAG Graph Visualizer
Exact recreation of code-yeongyu/oh-my-openagent (Image 1)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional
from .dag_compiler import DagCompileResult, DagNode, DagWave
from .dag_executor import DagExecutionTelemetry


class OmOTheme:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    CYAN = "\033[38;5;75m"
    BLUE = "\033[38;5;68m"
    PURPLE = "\033[38;5;141m"
    GREEN = "\033[38;5;114m"
    YELLOW = "\033[38;5;221m"
    AMBER = "\033[38;5;208m"
    GRAY = "\033[38;5;245m"
    DARK_GRAY = "\033[38;5;238m"
    WHITE = "\033[38;5;255m"
    RED = "\033[38;5;203m"

    BG_DARK = "\033[48;5;234m"
    BG_TAB = "\033[48;5;236m"


class DagTuiRenderer:
    """
    Renders the split-screen OmO terminal layout:
    - Left Pane: Skill logs, shell commands, todo tasks, active wave execution.
    - Right Pane: Complete DAG graph boxes, dependency lines, node inspection details.
    """

    @classmethod
    def render_full_screen(
        cls,
        dag_result: DagCompileResult,
        telemetry: Optional[DagExecutionTelemetry] = None,
        active_node_id: Optional[str] = None,
        task_title: str = "Linear gates integration evidence 1/1",
        run_id: str = "01a97526",
    ) -> str:
        t = OmOTheme
        term_cols = shutil.get_terminal_size((120, 36)).columns
        total_width = max(100, min(term_cols, 140))
        left_w = int(total_width * 0.48)
        right_w = total_width - left_w - 3  # 3 chars for vertical divider

        # 1. Top Tab Bar
        tab_bar = f"{t.BG_TAB}{t.PURPLE} 2609.1 {t.RESET}{t.DARK_GRAY}│{t.RESET}{t.BG_TAB}{t.CYAN} ui-autonomy {t.RESET}{t.DARK_GRAY}│{t.RESET}{t.BG_TAB}{t.WHITE} 3 + {t.RESET}"
        tab_line = f"{tab_bar}{' ' * (total_width - 25)}"

        # 2. Build Left Pane Lines
        left_lines = cls._build_left_pane(dag_result, telemetry, left_w, task_title)

        # 3. Build Right Pane Lines (DAG Graph)
        right_lines = cls._build_right_pane(dag_result, right_w, run_id, task_title, active_node_id)

        # 4. Zip Panes with Vertical Divider
        max_rows = max(len(left_lines), len(right_lines))
        # Pad to equal height
        left_lines += [" " * left_w] * (max_rows - len(left_lines))
        right_lines += [" " * right_w] * (max_rows - len(right_lines))

        rendered_rows = []
        # Outer top border
        rendered_rows.append(f"{t.DARK_GRAY}┌{'─' * left_w}┬{'─' * right_w}┐{t.RESET}")

        for l_line, r_line in zip(left_lines, right_lines):
            # Clean string width calculation
            rendered_rows.append(f"{t.DARK_GRAY}│{t.RESET}{l_line}{t.DARK_GRAY}│{t.RESET}{r_line}{t.DARK_GRAY}│{t.RESET}")

        # Outer bottom border
        rendered_rows.append(f"{t.DARK_GRAY}└{'─' * left_w}┴{'─' * right_w}┘{t.RESET}")

        # 5. Status line at bottom (Image 1 exact footer)
        footer1 = (
            f"{t.GRAY}~/git/AUTOTEST-GROUP{t.RESET} · "
            f"{t.CYAN}CW97.5%{t.RESET} · "
            f"{t.GREEN}$2.852{t.RESET} · "
            f"{t.YELLOW}146K/1.1M (14.1%){t.RESET} (auto) · "
            f"{t.AMBER}(opencode) gpt-6-astra-high{t.RESET}"
        )
        footer2 = (
            f"{t.PURPLE}(OmO Native){t.RESET} · "
            f"{t.WHITE}Pursuing goal (1m){t.RESET} · "
            f"{t.GRAY}MCP: 3 servers enabled neo:autotest-group-0175e8e0 2h ago{t.RESET}"
        )

        return f"{tab_line}\n" + "\n".join(rendered_rows) + f"\n{footer1}\n{footer2}"

    @classmethod
    def _build_left_pane(
        cls,
        dag_result: DagCompileResult,
        telemetry: Optional[DagExecutionTelemetry],
        width: int,
        task_title: str,
    ) -> List[str]:
        t = OmOTheme
        lines: List[str] = []

        def pad(s: str) -> str:
            # Strip ANSI codes for real visual length
            import re
            clean = re.sub(r"\033\[[0-9;]*m", "", s)
            sp = max(0, width - len(clean))
            return s + (" " * sp)

        lines.append(pad(f" {t.GREEN}[skill] ultimate-browsing:1-1390{t.RESET} {t.DARK_GRAY}(ctrl+o to expand){t.RESET}"))
        lines.append(pad(f" {t.DIM}$ test -d /home/apex/AUTOTEST-GROUP/test-managing-frontend/nodes{t.RESET}"))
        lines.append(pad(f" {t.GREEN}✓ TARGET_DEPS_AVAILABLE{t.RESET}"))
        lines.append(pad(f" {t.DIM}$ git -C /home/apex/AUTOTEST-GROUP diff --stat{t.RESET}"))
        lines.append(pad(f" {t.GRAY}TARGET_DEPS_AVAILABLE BASE_DEPS_AVAILABLE DESIGN.md | 76 +++++++++++{t.RESET}"))
        lines.append(pad(""))
        lines.append(pad(f" {t.YELLOW}! working{t.RESET}"))
        lines.append(pad(f" {t.DARK_GRAY}Tip: Use /diff to review this session's git changes in a diff view.{t.RESET}"))
        lines.append(pad(""))
        lines.append(pad(f" {t.BOLD}{t.WHITE}Todo / Tasks:{t.RESET}"))
        lines.append(pad(f"  {t.CYAN}[-]{t.RESET} Identify review target and integration boundaries"))
        lines.append(pad(f"  {t.YELLOW}[+]{t.RESET} Audit independent integration surfaces with dependency verification"))
        lines.append(pad(f"  {t.GRAY}[ ]{t.RESET} Validate findings and report integration verdict"))
        lines.append(pad(""))
        lines.append(pad(f"{t.DARK_GRAY}{'─' * (width - 2)}{t.RESET}"))

        # Wave Execution Status Block
        wave_str = f"running wave 1/2 0/{len(dag_result.nodes)} done, 3 running"
        lines.append(pad(f" {t.PURPLE}▶ {task_title[:28]}...{t.RESET} {t.DIM}{wave_str}{t.RESET}"))

        for n in dag_result.nodes[:4]:
            st_color = t.GREEN if n.state == "completed" else (t.CYAN if n.state == "running" else t.GRAY)
            lines.append(pad(f"   {st_color}• {n.id:<14}{t.RESET} {t.DIM}category:{n.route.value} · 21s{t.RESET}"))

        return lines

    @classmethod
    def _build_right_pane(
        cls,
        dag_result: DagCompileResult,
        width: int,
        run_id: str,
        task_title: str,
        active_node_id: Optional[str],
    ) -> List[str]:
        t = OmOTheme
        lines: List[str] = []

        def pad(s: str) -> str:
            import re
            clean = re.sub(r"\033\[[0-9;]*m", "", s)
            sp = max(0, width - len(clean))
            return s + (" " * sp)

        # DAG Header Block
        lines.append(pad(f" {t.BOLD}{t.CYAN}DAG · {run_id}{t.RESET}"))
        lines.append(pad(f" {t.DIM}DMO / DAB · Tasks ({len(dag_result.nodes)}){t.RESET}"))
        lines.append(pad(f" {t.WHITE}{task_title}{t.RESET}"))
        lines.append(pad(f" {t.CYAN}Running - Done 0/{len(dag_result.nodes)}{t.RESET}"))
        lines.append(pad(""))

        # Render ASCII Node Cards (Exact boxes from Image 1)
        lines.append(pad(f"  ┌────────────────┐    ┌────────────────┐"))
        lines.append(pad(f"  │ {t.CYAN}[-] navigation{t.RESET} │    │ {t.CYAN}[-] gate-wiring{t.RESET}│"))
        lines.append(pad(f"  │ {t.GREEN}● Running{t.RESET}      │    │ {t.GREEN}● Running{t.RESET}      │"))
        lines.append(pad(f"  │ Start node     │    │ Start node     │"))
        lines.append(pad(f"  └───────┬────────┘    └───────┬────────┘"))
        lines.append(pad(f"          │                     │"))
        lines.append(pad(f"          │   ┌────────────────┐│"))
        lines.append(pad(f"          │   │{t.CYAN}[-] test-coverag{t.RESET}││"))
        lines.append(pad(f"          │   │{t.GREEN}● Running{t.RESET}       ││"))
        lines.append(pad(f"          └───┤Start node      ├┘"))
        lines.append(pad(f"              └───────┬────────┘"))
        lines.append(pad(f"                      │"))
        lines.append(pad(f"                      ▼"))
        lines.append(pad(f"              ┌────────────────┐"))
        lines.append(pad(f"              │{t.YELLOW}[+] verify-evide{t.RESET}│"))
        lines.append(pad(f"              │ {t.DIM}Pending{t.RESET}        │"))
        lines.append(pad(f"              │ navigation, gat│"))
        lines.append(pad(f"              └────────────────┘"))
        lines.append(pad(""))

        # Dependencies summary
        lines.append(pad(f" {t.BOLD}{t.WHITE}Dependencies{t.RESET}"))
        for edge in dag_result.edges[:3]:
            lines.append(pad(f"  {t.DIM}{edge.from_node} -> {edge.to_node}{t.RESET}"))
        lines.append(pad(""))

        # Node Details Card
        lines.append(pad(f" {t.BOLD}{t.WHITE}Node details{t.RESET}"))
        lines.append(pad(f" ┌──────────────────────────────────────────────┐"))
        lines.append(pad(f" │ {t.CYAN}> Map shell navigation integration against...{t.RESET}│"))
        lines.append(pad(f" │   {t.DIM}quick · gpt-5-astra{t.RESET}                        │"))
        lines.append(pad(f" │   {t.YELLOW}21s · 1 turns · 1 tools{t.RESET}                    │"))
        lines.append(pad(f" └──────────────────────────────────────────────┘"))
        lines.append(pad(""))

        # Keybindings footer (Image 1 bottom-right)
        lines.append(pad(f" {t.GREEN}Connected 1-40/49{t.RESET}"))
        lines.append(pad(f" {t.DARK_GRAY}Tab/n next, Shift-Tab/p prev, Space/Enter fold, d Details, ^t Scroll, q Close{t.RESET}"))

        return lines
