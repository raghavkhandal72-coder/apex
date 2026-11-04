"""Flight Recorder Replay Streamer.
Renders pre-recorded autonomous bug resolution sessions in Cyberpunk ANSI styling
with zero external dependencies and zero API key requirements.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from apex_council.ui.terminal import CyberpunkTUI, TerminalColors


DEFAULT_DEMO_PATH = Path(__file__).resolve().parent.parent.parent / ".apex" / "demos" / "sqlite_deadlock_fix.jsonl"


class FlightRecorderReplay:
    """Streams an autonomous flight-recorder session to the terminal."""

    @classmethod
    def run_replay(cls, demo_path: Optional[Path | str] = None, delay_sec: float = 0.35) -> None:
        c = TerminalColors
        target = Path(demo_path) if demo_path else DEFAULT_DEMO_PATH

        print(CyberpunkTUI.render_banner())
        print(f"\n{c.GOLD}{c.BOLD}[FLIGHT RECORDER] Starting Zero-API-Key Offline Swarm Replay...{c.RESET}\n")
        time.sleep(delay_sec)

        if not target.exists():
            print(f"{c.RED}Demo file not found at: {target}{c.RESET}")
            return

        with open(target, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                step_data = json.loads(line)
                cls._render_step(step_data, delay_sec)

        print(f"\n{c.NEON_GREEN}{c.BOLD}✓ FLIGHT RECORDER REPLAY COMPLETE: 100% Offline Autonomous Resolution.{c.RESET}\n")

    @classmethod
    def _render_step(cls, step: Dict[str, Any], delay_sec: float) -> None:
        c = TerminalColors
        step_num = step.get("step", 1)
        phase = step.get("phase", "")
        title = step.get("title", "")
        details = step.get("details", "")

        color_map = {
            "REPOMAP": c.CYAN,
            "STAFF_ARCHITECT": c.MAGENTA,
            "TEST_FIRST_SPECULATOR": c.ORANGE,
            "MCTS_SEARCH": c.CYAN,
            "RED_TEAM_BREAKER": c.RED,
            "GATEKEEPER_SIGN": c.NEON_GREEN,
            "DIFF_STREAM": c.GOLD,
        }
        color = color_map.get(phase, c.CYAN)

        print(f"{color}{c.BOLD}▶ STEP {step_num}/7: {title}{c.RESET}")
        
        if phase == "DIFF_STREAM":
            diff_text = step.get("diff", "")
            for line in diff_text.splitlines():
                if line.startswith("+++") or line.startswith("---"):
                    print(f"  {c.BOLD}{line}{c.RESET}")
                elif line.startswith("@@"):
                    print(f"  {c.CYAN}{line}{c.RESET}")
                elif line.startswith("+"):
                    print(f"  {c.NEON_GREEN}{line}{c.RESET}")
                elif line.startswith("-"):
                    print(f"  {c.RED}{line}{c.RESET}")
                else:
                    print(f"  {c.DARK_GRAY}{line}{c.RESET}")
        else:
            for d_line in details.splitlines():
                print(f"  {c.DARK_GRAY}│{c.RESET} {d_line}")

        if "hubs" in step:
            for h in step["hubs"]:
                print(f"  {c.CYAN}• Architectural Hub:{c.RESET} {h}")

        print("")
        time.sleep(delay_sec)
