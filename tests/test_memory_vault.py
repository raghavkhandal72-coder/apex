import unittest

from apex_council.memory.matcher import MemoryMatcher
from apex_council.memory.vault import MemoryVault


class TestMemoryVault(unittest.TestCase):
    def setUp(self) -> None:
        self.vault = MemoryVault(":memory:")
        self.matcher = MemoryMatcher(self.vault)

    def test_record_and_retrieve_episode(self) -> None:
        ep_id = self.vault.record_episode(
            session_id="test-session-101",
            task_prompt="Fix race condition in sqlite connection pool",
            target_files=["db/pool.py"],
            error_signature="sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread",
            lesson_learned="Always enable check_same_thread=False or allocate thread-local connections",
            solution_summary="Added threading.local() connection manager",
            status="SOLVED",
        )
        self.assertGreater(ep_id, 0)
        episodes = self.vault.get_all_episodes()
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].session_id, "test-session-101")
        self.assertIn("db/pool.py", episodes[0].target_files)

    def test_add_and_retrieve_heuristics(self) -> None:
        h_id = self.vault.add_heuristic(
            category="CONCURRENCY",
            pattern="threading.Lock sqlite3 connection",
            rule_text="Never hold a mutex across blocking network I/O",
            confidence_score=0.95,
        )
        self.assertGreater(h_id, 0)
        heuristics = self.vault.get_all_heuristics()
        self.assertEqual(len(heuristics), 1)
        self.assertEqual(heuristics[0].category, "CONCURRENCY")
        self.assertEqual(heuristics[0].confidence_score, 0.95)

    def test_memory_matcher_relevance(self) -> None:
        self.vault.add_heuristic(
            category="DATABASE",
            pattern="sqlite3 database connection deadlock",
            rule_text="Use WAL journal mode and set busy_timeout to avoid lock contention",
            confidence_score=0.9,
        )
        self.vault.add_heuristic(
            category="ENCODING",
            pattern="windows cp1252 utf-8 unicode decode",
            rule_text="Always pass encoding='utf-8', errors='replace' to subprocess.run",
            confidence_score=1.0,
        )

        # Query matching database
        db_rules = self.matcher.find_relevant_rules("We have a sqlite3 deadlock issue on insert")
        self.assertEqual(len(db_rules), 1)
        self.assertEqual(db_rules[0].category, "DATABASE")

        # Query matching encoding
        enc_rules = self.matcher.find_relevant_rules("Subprocess failed with UnicodeDecodeError cp1252")
        self.assertEqual(len(enc_rules), 1)
        self.assertEqual(enc_rules[0].category, "ENCODING")

    def test_memory_injection_formatting(self) -> None:
        self.vault.add_heuristic(
            category="SECURITY",
            pattern="pickle unpickle remote code execution",
            rule_text="Never use pickle.loads on untrusted network payloads; use json or hmac",
            confidence_score=1.0,
        )
        injection = self.matcher.format_memory_injection("Implement serialization for network packet with pickle")
        self.assertIn("APEX EPISODIC MEMORY", injection)
        self.assertIn("Never use pickle.loads", injection)

        # Unrelated query should return empty string
        empty_injection = self.matcher.format_memory_injection("Paint the button color blue")
        self.assertEqual(empty_injection, "")

    def test_fts5_bm25_search(self) -> None:
        self.vault.record_episode(
            session_id="ep-1",
            task_prompt="Fix deadlocks in connection pool when timeout expires",
            target_files=["pool.py"],
            error_signature="ConnectionPoolTimeoutError: exhausted after 30s",
            lesson_learned="Increase queue size and use non-blocking acquire",
            solution_summary="Refactored pool queue",
        )
        self.vault.record_episode(
            session_id="ep-2",
            task_prompt="Optimize CSS animations on homepage navbar",
            target_files=["nav.css"],
            error_signature="Layout shift alert",
            lesson_learned="Use transform instead of left/top",
            solution_summary="Updated CSS styles",
        )

        results = self.vault.search_episodes_bm25("connection pool timeout")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].session_id, "ep-1")

    def test_normalized_ast_structural_fingerprint(self) -> None:
        from apex_council.memory.matcher import NormalizedASTHasher

        # Pattern 1: function with loop and return
        code1 = """
def transform_items(data):
    acc = []
    for item in data:
        acc.append(item * 2)
    return acc
"""
        # Pattern 2: completely different names, identical AST topology
        code2 = """
def compute_elements(records):
    buf = []
    for elem in records:
        buf.append(elem * 2)
    return buf
"""
        fp1 = NormalizedASTHasher.compute_fingerprint(code1)
        fp2 = NormalizedASTHasher.compute_fingerprint(code2)
        self.assertEqual(fp1, fp2)

        # Store heuristic with fp1
        self.vault.add_heuristic(
            category="PERFORMANCE",
            pattern="list append loop",
            rule_text="Use list comprehension for 2x faster execution than manual append loop",
            ast_fingerprint=fp1,
            confidence_score=0.98,
        )

        # Retrieve using code2!
        matches = self.matcher.find_by_ast(code2)
        self.assertEqual(len(matches), 1)
        self.assertIn("list comprehension", matches[0].rule_text)

    def test_ebbinghaus_decay_and_reinforcement(self) -> None:
        rule_id = self.vault.add_heuristic(
            category="CONCURRENCY",
            pattern="race condition",
            rule_text="Use monotonic clock for timeouts",
            confidence_score=0.9,
            strength_days=10.0,
        )
        rules = self.vault.get_all_heuristics()
        self.assertEqual(len(rules), 1)
        init_eff = rules[0].effective_confidence
        self.assertGreaterEqual(init_eff, 0.85)

        # Reinforce
        reinforced = self.vault.reinforce_heuristic(rule_id)
        self.assertTrue(reinforced)
        updated = self.vault.get_all_heuristics()[0]
        self.assertEqual(updated.strength_days, 15.0)

    def test_stacktrace_signature_clustering(self) -> None:
        from apex_council.memory.matcher import StacktraceClusterer

        trace1 = """
Traceback (most recent call last):
  File "/home/user/repo/worker.py", line 42, in process
    res = conn.execute("SELECT 1")
sqlite3.OperationalError: database is locked
"""
        trace2 = """
Traceback (most recent call last):
  File "C:\\projects\\app\\worker.py", line 89, in process
    res = conn.execute("SELECT 1")
sqlite3.OperationalError: database is locked
"""
        sig1 = StacktraceClusterer.compute_signature_hash(trace1)
        sig2 = StacktraceClusterer.compute_signature_hash(trace2)
        self.assertEqual(sig1, sig2)


if __name__ == "__main__":
    unittest.main()
