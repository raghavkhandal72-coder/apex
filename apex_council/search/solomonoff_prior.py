"""Apex-Sovereign: Solomonoff Universal Inductive Prior & Algorithmic Information Distance.
100% Pure Python Standard Library | Zero Dependencies | Ray Solomonoff (1964) & Li-Vitanyi (2008).

Mathematical Foundations:
1. Universal Solomonoff Inductive Prior:
   P_M(x) = sum_{p: U(p) = x} 2^(-l(p))
   Formalizes Occam's Razor: simpler programs have exponentially higher prior probability.
2. Kolmogorov Complexity Bound:
   K(x) <= C(x) + O(1), where C is a lossless compressor.
3. Pure-Python Lempel-Ziv-Welch (LZW) Dictionary Compression:
   Encodes repeated syntactic tokens into dynamic dictionary indices.
4. Normalized Compression Distance (NCD):
   NCD(x, y) = [ C(xy) - min(C(x), C(y)) ] / max(C(x), C(y))
5. AST Shannon Structural Entropy:
   H(x) = - sum_{t in NodeTypes} p(t) * log2(p(t))
6. Solomonoff Occam Action Prior:
   P(a | s) proportional to exp(- (C_LZW(code) / CharCount + beta * H(x)))
"""

from __future__ import annotations

import ast
import dataclasses
import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


class LZWCompressor:
    """Pure Python Standard Library Lempel-Ziv-Welch (LZW) string compressor."""

    @classmethod
    def compress(cls, text: str) -> List[int]:
        if not text:
            return []

        # Initialize dictionary with all ASCII / Latin chars
        dictionary: Dict[str, int] = {chr(i): i for i in range(256)}
        next_code = 256
        w = ""
        result: List[int] = []

        for c in text:
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                result.append(dictionary.get(w, ord(w[0]) if w else 0))
                # Add wc to the dictionary
                if next_code < 65536:
                    dictionary[wc] = next_code
                    next_code += 1
                w = c

        if w:
            result.append(dictionary.get(w, ord(w[0])))

        return result

    @classmethod
    def compressed_bit_length(cls, text: str) -> int:
        """Returns approximate compressed size in bits (12 bits per LZW token)."""
        tokens = cls.compress(text)
        return len(tokens) * 12


@dataclasses.dataclass(frozen=True)
class AlgorithmicInformationReport:
    raw_character_count: int
    lzw_token_count: int
    compressed_bits: int
    compression_ratio: float
    ast_shannon_entropy: float
    solomonoff_prior_score: float  # (0.0 to 1.0] Occam likelihood
    kolmogorov_upper_bound: int


class SolomonoffPriorEngine:
    """Computes universal inductive priors and algorithmic distances for code."""

    def __init__(self, entropy_beta: float = 0.5) -> None:
        self.entropy_beta = entropy_beta

    @classmethod
    def compute_ast_entropy(cls, code: str) -> float:
        """Computes Shannon entropy across AST node type distribution."""
        try:
            tree = ast.parse(code)
        except Exception:
            return 3.0  # Nominal entropy fallback for unparseable snippets

        node_types = [type(n).__name__ for n in ast.walk(tree)]
        if not node_types:
            return 0.0

        total = len(node_types)
        counts = Counter(node_types)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0.0:
                entropy -= p * math.log2(p)
        return round(entropy, 4)

    @classmethod
    def compute_ncd(cls, code_x: str, code_y: str) -> float:
        """
        Computes Normalized Compression Distance (NCD) in [0.0, 1.0+].
        NCD(x, y) = [ C(xy) - min(C(x), C(y)) ] / max(C(x), C(y))
        """
        if code_x == code_y:
            return 0.0

        c_x = LZWCompressor.compressed_bit_length(code_x)
        c_y = LZWCompressor.compressed_bit_length(code_y)
        c_xy = LZWCompressor.compressed_bit_length(code_x + "\n" + code_y)

        min_c = min(c_x, c_y)
        max_c = max(c_x, c_y)

        if max_c == 0:
            return 0.0

        ncd = (c_xy - min_c) / max_c
        return round(max(0.0, ncd), 4)

    def evaluate_program(self, code: str) -> AlgorithmicInformationReport:
        """
        Evaluates the algorithmic information content, Kolmogorov upper bound,
        and Solomonoff inductive prior of candidate code.
        """
        raw_len = len(code)
        tokens = LZWCompressor.compress(code)
        comp_bits = len(tokens) * 12
        comp_ratio = (comp_bits / (raw_len * 8)) if raw_len > 0 else 1.0
        ast_entropy = self.compute_ast_entropy(code)

        # Solomonoff prior score: P(M) proportional to exp(- (tokens + beta * entropy))
        norm_complexity = (len(tokens) / 10.0) + (self.entropy_beta * ast_entropy)
        solomonoff_score = math.exp(-min(20.0, norm_complexity))

        return AlgorithmicInformationReport(
            raw_character_count=raw_len,
            lzw_token_count=len(tokens),
            compressed_bits=comp_bits,
            compression_ratio=round(comp_ratio, 4),
            ast_shannon_entropy=ast_entropy,
            solomonoff_prior_score=round(solomonoff_score, 6),
            kolmogorov_upper_bound=comp_bits,
        )

    def rank_candidates_by_occam_razor(self, candidates: List[str]) -> List[Tuple[str, float]]:
        """
        Ranks candidate programs according to the Solomonoff Occam prior.
        Returns List of (candidate_code, solomonoff_score) sorted descending.
        """
        scored = [
            (c, self.evaluate_program(c).solomonoff_prior_score)
            for c in candidates
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored
