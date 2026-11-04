import tempfile
import unittest
from pathlib import Path

from apex_council.graph.cache import IncrementalASTCache
from apex_council.graph.pagerank import PersonalizedPageRankEngine
from apex_council.graph.parser import SymbolGraphExtractor
from apex_council.graph.repo_map import RepoMap
from apex_council.memory.fingerprint import NormalizedASTHasher
from apex_council.memory.matcher import MemoryMatcher
from apex_council.memory.vault import MemoryVault


class TestPhase4GraphAndMemory(unittest.TestCase):
    def test_symbol_extraction_and_ast_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            f = Path(tmp_dir) / "mod.py"
            f.write_text("def greet(name: str) -> str:\n    return f'Hello {name}'\n", encoding="utf-8")

            cache = IncrementalASTCache(db_path=":memory:")
            file_symbols = cache.get_or_parse(f)
            self.assertEqual(len(file_symbols.definitions), 1)
            self.assertEqual(file_symbols.definitions[0].name, "greet")

            # Second read should be retrieved from cache
            s2 = cache.get_or_parse(f)
            self.assertEqual(s2.definitions[0].name, "greet")

    def test_pagerank_convergence_and_repo_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir)
            (p / "main.py").write_text("import helper\ndef run(): helper.assist()\n", encoding="utf-8")
            (p / "helper.py").write_text("def assist(): return True\n", encoding="utf-8")

            repo_map = RepoMap(p, max_tokens=256)
            skeleton = repo_map.generate_map(keywords=["assist"])
            self.assertIn("def assist()", skeleton)

    def test_normalized_ast_structural_fingerprint(self) -> None:
        c1 = "def calc(x, y): return x + y"
        c2 = "def compute(a, b): return a + b"
        h1 = NormalizedASTHasher.compute_fingerprint(c1)
        h2 = NormalizedASTHasher.compute_fingerprint(c2)
        self.assertEqual(h1, h2)

    def test_memory_vault_fts5_and_decay(self) -> None:
        vault = MemoryVault(":memory:")
        vault.record_episode(
            session_id="s1",
            task_prompt="Fix multithreaded sqlite locking",
            target_files=["db.py"],
            error_signature="sqlite3.OperationalError: database is locked",
            lesson_learned="Always enable WAL mode and set busy_timeout",
            solution_summary="Added WAL pragma",
            status="SOLVED",
        )
        vault.add_heuristic(
            category="DATABASE",
            pattern="sqlite database locked concurrency",
            rule_text="Always enable WAL mode and set busy_timeout",
            confidence_score=0.95,
        )
        matcher = MemoryMatcher(vault)
        rules = matcher.find_relevant_rules("sqlite database locked under concurrency")
        self.assertGreater(len(rules), 0)

        episodes = vault.search_episodes_bm25("sqlite locking")
        self.assertGreater(len(episodes), 0)


if __name__ == "__main__":
    unittest.main()
