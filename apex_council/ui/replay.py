"""Flight Recorder Replay Streamer and Standalone Single-File HTML Report Generator.
Renders pre-recorded autonomous bug resolution sessions in Cyberpunk ANSI styling
and exports self-contained audit reports with zero external dependencies.
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from apex_council.ui.terminal import CyberpunkTUI, TerminalColors


DEFAULT_DEMO_PATH = Path(__file__).resolve().parent.parent.parent / ".apex" / "demos" / "sqlite_deadlock_fix.jsonl"


class HTMLReportGenerator:
    """Generates an airtight, zero-external-dependency, single-file HTML audit report."""

    @staticmethod
    def generate_report(
        title: str,
        task_prompt: str,
        target_file: str,
        diff_text: str,
        is_passing: bool,
        merkle_root: str = "N/A",
        signature: str = "N/A",
        duration_ms: float = 0.0,
        mcts_nodes: int = 0,
        mutation_score: float = 100.0,
        output_path: Optional[Path | str] = None,
    ) -> str:
        escaped_title = html.escape(title)
        escaped_task = html.escape(task_prompt)
        escaped_file = html.escape(target_file)
        status_color = "#3fb950" if is_passing else "#f85149"
        status_text = "PASSED & SIGNED" if is_passing else "VALIDATION FAILED"

        # Format diff lines with colored span tags
        formatted_diff_lines: List[str] = []
        for line in diff_text.splitlines():
            esc_line = html.escape(line)
            if line.startswith("+++") or line.startswith("---"):
                formatted_diff_lines.append(f'<span class="diff-header">{esc_line}</span>')
            elif line.startswith("@@"):
                formatted_diff_lines.append(f'<span class="diff-chunk">{esc_line}</span>')
            elif line.startswith("+"):
                formatted_diff_lines.append(f'<span class="diff-add">{esc_line}</span>')
            elif line.startswith("-"):
                formatted_diff_lines.append(f'<span class="diff-del">{esc_line}</span>')
            else:
                formatted_diff_lines.append(f'<span class="diff-ctx">{esc_line}</span>')

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Apex-Sovereign Audit: {escaped_title}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --gold: #d29922;
            --neon: #3fb950;
            --danger: #f85149;
            --font-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            padding: 32px 24px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 6px solid {status_color};
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        h1 {{ font-size: 24px; color: #fff; margin-bottom: 8px; font-family: var(--font-mono); }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            background: {status_color}22;
            color: {status_color};
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 12px;
            border: 1px solid {status_color};
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .card-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }}
        .card-value {{ font-size: 18px; font-weight: 700; color: #fff; font-family: var(--font-mono); }}
        .section-title {{ font-size: 18px; color: #fff; margin: 24px 0 12px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
        .diff-container {{
            background: #040d21;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
            font-family: var(--font-mono);
            font-size: 13px;
            white-space: pre;
            line-height: 1.5;
        }}
        .diff-header {{ color: var(--text-muted); font-weight: 700; }}
        .diff-chunk {{ color: var(--accent); }}
        .diff-add {{ color: #7ee787; background: #23863622; display: block; }}
        .diff-del {{ color: #ffa198; background: #da363322; display: block; }}
        .diff-ctx {{ color: var(--text-muted); display: block; }}
        .hash-code {{
            background: #010409;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--accent);
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="badge">{status_text}</span>
            <h1>🏛️ Apex-Sovereign Autonomous Verification Receipt</h1>
            <p style="color: var(--text-muted); font-size: 14px;">Task: {escaped_task}</p>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-label">Target File</div>
                <div class="card-value" style="font-size: 14px;">{escaped_file}</div>
            </div>
            <div class="card">
                <div class="card-label">MCTS Search Nodes</div>
                <div class="card-value">{mcts_nodes} AST Nodes</div>
            </div>
            <div class="card">
                <div class="card-label">Mutation Kill Score</div>
                <div class="card-value" style="color: #3fb950;">{mutation_score:.1f}%</div>
            </div>
            <div class="card">
                <div class="card-label">Execution Latency</div>
                <div class="card-value">{duration_ms:.1f}ms</div>
            </div>
        </div>

        <div class="section-title">🔒 Cryptographic Attestation & Merkle Proof</div>
        <div class="card" style="margin-bottom: 24px;">
            <div style="margin-bottom: 12px;">
                <div class="card-label">Repository Merkle Root</div>
                <div class="hash-code">{html.escape(merkle_root)}</div>
            </div>
            <div>
                <div class="card-label">Sovereign Gatekeeper HMAC-SHA512 Seal</div>
                <div class="hash-code">{html.escape(signature)}</div>
            </div>
        </div>

        <div class="section-title">📝 Sovereign Code Diff Stream</div>
        <div class="diff-container">{''.join(formatted_diff_lines)}</div>
    </div>
</body>
</html>
"""
        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html_body, encoding="utf-8")

        return html_body


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
