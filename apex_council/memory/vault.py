"""Persistent Episodic Memory Vault with SQLite3 FTS5 (BM25), AST Fingerprinting, and Ebbinghaus Decay.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import json
import math
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
    strength_days: float = 30.0
    last_reinforced_at: str = ""

    @property
    def effective_confidence(self) -> float:
        """Applies Ebbinghaus Forgetting Curve: R = e^(-t / S)."""
        ref_date = self.last_reinforced_at or self.created_at
        if not ref_date:
            return self.confidence_score
        try:
            last_dt = datetime.fromisoformat(ref_date)
            now = datetime.now(timezone.utc)
            days_elapsed = max(0.0, (now - last_dt).total_seconds() / 86400.0)
            retention = math.exp(-days_elapsed / max(self.strength_days, 1.0))
            return round(max(0.05, self.confidence_score * retention), 3)
        except Exception:
            return self.confidence_score


class MemoryVault:
    """Manages the persistent SQLite database with FTS5, AST fingerprints, and Ebbinghaus confidence decay."""

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
                strength_days REAL NOT NULL DEFAULT 30.0,
                last_reinforced_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
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
            pass

        # Safe schema migration for pre-existing databases
        for col, col_def in [("ast_fingerprint", "TEXT NOT NULL DEFAULT ''")]:
            try:
                conn.execute(f"ALTER TABLE episodes ADD COLUMN {col} {col_def};")
            except Exception:
                pass
            try:
                conn.execute(f"ALTER TABLE heuristics ADD COLUMN {col} {col_def};")
            except Exception:
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
        strength_days: float = 30.0,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO heuristics (
                    category, pattern, rule_text, ast_fingerprint, confidence_score, strength_days, last_reinforced_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (category, pattern, rule_text, ast_fingerprint, confidence_score, strength_days, now, now),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            if self._persistent_conn is None:
                conn.close()

    def reinforce_heuristic(self, heuristic_id: int) -> bool:
        """Strengthens heuristic memory under repetition (increasing strength S)."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE heuristics
                SET strength_days = strength_days * 1.5,
                    last_reinforced_at = ?,
                    confidence_score = MIN(1.0, confidence_score + 0.05)
                WHERE id = ?
                """,
                (now, heuristic_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if self._persistent_conn is None:
                conn.close()

    def search_episodes_bm25(self, query: str, limit: int = 5) -> List[Episode]:
        """Runs SQLite3 FTS5 full-text search with BM25 ranking."""
        conn = self._get_connection()
        try:
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
                    ast_fingerprint=r["ast_fingerprint"] if "ast_fingerprint" in r.keys() else "",
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
        """Finds heuristics with identical normalized AST structural fingerprint, sorted by effective confidence."""
        if not fingerprint:
            return []
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM heuristics WHERE ast_fingerprint = ?",
                (fingerprint,),
            ).fetchall()
            rules = [
                HeuristicRule(
                    id=r["id"],
                    category=r["category"],
                    pattern=r["pattern"],
                    rule_text=r["rule_text"],
                    ast_fingerprint=r["ast_fingerprint"] if "ast_fingerprint" in r.keys() else "",
                    confidence_score=r["confidence_score"],
                    strength_days=r["strength_days"] if "strength_days" in r.keys() else 30.0,
                    last_reinforced_at=r["last_reinforced_at"] if "last_reinforced_at" in r.keys() else "",
                    created_at=r["created_at"],
                )
                for r in rows
            ]
            rules.sort(key=lambda x: x.effective_confidence, reverse=True)
            return rules
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
                    ast_fingerprint=r["ast_fingerprint"] if "ast_fingerprint" in r.keys() else "",
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
            rows = conn.execute("SELECT * FROM heuristics").fetchall()
            rules = [
                HeuristicRule(
                    id=r["id"],
                    category=r["category"],
                    pattern=r["pattern"],
                    rule_text=r["rule_text"],
                    ast_fingerprint=r["ast_fingerprint"] if "ast_fingerprint" in r.keys() else "",
                    confidence_score=r["confidence_score"],
                    strength_days=r["strength_days"] if "strength_days" in r.keys() else 30.0,
                    last_reinforced_at=r["last_reinforced_at"] if "last_reinforced_at" in r.keys() else "",
                    created_at=r["created_at"],
                )
                for r in rows
            ]
            rules.sort(key=lambda x: x.effective_confidence, reverse=True)
            return rules
        finally:
            if self._persistent_conn is None:
                conn.close()
