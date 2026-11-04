"""Monte Carlo Tree Search (MCTS) Test-Time Compute Engine with PUCT and Transposition Table.
Re-exports SovereignMCTSEngine, MCTSNode, and MCTSResult.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

from apex_council.search.sovereign_mcts import (
    AutonomousSDETTestAmplifier,
    MCTSNode,
    MCTSResult,
    SovereignMCTSEngine,
    SovereignMCTSNode,
    SovereignSolveResult,
    _LineTargetedOperatorSynthesizer,
)

# Canonical MCTSEngine points to SovereignMCTSEngine
MCTSEngine = SovereignMCTSEngine

__all__ = [
    "MCTSEngine",
    "MCTSNode",
    "MCTSResult",
    "SovereignMCTSEngine",
    "SovereignMCTSNode",
    "SovereignSolveResult",
    "AutonomousSDETTestAmplifier",
    "_LineTargetedOperatorSynthesizer",
]
