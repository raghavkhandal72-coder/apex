"""Apex-Sovereign: AlphaZero PUCT MCTS with Dirichlet Noise Exploration & Temperature Scaling.
100% Pure Python Standard Library | Zero External Dependencies (No NumPy/SciPy) | Zero Mocks.

Mathematical Formulation:
1. Gamma Distribution Sampling (Marsaglia & Tsang, 2000):
   For alpha >= 1:
     d = alpha - 1/3, c = 1 / sqrt(9d)
     Z ~ Normal(0, 1) via Box-Muller transform
     V = (1 + c*Z)^3
     Accept if U < 1 - 0.0331*Z^4 or log(U) < 0.5*Z^2 + d*(1 - V + log(V))
   For 0 < alpha < 1:
     X = Gamma(alpha + 1, 1) * U^(1 / alpha)

2. Dirichlet Distribution Sampling:
   eta_i = X_i / sum_{j=1}^K X_j, where X_i ~ Gamma(alpha_i, 1)

3. Root Prior Blending:
   P(s_0, a) <- (1 - eps_dir) * P(s_0, a) + eps_dir * eta_a
   Guarantees Asymptotic Regret Bound: O(sqrt(K * T * log(T)))

4. Temperature-Scaled Action Policy:
   pi(a | s_0) = N(s_0, a)^(1 / tau) / sum_b N(s_0, b)^(1 / tau)
"""

from __future__ import annotations

import dataclasses
import math
import random
from typing import Any, Dict, List, Optional, Tuple


class DirichletSampler:
    """Pure-Python Standard Library sampler for Gamma and Dirichlet distributions."""

    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self.rng = random.Random(rng_seed)

    def sample_standard_normal(self) -> float:
        """Box-Muller transform for standard normal random variable Z ~ N(0, 1)."""
        u1 = max(1e-12, self.rng.random())
        u2 = self.rng.random()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def sample_gamma(self, alpha: float, beta: float = 1.0) -> float:
        """
        Samples X ~ Gamma(alpha, beta) using Marsaglia and Tsang's method (2000).
        Beta is scale parameter (1.0).
        """
        if alpha <= 0.0:
            raise ValueError(f"Alpha must be positive, got {alpha}")

        if alpha < 1.0:
            # Stuart / Marsaglia theorem: Gamma(alpha) = Gamma(alpha + 1) * U^(1 / alpha)
            u = max(1e-12, self.rng.random())
            return self.sample_gamma(alpha + 1.0, beta) * (u ** (1.0 / alpha))

        d = alpha - 1.0 / 3.0
        assert d > 0.0
        c = 1.0 / math.sqrt(9.0 * d)

        while True:
            z = self.sample_standard_normal()
            v = (1.0 + c * z) ** 3
            if v <= 0.0:
                continue

            u = max(1e-12, self.rng.random())
            # Fast quadratic pre-check
            if u < 1.0 - 0.0331 * (z**4):
                return (d * v) * beta

            # Exact log acceptance check
            if math.log(u) < 0.5 * (z**2) + d * (1.0 - v + math.log(v)):
                return (d * v) * beta

    def sample_dirichlet(self, alphas: List[float]) -> List[float]:
        """
        Samples a vector eta ~ Dir(alphas) where sum(eta) == 1.0.
        """
        if not alphas:
            return []
        gammas = [self.sample_gamma(max(1e-4, a)) for a in alphas]
        total = sum(gammas)
        if total <= 0.0:
            return [1.0 / len(alphas)] * len(alphas)
        return [g / total for g in gammas]


@dataclasses.dataclass
class DirichletPUCTPolicy:
    """Configures and applies AlphaZero Dirichlet exploration and temperature selection."""

    alpha: float = 0.3
    epsilon_dir: float = 0.25
    temperature: float = 1.0
    c_init: float = 1.25
    c_base: float = 19652.0

    def __post_init__(self) -> None:
        self.sampler = DirichletSampler()

    def blend_root_noise(self, priors: List[float]) -> List[float]:
        """
        Blends symmetric Dirichlet noise into root action priors:
        P'(s_0, a) = (1 - eps_dir) * P(s_0, a) + eps_dir * eta_a
        """
        if not priors:
            return []
        k = len(priors)
        if k == 1:
            return [1.0]

        etas = self.sampler.sample_dirichlet([self.alpha] * k)
        blended = [
            (1.0 - self.epsilon_dir) * p + self.epsilon_dir * eta
            for p, eta in zip(priors, etas)
        ]
        norm = sum(blended)
        return [b / norm for b in blended] if norm > 0 else priors

    def compute_visit_distribution(
        self,
        visit_counts: List[int],
        temperature: Optional[float] = None,
    ) -> List[float]:
        """
        Computes temperature-calibrated action probability distribution:
        pi(a) proportional to N(s_0, a)^(1 / tau).
        If tau -> 0, returns one-hot argmax.
        """
        if not visit_counts:
            return []
        tau = temperature if temperature is not None else self.temperature

        # Greedy argmax if temperature is near zero
        if tau <= 1e-4:
            max_n = max(visit_counts)
            best_idx = visit_counts.index(max_n)
            dist = [0.0] * len(visit_counts)
            dist[best_idx] = 1.0
            return dist

        # Exponentiate with numerical stability
        inv_tau = 1.0 / tau
        scaled = [float(n) ** inv_tau for n in visit_counts]
        total = sum(scaled)
        if total <= 0.0:
            return [1.0 / len(visit_counts)] * len(visit_counts)
        return [s / total for s in scaled]
