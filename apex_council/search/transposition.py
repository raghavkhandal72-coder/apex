"""Zobrist / SHA-256 Normalized AST Transposition Table for MCTS.
Caches rollout evaluations by normalized AST topology to skip redundant sandbox test executions.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

from apex_council.search.transposition_and_crossover import (
    ASTMetricsAndHashEngine,
    ASTTranspositionTable,
    TranspositionEntry,
    _CanonicalAlphaNormalizer,
)

__all__ = [
    "ASTTranspositionTable",
    "TranspositionEntry",
    "ASTMetricsAndHashEngine",
    "_CanonicalAlphaNormalizer",
]
