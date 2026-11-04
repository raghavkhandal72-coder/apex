"""Personalized PageRank Repo-Map Engine.
Compresses entire repositories into an architectural skeleton fitting within strict token budgets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from apex_council.graph.cache import ASTCache
from apex_council.graph.pagerank import PageRankGraph
from apex_council.graph.parser import FileSymbols, Symbol, SymbolParser


IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__",
    "node_modules", "dist", "build", ".pytest_cache", ".mypy_cache",
    ".tox", ".idea", ".vscode", ".apex", ".system_generated"
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".sh"
}


class RepoMap:
    """Scans codebases, builds dependency graphs, and generates token-bounded structural maps."""

    def __init__(
        self,
        root_dir: Path | str,
        max_tokens: int = 1024,
        cache: Optional[ASTCache] = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.max_tokens = max_tokens
        self.file_symbols: Dict[str, FileSymbols] = {}
        self.graph = PageRankGraph()
        self.ranks: Dict[str, float] = {}
        self.cache = cache or ASTCache(self.root_dir / ".apex" / "ast_cache.db")

    def scan(self) -> RepoMap:
        """Walks the root directory and extracts symbols using the incremental AST cache."""
        self.file_symbols.clear()
        
        for dirpath, dirnames, filenames in os.walk(self.root_dir):
            # Prune ignored directories in-place
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                if file_path.suffix.lower() not in CODE_EXTENSIONS:
                    continue

                try:
                    rel_path = file_path.relative_to(self.root_dir).as_posix()
                except ValueError:
                    rel_path = file_path.as_posix()

                syms = self.cache.get_or_parse(file_path)
                syms.filepath = rel_path
                self.file_symbols[rel_path] = syms

        self._build_dependency_graph()
        return self

    def _build_dependency_graph(self) -> None:
        """Constructs caller-callee and import edges across files."""
        self.graph = PageRankGraph()
        for filepath in self.file_symbols:
            self.graph.add_node(filepath)

        # Index symbol -> files defining it
        defined_in: Dict[str, List[str]] = {}
        for filepath, syms in self.file_symbols.items():
            for name in syms.defined_names:
                defined_in.setdefault(name, []).append(filepath)

        # Build edges based on symbol references
        for filepath, syms in self.file_symbols.items():
            for ref in syms.references:
                target_files = defined_in.get(ref, [])
                for target in target_files:
                    if target != filepath:
                        self.graph.add_edge(filepath, target, weight=1.0)

            # Build edges based on import path match
            for imp in syms.imports:
                imp_path_cand = imp.replace(".", "/")
                for candidate_file in self.file_symbols:
                    if imp_path_cand in candidate_file or candidate_file.startswith(imp_path_cand):
                        if candidate_file != filepath:
                            self.graph.add_edge(filepath, candidate_file, weight=2.0)

    def generate_map(
        self,
        focus_files: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        token_budget: Optional[int] = None,
    ) -> str:
        """Generates a compact structural skeleton biased by focus files or keywords.
        
        Args:
            focus_files: Specific files that receive boosted teleportation weight.
            keywords: Keywords to boost relevant files in PageRank.
            token_budget: Maximum tokens allowed (defaults to self.max_tokens).
            
        Returns:
            A compact, high-signal structural overview of the codebase.
        """
        budget = token_budget or self.max_tokens
        if not self.file_symbols:
            self.scan()

        if not self.file_symbols:
            return "# Empty repository (no source code files detected)"

        # Calculate personalization vector
        personalization: Dict[str, float] = {}
        focus_set = set(focus_files or [])
        keyword_set = {k.lower() for k in (keywords or [])}

        for path, syms in self.file_symbols.items():
            score = 1.0
            if path in focus_set or any(f in path for f in focus_set):
                score += 15.0
            if keyword_set:
                matched_words = sum(1 for k in keyword_set if k in path.lower() or any(k in s.name.lower() for s in syms.definitions))
                score += matched_words * 5.0
            personalization[path] = score

        # Compute PageRank with Warm-Start support
        self.ranks = self.graph.compute_pagerank(
            personalization=personalization,
            initial_ranks=self.ranks if self.ranks else None,
        )

        # Sort files by PageRank score descending
        ranked_files = sorted(self.file_symbols.keys(), key=lambda f: self.ranks.get(f, 0.0), reverse=True)

        # Binary search to fit the largest structural skeleton within the token budget
        return self._fit_skeleton(ranked_files, budget)

    def _fit_skeleton(self, ranked_files: List[str], token_budget: int) -> str:
        """Uses binary search over the number of included files to strictly obey the token budget."""
        char_budget = token_budget * 4  # Standard estimation: ~4 chars per token

        def render_subset(k: int) -> str:
            lines = [
                "🏛️ APEX SOVEREIGN REPOSITORY MAP (Personalized PageRank)",
                f"# Total Indexed Files: {len(self.file_symbols)} | Architectural Spine View:",
                "",
            ]
            for file_path in ranked_files[:k]:
                syms = self.file_symbols[file_path]
                rank_score = self.ranks.get(file_path, 0.0)
                lines.append(f"📁 {file_path} [Rank: {rank_score:.4f}]")
                if not syms.definitions:
                    lines.append("  (module declarations / utility)")
                for s in syms.definitions:
                    indent = "    " if s.kind == "method" else "  "
                    sig = s.signature or f"def {s.name}()"
                    doc_hint = f"  # {s.docstring}" if s.docstring else ""
                    lines.append(f"{indent}{sig}{doc_hint}")
                lines.append("")
            return "\n".join(lines).strip()

        # Binary search for optimal file count k in [1, len(ranked_files)]
        low = 1
        high = len(ranked_files)
        best_output = render_subset(1)

        while low <= high:
            mid = (low + high) // 2
            rendered = render_subset(mid)
            if len(rendered) <= char_budget:
                best_output = rendered
                low = mid + 1  # Try including more files
            else:
                high = mid - 1  # Exceeded budget, back off

        return best_output

    def get_summary(self) -> Dict[str, object]:
        """Returns statistics on the repository structure."""
        if not self.ranks:
            self.generate_map()
        top_hubs = sorted(self.ranks.items(), key=lambda x: x[1], reverse=True)[:5]
        total_syms = sum(len(s.definitions) for s in self.file_symbols.values())
        return {
            "total_files": len(self.file_symbols),
            "total_symbols": total_syms,
            "top_architectural_hubs": [{"file": f, "pagerank": round(score, 4)} for f, score in top_hubs],
        }
