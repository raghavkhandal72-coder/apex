from __future__ import annotations

import time
from typing import Dict, List

from .evaluator.consensus import synthesize_consensus
from .evaluator.runtime_eval import evaluate_runtime
from .evaluator.security_eval import evaluate_security
from .models import CodeSubmission, CouncilResult, Critique, EvaluationScore, ModelProvider
from .providers.factory import get_providers


class CouncilEngine:
    def __init__(self, force_offline: bool = False):
        self.providers = get_providers(force_offline=force_offline)

    def convene_council(self, task_prompt: str, test_harness: str = "") -> CouncilResult:
        start_time = time.perf_counter()

        # Step 1: Parallel Code Generation
        submissions: Dict[ModelProvider, CodeSubmission] = {}
        for provider_enum, provider_impl in self.providers.items():
            submissions[provider_enum] = provider_impl.generate(task_prompt)

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

        # Step 4: Determine Verdict & Consensus Winner
        winner = max(evaluations.keys(), key=lambda p: evaluations[p].overall_score)

        # Step 5: Synthesize Flaw-Free Consensus Code
        consensus_code = synthesize_consensus(task_prompt, submissions, evaluations, winner)

        total_time_ms = (time.perf_counter() - start_time) * 1000

        verdict_summary = (
            f"{winner.value} earned the highest composite score ({evaluations[winner].overall_score}/100) "
            f"based on automated security auditing ({evaluations[winner].security_score}%), "
            f"runtime verification ({evaluations[winner].execution_time_ms:.1f}ms), "
            f"and peer consensus across all three foundational models."
        )

        return CouncilResult(
            task_prompt=task_prompt,
            submissions=submissions,
            critiques=critiques,
            evaluations=evaluations,
            winner=winner,
            consensus_code=consensus_code,
            verdict_summary=verdict_summary,
            total_time_ms=total_time_ms,
        )
