"""Memory Matcher with SQLite3 FTS5 BM25 Ranking and Normalized AST Structural Hashing.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import ast
import hashlib
import re
from typing import Dict, List, Optional, Set

from apex_council.memory.vault import Episode, HeuristicRule, MemoryVault


class ASTNormalizer(ast.NodeTransformer):
    """Normalizes identifiers, variable names, arguments, and constants.
    Preserves purely the abstract structural topology of the code.
    """

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "_f"
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = "_af"
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = "_c"
        return self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = "_a"
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> ast.AST:
        node.id = "_v"
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, str):
            node.value = ""
        elif isinstance(node.value, (int, float)):
            node.value = 0
        return self.generic_visit(node)


class NormalizedASTHasher:
    """Computes a SHA-256 fingerprint of the normalized AST topology."""

    @staticmethod
    def compute_fingerprint(code: str) -> str:
        try:
            tree = ast.parse(code)
            normalizer = ASTNormalizer()
            normalized_tree = normalizer.visit(tree)
            ast.fix_missing_locations(normalized_tree)
            canonical_code = ast.unparse(normalized_tree) if hasattr(ast, "unparse") else ast.dump(normalized_tree)
            return hashlib.sha256(canonical_code.encode("utf-8")).hexdigest()
        except Exception:
            # Fallback token normalization
            tokens = re.sub(r"\s+", " ", code).strip()
            return hashlib.sha256(tokens.encode("utf-8")).hexdigest()


class MemoryMatcher:
    """Matches developer prompts, stack traces, and code blocks using FTS5 BM25 & AST Fingerprints."""

    def __init__(self, vault: MemoryVault) -> None:
        self.vault = vault

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        words = re.findall(r"\b[A-Za-z0-9_]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "for", "with", "that", "this", "from", "are", "was",
            "were", "will", "can", "should", "could", "have", "has", "had"
        }
        return {w for w in words if w not in stopwords}

    def find_by_ast(self, code_snippet: str) -> List[HeuristicRule]:
        """Finds heuristics that structurally match the code snippet regardless of naming."""
        fp = NormalizedASTHasher.compute_fingerprint(code_snippet)
        return self.vault.get_by_ast_fingerprint(fp)

    def find_relevant_rules(self, query: str, top_k: int = 3) -> List[HeuristicRule]:
        rules = self.vault.get_all_heuristics()
        if not rules:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return rules[:top_k]

        scored: List[tuple[float, HeuristicRule]] = []
        for r in rules:
            pat_tokens = self._tokenize(f"{r.category} {r.pattern} {r.rule_text}")
            overlap = len(query_tokens & pat_tokens)
            score = overlap * r.confidence_score
            if score > 0:
                scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def find_relevant_episodes(self, query: str, top_k: int = 3) -> List[Episode]:
        # 1. Try SQLite3 FTS5 BM25 Ranking First
        bm25_matches = self.vault.search_episodes_bm25(query, limit=top_k)
        if bm25_matches:
            return bm25_matches

        # 2. Fallback to token overlap
        episodes = self.vault.get_all_episodes(limit=50)
        if not episodes:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return episodes[:top_k]

        scored: List[tuple[int, Episode]] = []
        for ep in episodes:
            ep_tokens = self._tokenize(f"{ep.task_prompt} {ep.error_signature} {ep.lesson_learned}")
            overlap = len(query_tokens & ep_tokens)
            if overlap > 0:
                scored.append((overlap, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def format_memory_injection(self, query: str, code_snippet: Optional[str] = None) -> str:
        """Formats matched lessons into a high-signal injection prompt block."""
        matched_rules = self.find_relevant_rules(query)
        matched_episodes = self.find_relevant_episodes(query)
        ast_rules = self.find_by_ast(code_snippet) if code_snippet else []

        all_rules = list({r.rule_text: r for r in (ast_rules + matched_rules)}.values())

        if not all_rules and not matched_episodes:
            return ""

        lines = [
            "🏛️ APEX EPISODIC MEMORY (Learned Institutional Knowledge):",
            "# Automatically retrieved past lessons via FTS5 BM25 & AST Structural Fingerprinting:",
        ]

        for r in all_rules:
            ast_tag = " [AST MATCH]" if r in ast_rules else ""
            lines.append(f"  • [{r.category}]{ast_tag} {r.rule_text} (Score: {r.confidence_score:.1f})")

        for ep in matched_episodes:
            lines.append(f"  • [Historical Issue] '{ep.task_prompt[:60]}...' ➔ Lesson: {ep.lesson_learned}")

        lines.append("")
        return "\n".join(lines)
