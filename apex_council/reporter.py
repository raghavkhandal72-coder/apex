from __future__ import annotations

import sys
from typing import Dict

from .models import CouncilResult, ModelProvider

# ANSI formatting
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

PROVIDER_COLORS: Dict[ModelProvider, str] = {
    ModelProvider.GEMINI: f"{BOLD}{BLUE}",
    ModelProvider.CLAUDE: f"{BOLD}{MAGENTA}",
    ModelProvider.OPENAI: f"{BOLD}{GREEN}",
}


class CouncilReporter:
    @staticmethod
    def format_terminal(result: CouncilResult) -> str:
        lines = []
        banner = f"""{BOLD}{CYAN}
    ___    ____  _______  __     ______ ____  __  ___   ____________  __ 
   /   |  / __ \/ ____/ |/ /    / ____// __ \/ / / / | / / ____/  _/ / / 
  / /| | / /_/ / __/  |   /    / /    / / / / / / /  |/ / /    / /  / /  
 / ___ |/ ____/ /___ /   |    / /___ / /_/ / /_/ / /|  / /____/ /  / /___
/_/  |_/_/   /_____//_/|_|    \____/ \____/\____/_/ |_/\____/___/ /_____/
{RESET}{DIM}   Google Gemini  ×  Anthropic Claude  ×  OpenAI / Microsoft  [v1.0.0]{RESET}"""
        lines.append(banner)
        lines.append(f"{BOLD}{CYAN}========================================================================{RESET}\n")

        lines.append(f"{BOLD}🎯 Task Prompt:{RESET} {YELLOW}\"{result.task_prompt}\"{RESET}\n")

        # Head-to-Head Scoreboard Table
        lines.append(f"{BOLD}📊 HEAD-TO-HEAD SCOREBOARD{RESET}")
        lines.append("-" * 75)
        lines.append(
            f"{'Model Provider':<22} | {'Security':<10} | {'Peer Review':<12} | {'Runtime':<10} | {'Overall Score'}"
        )
        lines.append("-" * 75)

        for provider, score in result.evaluations.items():
            color = PROVIDER_COLORS.get(provider, WHITE)
            sub = result.submissions[provider]
            name_display = f"{color}{provider.value[:20]}{RESET}"
            sec_display = f"{GREEN}{score.security_score:.0f}%{RESET}" if score.security_score >= 80 else f"{RED}{score.security_score:.0f}%{RESET}"
            peer_display = f"{YELLOW}{score.peer_review_avg:.1f} / 10{RESET}"
            runtime_display = f"{score.execution_time_ms:.1f} ms"
            overall_display = f"{BOLD}{score.overall_score:.1f} / 100{RESET}"

            lines.append(
                f"{name_display:<31} | {sec_display:<19} | {peer_display:<21} | {runtime_display:<10} | {overall_display}"
            )

        lines.append("-" * 75)
        lines.append("")

        # Peer Critique Highlights
        lines.append(f"{BOLD}🔍 PEER-REVIEW CROSS EXAMINATION HIGHLIGHTS{RESET}")
        for crit in result.critiques:
            rev_color = PROVIDER_COLORS.get(crit.reviewer, WHITE)
            tgt_color = PROVIDER_COLORS.get(crit.target, WHITE)
            lines.append(
                f"  • {rev_color}{crit.reviewer.value}{RESET} critiqued {tgt_color}{crit.target.value}{RESET}: "
                f"{DIM}Score {crit.score}/10{RESET} - {crit.feedback}"
            )
            for flaw in crit.identified_flaws:
                lines.append(f"    {RED}↳ {flaw}{RESET}")
        lines.append("")

        # Winner Verdict
        winner_color = PROVIDER_COLORS.get(result.winner, GREEN)
        lines.append(f"{BOLD}{CYAN}========================================================================{RESET}")
        lines.append(f"{BOLD}🏆 COUNCIL VERDICT & WINNER:{RESET} {winner_color}{result.winner.value}{RESET}")
        lines.append(f"  {result.verdict_summary}")
        lines.append(f"  {DIM}Total Council Deliberation Time: {result.total_time_ms:.1f} ms{RESET}")
        lines.append(f"{BOLD}{CYAN}========================================================================{RESET}\n")

        # Synthesized Consensus Code
        lines.append(f"{BOLD}{GREEN}✨ SYNTHESIZED FLAW-FREE CONSENSUS CODE (Ready to Use):{RESET}")
        lines.append("-" * 75)
        lines.append(result.consensus_code)
        lines.append("-" * 75)

        return "\n".join(lines)

    @staticmethod
    def format_markdown(result: CouncilResult) -> str:
        md = []
        md.append("# 🏛️ Apex-Council Code Deliberation Report\n")
        md.append(f"> **Task:** `{result.task_prompt}`\n")
        md.append(f"**Deliberation Duration:** `{result.total_time_ms:.1f} ms` | **Consensus Winner:** 🏆 **{result.winner.value}**\n")

        md.append("## 📊 Head-to-Head Scoreboard\n")
        md.append("| Provider | Model | Security Audit | Peer Review | Runtime | Overall Score |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        for provider, score in result.evaluations.items():
            sub = result.submissions[provider]
            winner_badge = " 🏆" if provider == result.winner else ""
            md.append(
                f"| **{provider.value}**{winner_badge} | `{sub.model_name}` | `{score.security_score:.0f}%` | `{score.peer_review_avg:.1f}/10` | `{score.execution_time_ms:.1f}ms` | **`{score.overall_score:.1f}`** |"
            )

        md.append("\n## 🔍 Cross-Critique Matrix\n")
        for crit in result.critiques:
            md.append(f"- **{crit.reviewer.value}** on **{crit.target.value}** (`{crit.score}/10`): {crit.feedback}")
            for flaw in crit.identified_flaws:
                md.append(f"  - ⚠️ *{flaw}*")

        md.append(f"\n## 🏆 Final Verdict\n> {result.verdict_summary}\n")
        md.append("## ✨ Synthesized Flaw-Free Consensus Code\n")
        md.append("```python\n" + result.consensus_code + "\n```")

        return "\n".join(md)
