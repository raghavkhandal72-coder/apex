from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from .context import load_project_context
from .evaluator.consensus import synthesize_consensus
from .evaluator.runtime_eval import evaluate_runtime
from .evaluator.security_eval import evaluate_security
from .models import CodeSubmission, CouncilResult, Critique, EvaluationScore, ModelProvider
from .providers.factory import get_providers


class CouncilEngine:
    def __init__(self, force_offline: bool = False, strict: bool = False):
        self.force_offline = force_offline
        self.strict = strict
        self.providers = get_providers(force_offline=force_offline, strict=strict)

    def convene_council(self, task_prompt: str, test_harness: str = "") -> CouncilResult:
        """Runs the Competitive Head-to-Head Council deliberation."""
        start_time = time.perf_counter()

        # Enrich prompt with local repository guidelines (AGENTS.md / CLAUDE.md) if present
        repo_ctx = load_project_context(".")
        full_prompt = f"{task_prompt}\n\n[Context]\n{repo_ctx}" if repo_ctx else task_prompt

        # Step 1: Parallel Code Generation
        submissions: Dict[ModelProvider, CodeSubmission] = {}
        for provider_enum, provider_impl in self.providers.items():
            submissions[provider_enum] = provider_impl.generate(full_prompt)

        # Step 2: Cross-Examination (Peer Review Matrix)
        critiques: List[Critique] = []
        peer_scores: Dict[ModelProvider, List[float]] = {p: [] for p in self.providers}

        for reviewer_enum, reviewer_impl in self.providers.items():
            for target_enum, target_sub in submissions.items():
                if reviewer_enum != target_enum:
                    crit = reviewer_impl.critique(target_enum, target_sub.code, task_prompt)
                    critiques.append(crit)
                    peer_scores[target_enum].append(crit.score)

        # Step 3: Automated Security & Runtime Evaluation
        evaluations: Dict[ModelProvider, EvaluationScore] = {}
        for provider_enum, sub in submissions.items():
            sec_score, sec_issues = evaluate_security(sub.code)
            syntax_ok, runtime_ok, exec_ms, err = evaluate_runtime(sub.code, test_harness)

            avg_peer = sum(peer_scores[provider_enum]) / len(peer_scores[provider_enum]) if peer_scores[provider_enum] else 8.0

            score = EvaluationScore(
                security_score=sec_score,
                security_issues=sec_issues,
                syntax_valid=syntax_ok,
                runtime_passed=runtime_ok,
                execution_time_ms=exec_ms,
                peer_review_avg=avg_peer,
            )
            score.compute_overall()
            evaluations[provider_enum] = score

        # Step 4: Determine Verdict & Consensus Mode
        live_subs = [p for p, s in submissions.items() if not getattr(s, "is_simulated", False)]
        live_count = len(live_subs)

        if live_count >= 2:
            consensus_mode = "multi_live_consensus"
            for p, ev in evaluations.items():
                ev.is_ranked = (p in live_subs)
            ranked_evals = {p: ev for p, ev in evaluations.items() if ev.is_ranked}
            winner = max(ranked_evals.keys(), key=lambda p: ranked_evals[p].overall_score)
            verdict_summary = (
                f"{winner.value} [LIVE] earned the highest composite score ({evaluations[winner].overall_score}/100) "
                f"in live multi-model cross-examination across {live_count} foundational models. "
                f"Security audit: {evaluations[winner].security_score:.0f}%, "
                f"Runtime: {evaluations[winner].execution_time_ms:.1f}ms."
            )
        elif live_count == 1:
            consensus_mode = "single_live_fallback"
            winner = live_subs[0]
            for p, ev in evaluations.items():
                ev.is_ranked = (p == winner)
            verdict_summary = (
                f"Synthesized from {winner.value} (Sole active live foundation model). "
                f"Peer models were simulated fallbacks (UNRANKED); true multi-agent consensus requires >= 2 live providers."
            )
        else:
            consensus_mode = "offline_simulation"
            for p, ev in evaluations.items():
                ev.is_ranked = True
            winner = max(evaluations.keys(), key=lambda p: evaluations[p].overall_score)
            verdict_summary = (
                f"{winner.value} selected by offline benchmark heuristic ({evaluations[winner].overall_score}/100). "
                f"Full offline simulation mode (zero API keys detected)."
            )

        # Step 5: Synthesize Flaw-Free Consensus Code
        consensus_code = synthesize_consensus(task_prompt, submissions, evaluations, winner)

        total_time_ms = (time.perf_counter() - start_time) * 1000

        return CouncilResult(
            task_prompt=task_prompt,
            submissions=submissions,
            critiques=critiques,
            evaluations=evaluations,
            winner=winner,
            consensus_code=consensus_code,
            verdict_summary=verdict_summary,
            total_time_ms=total_time_ms,
            live_providers_count=live_count,
            consensus_mode=consensus_mode,
        )

    def audit_file(self, file_path: Path | str) -> Dict[str, Any]:
        """Audits an existing codebase file using the full Council."""
        target_path = Path(file_path).resolve()
        content = target_path.read_text(encoding="utf-8", errors="ignore")

        # Static security pre-check
        sec_score, sec_issues = evaluate_security(content)

        # Prompt council to review and remediate
        audit_prompt = (
            f"Audit and refactor this file for production security, clean typing, and bug fixes.\n\n"
            f"File: {target_path.name}\n```\n{content}\n```"
        )
        council_result = self.convene_council(audit_prompt)

        return {
            "file_path": str(target_path),
            "original_security_score": sec_score,
            "original_security_issues": sec_issues,
            "council_result": council_result,
        }

    def collaborative_relay(self, prompt: str) -> Dict[str, Any]:
        """Collaborative Relay Pipeline:

        Gemini (Architecture) -> Claude (Implementation & Safeguards) -> OpenAI (Unit Tests)
        """
        start = time.perf_counter()

        # Step 1: Gemini Architecture
        gemini_sub = self.providers[ModelProvider.GEMINI].generate(f"Design the architecture and data structures for: {prompt}")

        # Step 2: Claude Implementation
        claude_sub = self.providers[ModelProvider.CLAUDE].generate(
            f"Implement defensive production logic based on this architecture:\n{gemini_sub.code}\nGoal: {prompt}"
        )

        # Step 3: OpenAI Unit Tests
        openai_sub = self.providers[ModelProvider.OPENAI].generate(
            f"Write a comprehensive unit test suite using unittest for this code:\n{claude_sub.code}"
        )

        total_time_ms = (time.perf_counter() - start) * 1000

        combined_code = (
            f'"""Apex-Council Collaborative Relay Pipeline Output\n'
            f'Architect: Google Gemini | Implementer: Anthropic Claude | QA Engineer: OpenAI\n'
            f'"""\n\n'
            f"# === IMPLEMENTATION (Anthropic Claude & Google Gemini) ===\n"
            f"{claude_sub.code}\n\n"
            f"# === VERIFICATION SUITE (OpenAI) ===\n"
            f"{openai_sub.code}\n"
        )

        return {
            "task_prompt": prompt,
            "architecture": gemini_sub.code,
            "implementation": claude_sub.code,
            "tests": openai_sub.code,
            "combined_code": combined_code,
            "total_time_ms": total_time_ms,
        }
