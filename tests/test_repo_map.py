import tempfile
import unittest
from pathlib import Path

from apex_council.graph.pagerank import PageRankGraph
from apex_council.graph.parser import SymbolParser
from apex_council.graph.repo_map import RepoMap


class TestRepoMapEngine(unittest.TestCase):
    def test_symbol_parser_python(self) -> None:
        code = '''
"""Module docstring."""
import os
from math import sqrt

class MatrixSolver:
    """Solves linear systems."""
    def __init__(self, size: int) -> None:
        self.size = size

    def solve(self, matrix: list) -> list:
        return [sqrt(x) for x in matrix]

def helper_func(val: int) -> int:
    return val * 2
'''
        syms = SymbolParser.parse_python_source(code, filepath="solver.py")
        self.assertEqual(syms.filepath, "solver.py")
        names = {s.name for s in syms.definitions}
        self.assertIn("MatrixSolver", names)
        self.assertIn("__init__", names)
        self.assertIn("solve", names)
        self.assertIn("helper_func", names)
        self.assertIn("math.sqrt", syms.imports)
        self.assertIn("os", syms.imports)
        self.assertIn("sqrt", syms.references)

    def test_symbol_parser_generic_js(self) -> None:
        js_code = """
import { useState } from 'react';

export class AuthWidget {
  login() {}
}

export function verifyToken(token) {
  return true;
}
"""
        syms = SymbolParser.parse_generic_source(js_code, filepath="auth.js")
        names = {s.name for s in syms.definitions}
        self.assertIn("AuthWidget", names)
        self.assertIn("verifyToken", names)
        self.assertIn("react", syms.imports)

    def test_pagerank_convergence(self) -> None:
        graph = PageRankGraph()
        # Node A points to B and C; B points to C; C points to A
        graph.add_edge("A", "B")
        graph.add_edge("A", "C")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")

        ranks = graph.compute_pagerank()
        self.assertEqual(len(ranks), 3)
        self.assertAlmostEqual(sum(ranks.values()), 1.0, places=4)
        # C has 2 incoming edges (from A and B), should have highest rank
        self.assertGreater(ranks["C"], ranks["B"])

    def test_repo_map_scan_and_token_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Create core module
            core_file = tmppath / "core.py"
            core_file.write_text("""
class CoreEngine:
    '''Central system engine.'''
    def run(self): pass
""", encoding="utf-8")

            # Create helper module referencing core
            worker_file = tmppath / "worker.py"
            worker_file.write_text("""
from core import CoreEngine

class Worker:
    def process(self):
        engine = CoreEngine()
        engine.run()
""", encoding="utf-8")

            # Run repo map
            repo_map = RepoMap(root_dir=tmpdir, max_tokens=150)
            repo_map.scan()
            
            self.assertEqual(len(repo_map.file_symbols), 2)
            
            # Generate map with tight budget
            rendered = repo_map.generate_map(token_budget=150)
            self.assertIn("CoreEngine", rendered)
            self.assertIn("Worker", rendered)
            # Budget check: 150 tokens ~ 600 chars (allow small margin)
            self.assertLessEqual(len(rendered), 150 * 5)

            # Summary stats
            summary = repo_map.get_summary()
            self.assertEqual(summary["total_files"], 2)
            self.assertGreaterEqual(summary["total_symbols"], 2)

    def test_repo_map_personalization_boost(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "file_a.py").write_text("class A: pass", encoding="utf-8")
            (tmppath / "file_b.py").write_text("class B: pass", encoding="utf-8")

            repo_map = RepoMap(root_dir=tmpdir)
            repo_map.scan()

            # Boost file_b via focus_files
            repo_map.generate_map(focus_files=["file_b.py"])
            self.assertGreater(repo_map.ranks["file_b.py"], repo_map.ranks["file_a.py"])

    def test_ast_cache_incremental(self) -> None:
        from apex_council.graph.cache import ASTCache
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            f = tmppath / "sample.py"
            f.write_text("class Alpha: pass", encoding="utf-8")

            cache = ASTCache(":memory:")
            syms1 = cache.get_or_parse(f)
            self.assertEqual(len(syms1.definitions), 1)
            self.assertEqual(syms1.definitions[0].name, "Alpha")

            # Second call should hit cache
            syms2 = cache.get_or_parse(f)
            self.assertEqual(len(syms2.definitions), 1)

            # Modify file
            f.write_text("class Beta: pass\nclass Gamma: pass", encoding="utf-8")
            syms3 = cache.get_or_parse(f)
            self.assertEqual(len(syms3.definitions), 2)
            names = {s.name for s in syms3.definitions}
            self.assertIn("Beta", names)
            self.assertIn("Gamma", names)

    def test_warm_start_pagerank(self) -> None:
        graph = PageRankGraph()
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")
        graph.add_edge("C", "A")

        cold_ranks = graph.compute_pagerank()
        # Warm start using cold ranks
        warm_ranks = graph.compute_pagerank(initial_ranks=cold_ranks, max_iter=5)
        for node in cold_ranks:
            self.assertAlmostEqual(cold_ranks[node], warm_ranks[node], places=3)


if __name__ == "__main__":
    unittest.main()
