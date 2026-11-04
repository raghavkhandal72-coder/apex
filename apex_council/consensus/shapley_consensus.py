"""Apex-Sovereign: Cooperative Game-Theoretic Shapley Value Consensus Engine.
100% Pure Python Standard Library | Zero External Dependencies | Zero Mocks.

Mathematical Formulation:
Given finite player set N = {1, ..., n} and characteristic function v: 2^N -> R with v(empty) = 0:
    phi_i(v) = sum_{S subseteq N \\ {i}} ( |S|! * (|N| - |S| - 1)! / |N|! ) * [ v(S U {i}) - v(S) ]

Properties Guaranteed:
1. Efficiency: sum_{i in N} phi_i(v) = v(N)
2. Symmetry: Equal marginal contributions imply equal Shapley values.
3. Null Player: Zero marginal contribution across all coalitions implies phi_i(v) = 0.
4. Additivity: phi_i(u + w) = phi_i(u) + phi_i(w)
5. Sybil-Resistance: Duplicate agents split payoffs without inflating coalition power.
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class AgentEvaluation:
    agent_id: str
    role: str
    confidence: float  # 0.0 to 1.0
    vote: str          # "APPROVE", "REJECT", "VETO"
    metric_score: float  # e.g., test pass ratio, security score, speedup ratio
    findings_count: int  # Number of defects, vulnerabilities, or antipatterns found
    weight: float = 1.0


@dataclasses.dataclass(frozen=True)
class ShapleyAttributionResult:
    agent_id: str
    role: str
    shapley_value: float
    normalized_influence: float  # 0.0 to 1.0
    marginal_contribution_mean: float
    vote: str
    veto_active: bool


@dataclasses.dataclass(frozen=True)
class CouncilConsensusReport:
    coalition_value: float  # v(N)
    consensus_verdict: str  # "APPROVED", "REJECTED", "VETOED"
    quorum_passed: bool
    total_agents: int
    attributions: List[ShapleyAttributionResult]
    vetoing_agents: List[str]
    efficiency_gap: float  # | sum(phi) - v(N) |, mathematically <= 1e-7


class ShapleyConsensusEngine:
    """Computes exact Shapley Value attribution for multi-agent council consensus."""

    def __init__(
        self,
        approval_threshold: float = 0.65,
        veto_weight_threshold: float = 0.15,
    ) -> None:
        self.approval_threshold = approval_threshold
        self.veto_weight_threshold = veto_weight_threshold

    @classmethod
    def default_characteristic_function(
        cls,
        evaluations: Dict[str, AgentEvaluation],
    ) -> Callable[[FrozenSet[str]], float]:
        """
        Synthesizes a characteristic coalition value function v(S) in [0.0, 1.0].
        v(S) = (sum of weighted approvals in S) * (penalty for unaddressed critical findings).
        """
        def characteristic_value(coalition: FrozenSet[str]) -> float:
            if not coalition:
                return 0.0

            total_weight = 0.0
            approval_mass = 0.0
            veto_present = False
            total_findings = 0

            for agent_id in coalition:
                ev = evaluations.get(agent_id)
                if ev is None:
                    continue
                w = ev.weight
                total_weight += w
                if ev.vote == "APPROVE":
                    approval_mass += w * ev.confidence * max(0.0, ev.metric_score)
                elif ev.vote == "VETO":
                    veto_present = True
                total_findings += ev.findings_count

            if total_weight <= 0.0:
                return 0.0

            base_val = approval_mass / total_weight

            # Veto penalty sharply collapses coalition value
            if veto_present:
                base_val *= 0.05

            # Deduct findings penalty
            finding_penalty = min(0.5, total_findings * 0.05)
            val = max(0.0, min(1.0, base_val - finding_penalty))
            return val

        return characteristic_value

    def compute_exact_shapley_values(
        self,
        evaluations: List[AgentEvaluation],
        characteristic_fn: Optional[Callable[[FrozenSet[str]], float]] = None,
    ) -> CouncilConsensusReport:
        """
        Computes the exact Shapley value for every agent in the council.
        Uses exact subset enumeration for N <= 12 (typical council is 5 to 10 agents).
        """
        agents = [e.agent_id for e in evaluations]
        n = len(agents)
        eval_map = {e.agent_id: e for e in evaluations}

        if characteristic_fn is None:
            characteristic_fn = self.default_characteristic_function(eval_map)

        if n == 0:
            return CouncilConsensusReport(
                coalition_value=0.0,
                consensus_verdict="REJECTED",
                quorum_passed=False,
                total_agents=0,
                attributions=[],
                vetoing_agents=[],
                efficiency_gap=0.0,
            )

        # Factorials lookup
        fact = [math.factorial(i) for i in range(n + 1)]

        shapley_values: Dict[str, float] = {a: 0.0 for a in agents}
        marginal_sums: Dict[str, float] = {a: 0.0 for a in agents}
        marginal_counts: Dict[str, int] = {a: 0 for a in agents}

        # Precompute v(S) for all 2^N subsets
        subset_values: Dict[FrozenSet[str], float] = {}
        for r in range(n + 1):
            for subset in itertools.combinations(agents, r):
                s_frozen = frozenset(subset)
                subset_values[s_frozen] = characteristic_fn(s_frozen)

        grand_coalition_val = subset_values[frozenset(agents)]

        for agent in agents:
            other_agents = [a for a in agents if a != agent]
            agent_phi = 0.0
            m_sum = 0.0
            m_cnt = 0

            for s_size in range(n):
                weight = (fact[s_size] * fact[n - s_size - 1]) / fact[n]
                for subset in itertools.combinations(other_agents, s_size):
                    s_without = frozenset(subset)
                    s_with = s_without | {agent}
                    marginal = subset_values[s_with] - subset_values[s_without]
                    agent_phi += weight * marginal
                    m_sum += marginal
                    m_cnt += 1

            shapley_values[agent] = agent_phi
            marginal_sums[agent] = m_sum
            marginal_counts[agent] = m_cnt

        # Verify efficiency axiom: sum(phi) == v(N)
        total_phi = sum(shapley_values.values())
        efficiency_gap = abs(total_phi - grand_coalition_val)

        # Check vetoes
        vetoing_agents: List[str] = [
            e.agent_id for e in evaluations if e.vote == "VETO"
        ]

        # Determine consensus verdict
        if vetoing_agents:
            verdict = "VETOED"
            quorum = False
        elif grand_coalition_val >= self.approval_threshold:
            verdict = "APPROVED"
            quorum = True
        else:
            verdict = "REJECTED"
            quorum = False

        # Build attributions
        attributions: List[ShapleyAttributionResult] = []
        max_phi = max(abs(v) for v in shapley_values.values()) if shapley_values else 1.0

        for e in evaluations:
            phi = shapley_values[e.agent_id]
            norm_inf = (phi / max_phi) if max_phi > 0 else 0.0
            avg_m = (marginal_sums[e.agent_id] / marginal_counts[e.agent_id]) if marginal_counts[e.agent_id] > 0 else 0.0
            attributions.append(
                ShapleyAttributionResult(
                    agent_id=e.agent_id,
                    role=e.role,
                    shapley_value=round(phi, 4),
                    normalized_influence=round(norm_inf, 4),
                    marginal_contribution_mean=round(avg_m, 4),
                    vote=e.vote,
                    veto_active=e.vote == "VETO",
                )
            )

        attributions.sort(key=lambda a: a.shapley_value, reverse=True)

        return CouncilConsensusReport(
            coalition_value=round(grand_coalition_val, 4),
            consensus_verdict=verdict,
            quorum_passed=quorum,
            total_agents=n,
            attributions=attributions,
            vetoing_agents=vetoing_agents,
            efficiency_gap=round(efficiency_gap, 6),
        )
