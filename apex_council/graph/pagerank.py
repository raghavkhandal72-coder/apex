"""Directed graph construction and power-iteration Personalized PageRank engine.
Pure Python standard library implementation.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set, Tuple


class PageRankGraph:
    """Directed graph for repository modules and symbol dependencies."""

    def __init__(self) -> None:
        self.nodes: Set[str] = set()
        # Adjacency list: node -> dict of (target_node -> weight)
        self.out_edges: Dict[str, Dict[str, float]] = {}
        self.in_edges: Dict[str, Dict[str, float]] = {}

    def add_node(self, node: str) -> None:
        self.nodes.add(node)
        if node not in self.out_edges:
            self.out_edges[node] = {}
        if node not in self.in_edges:
            self.in_edges[node] = {}

    def add_edge(self, source: str, target: str, weight: float = 1.0) -> None:
        if source == target:
            return  # No self loops for PageRank stability
        self.add_node(source)
        self.add_node(target)
        self.out_edges[source][target] = self.out_edges[source].get(target, 0.0) + weight
        self.in_edges[target][source] = self.in_edges[target].get(source, 0.0) + weight

    def compute_pagerank(
        self,
        personalization: Optional[Dict[str, float]] = None,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
        initial_ranks: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Calculates Personalized PageRank scores via power iteration.
        
        Args:
            personalization: Optional dict mapping node -> prior weight (e.g. actively edited files).
            damping: Damping factor (default 0.85).
            max_iter: Maximum iterations before stopping.
            tol: Convergence tolerance threshold on L1 norm.
            initial_ranks: Optional prior stationary distribution vector for Warm-Start.
            
        Returns:
            Dict of node -> rank score (sums to 1.0).
        """
        if not self.nodes:
            return {}

        n = len(self.nodes)
        node_list = sorted(list(self.nodes))
        
        # Build teleportation vector p
        p: Dict[str, float] = {}
        if personalization:
            total_pers = sum(personalization.get(node, 0.0) for node in node_list)
            if total_pers > 0:
                p = {node: personalization.get(node, 0.0) / total_pers for node in node_list}
            else:
                p = {node: 1.0 / n for node in node_list}
        else:
            p = {node: 1.0 / n for node in node_list}

        # Initialize ranks: Warm-Start if prior distribution available, else uniform 1/n
        ranks: Dict[str, float] = {}
        if initial_ranks:
            total_init = sum(initial_ranks.get(node, 1.0 / n) for node in node_list)
            ranks = {node: initial_ranks.get(node, 1.0 / n) / total_init for node in node_list}
        else:
            ranks = {node: 1.0 / n for node in node_list}

        for _ in range(max_iter):
            next_ranks: Dict[str, float] = {node: 0.0 for node in node_list}
            dangling_sum = 0.0

            # Calculate outbound contributions
            for u in node_list:
                out_degree = sum(self.out_edges[u].values())
                if out_degree > 0:
                    for v, w in self.out_edges[u].items():
                        next_ranks[v] += damping * ranks[u] * (w / out_degree)
                else:
                    dangling_sum += ranks[u]

            # Distribute dangling mass and teleportation mass
            for u in node_list:
                next_ranks[u] += (damping * dangling_sum + (1.0 - damping)) * p[u]

            # Check convergence via L1 norm
            diff = sum(abs(next_ranks[u] - ranks[u]) for u in node_list)
            ranks = next_ranks
            if diff < tol:
                break

        # Normalize final scores to sum strictly to 1.0
        total_sum = sum(ranks.values()) or 1.0
        return {node: score / total_sum for node, score in ranks.items()}
