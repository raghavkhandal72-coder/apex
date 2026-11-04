"""Zobrist / SHA-256 Normalized AST Transposition Table for MCTS.
Caches rollout evaluations by normalized AST topology to skip redundant sandbox test executions.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from apex_council.memory.fingerprint import NormalizedASTHasher


@dataclass
class TranspositionEntry:
    ast_hash: str
    eval_score: float
    eval_details: Dict[str, Any]
    visit_count: int
    created_at: float


class ASTTranspositionTable:
    """O(1) in-memory cache of MCTS AST state evaluations to avoid duplicate sandbox executions."""

    def __init__(self, max_entries: int = 5000) -> None:
        self.max_entries = max_entries
        self.table: Dict[str, TranspositionEntry] = {}
        self.hits: int = 0
        self.misses: int = 0

    def lookup(self, code: str) -> Optional[Tuple[float, Dict[str, Any]]]:
        ast_hash = NormalizedASTHasher.compute_fingerprint(code)
        if ast_hash in self.table:
            self.hits += 1
            entry = self.table[ast_hash]
            entry.visit_count += 1
            return entry.eval_score, entry.eval_details
        self.misses += 1
        return None

    def store(self, code: str, score: float, details: Dict[str, Any]) -> str:
        ast_hash = NormalizedASTHasher.compute_fingerprint(code)
        if len(self.table) >= self.max_entries:
            # Evict oldest entry
            oldest_key = min(self.table.keys(), key=lambda k: self.table[k].created_at)
            del self.table[oldest_key]

        self.table[ast_hash] = TranspositionEntry(
            ast_hash=ast_hash,
            eval_score=score,
            eval_details=details,
            visit_count=1,
            created_at=time.time(),
        )
        return ast_hash

    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def clear(self) -> None:
        self.table.clear()
        self.hits = 0
        self.misses = 0
