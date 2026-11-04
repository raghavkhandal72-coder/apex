"""Cross-Model Semantic Diff Merger / Genetic AST Crossover.
Synthesizes hybrid child nodes by merging complementary functions, classes, and edge-case guards from two models.
Pure Python standard library implementation.
"""

from __future__ import annotations

from apex_council.search.transposition_and_crossover import (
    BitmaskGeneticASTCrossover,
    CrossoverResult,
    SemanticASTCrossover,
)

__all__ = [
    "CrossoverResult",
    "SemanticASTCrossover",
    "BitmaskGeneticASTCrossover",
]
