"""Persistent Episodic Memory Vault with SQLite3 FTS5 (BM25) and AST Fingerprinting.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Episode:
    id: Optional[int]
    session_id: str
    task_prompt: str
    target_files: List[str]
    error_signature: str
    lesson_learned: str
    solution_summary: str
    ast_fingerprint: str
    status: str
    created_at: str


@dataclass
class HeuristicRule:
    id: Optional[int]
    category: str
    pattern: str
    rule_text: str
    ast_fingerprint: str
    confidence_score: float
    created_at: str


class MemoryVault:
    """Manages the persistent SQLite database with FTS5 full-text indexing and AST fingerprints."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self.db_path = str(db_path)
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                task_prompt TEXT NOT NULL,
                target_files TEXT NOT NULL,
                error_signature TEXT NOT NULL,
                lesson_learned TEXT NOT NULL,
                solution_summary TEXT NOT NULL,
                ast_fingerprint TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                pattern TEXT NOT NULL,
                rule_text TEXT NOT NULL,
                ast_fingerprint TEXT NOT NULL DEFAULT '',
                confidence_score REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        # Create FTS5 Virtual Table for BM25 Ranking
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
                    task_prompt, error_signature, lesson_learned,
                    content='episodes',
                    content_rowid='id'
                );
                """
            )
            # Create FTS triggers for automatic sync
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
                    INSERT INTO episodes_fts(rowid, task_prompt, error_signature, lesson_learned)
                    VALUES (new.id, new.task_prompt, new.error_signature, new.lesson_learned);
                END;
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
                    INSERT INTO episodes_fts(episodes_fts, rowid, task_prompt, error_signature, lesson_learned)
                    VALUES('delete', old.id, old.task_prompt, old.error_signature, old.lesson_learned);
                END;
                """
            )
        except Exception:
            # Fallback if FTS5 is compiled out in legacy environments
            pass

        conn.commit()
        if self._persistent_conn is None:
            conn.close()

    def record_episode(
        self,
        session_id: str,
        task_prompt: str,
        target_files: List[str],
        error_signature: str,
        lesson_learned: str,
        solution_summary: str,
        ast_fingerprint: str = "",
        status: str = "SOLVED",
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodes (
                    session_id, task_prompt, target_files, error_signature,
                    lesson_learned, solution_summary, ast_fingerprint, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    task_prompt,
                    json.dumps(target_files),
                    error_signature,
                    lesson_learned,
                    solution_summary,
                    ast_fingerprint,
                    status,
                    now,
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            if self._persistent_conn is None:
                conn.close()

    def add_heuristic(
        self,
        category: str,
        pattern: str,
        rule_text: str,
        ast_fingerprint: str = "",
        confidence_score: float = 1.0,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO heuristics (
                    category, pattern, rule_text, ast_fingerprint, confidence_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (category, pattern, rule_text, ast_fingerprint, confidence_score, now),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            if self._persistent_conn is None:
                conn.close()

    def search_episodes_bm25(self, query: str, limit: int = 5) -> List[Episode]:
        """Runs SQLite3 FTS5 full-text search with BM25 ranking."""
        conn = self._get_connection()
        try:
            # Sanitize FTS5 query string
            sanitized = " OR ".join([f'"{w}"' for w in query.replace('"', "").split() if len(w) > 2])
            if not sanitized:
                return []

            rows = conn.execute(
                """
                SELECT e.* FROM episodes_fts f
                JOIN episodes e ON e.id = f.rowid
                WHERE episodes_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (sanitized, limit),
            ).fetchall()

            return [
                Episode(
                    id=r["id"],
                    session_id=r["session_id"],
                    task_prompt=r["task_prompt"],
                    target_files=json.loads(r["target_files"]),
                    error_signature=r["error_signature"],
                    lesson_learned=r["lesson_learned"],
                    solution_summary=r["solution_summary"],
                    ast_fingerprint=r["ast_fingerprint"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        except Exception:
            return []
        finally:
            if self._persistent_conn is None:
                conn.close()

    def get_by_ast_fingerprint(self, fingerprint: str) -> List[HeuristicRule]:
        """Finds heuristics with identical normalized AST structural fingerprint."""
        if not fingerprint:
            return []
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM heuristics WHERE ast_fingerprint = ? ORDER BY confidence_score DESC",
                (fingerprint,),
            ).fetchall()
            return [
                HeuristicRule(
                    id=r["id"],
                    category=r["category"],
                    pattern=r["pattern"],
                    rule_text=r["rule_text"],
                    ast_fingerprint=r["ast_fingerprint"],
                    confidence_score=r["confidence_score"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            if self._persistent_conn is None:
                conn.close()

    def get_all_episodes(self, limit: int = 100) -> List[Episode]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM episodes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [
                Episode(
                    id=r["id"],
                    session_id=r["session_id"],
                    task_prompt=r["task_prompt"],
                    target_files=json.loads(r["target_files"]),
                    error_signature=r["error_signature"],
                    lesson_learned=r["lesson_learned"],
                    solution_summary=r["solution_summary"],
                    ast_fingerprint=r["ast_fingerprint"],
                    status=r["status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            if self._persistent_conn is None:
                conn.close()

    def get_all_heuristics(self) -> List[HeuristicRule]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM heuristics ORDER BY confidence_score DESC").fetchall()
            return [
                HeuristicRule(
                    id=r["id"],
                    category=r["category"],
                    pattern=r["pattern"],
                    rule_text=r["rule_text"],
                    ast_fingerprint=r["ast_fingerprint"],
                    confidence_score=r["confidence_score"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            if self._persistent_conn is None:
                conn.close()
