#!/usr/bin/env python3
"""
Apex-Sovereign: GBrain Multi-Session Context & Memory Engine
Inspired by garrytan/gbrain (Garry's Agent Brain)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class GBrainFact:
    fact_id: int
    key: str
    text: str
    source: str
    tags: str
    confidence: float
    created_at: float
    updated_at: float
    is_withdrawn: bool = False


class GBrainEngine:
    """
    Persistent cross-session knowledge brain with source attribution,
    corrections, memory locking, and sub-millisecond retrieval.
    """

    def __init__(self, db_path: str = ".apex/gbrain.db") -> None:
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gbrain_facts (
                    fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    is_withdrawn INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gbrain_locks (
                    lock_name TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    acquired_at REAL NOT NULL
                )
            """)
            conn.commit()

    def store_fact(
        self,
        key: str,
        text: str,
        source: str = "agent_session",
        tags: str = "general",
        confidence: float = 1.0,
    ) -> int:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO gbrain_facts (key, text, source, tags, confidence, created_at, updated_at, is_withdrawn)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (key, text, source, tags, confidence, now, now))
            conn.commit()
            return cursor.lastrowid

    def recall_facts(self, query: str = "", limit: int = 10, include_withdrawn: bool = False) -> List[GBrainFact]:
        with self._get_connection() as conn:
            if not query:
                clause = "" if include_withdrawn else "WHERE is_withdrawn = 0"
                rows = conn.execute(f"SELECT * FROM gbrain_facts {clause} ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
            else:
                keywords = [f"%{w.lower()}%" for w in query.split() if len(w) > 2]
                if not keywords:
                    keywords = [f"%{query.lower()}%"]
                conditions = " OR ".join(["LOWER(text) LIKE ? OR LOWER(key) LIKE ? OR LOWER(tags) LIKE ?"] * len(keywords))
                params = []
                for kw in keywords:
                    params.extend([kw, kw, kw])
                withdrawn_clause = "" if include_withdrawn else "AND is_withdrawn = 0"
                sql = f"SELECT * FROM gbrain_facts WHERE ({conditions}) {withdrawn_clause} ORDER BY updated_at DESC LIMIT ?"
                params.append(limit)
                rows = conn.execute(sql, params).fetchall()

            facts = []
            for r in rows:
                facts.append(
                    GBrainFact(
                        fact_id=r["fact_id"],
                        key=r["key"],
                        text=r["text"],
                        source=r["source"],
                        tags=r["tags"],
                        confidence=r["confidence"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        is_withdrawn=bool(r["is_withdrawn"]),
                    )
                )
            return facts

    def correct_fact(self, fact_id: int, new_text: str) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE gbrain_facts SET text = ?, updated_at = ? WHERE fact_id = ?
            """, (new_text, now, fact_id))
            conn.commit()
            return cursor.rowcount > 0

    def withdraw_fact(self, fact_id: int) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE gbrain_facts SET is_withdrawn = 1, updated_at = ? WHERE fact_id = ?
            """, (now, fact_id))
            conn.commit()
            return cursor.rowcount > 0

    def acquire_lock(self, lock_name: str = "global_brain", session_id: str = "default_session", ttl_s: float = 30.0) -> bool:
        now = time.time()
        with self._get_connection() as conn:
            # Check existing lock
            row = conn.execute("SELECT session_id, acquired_at FROM gbrain_locks WHERE lock_name = ?", (lock_name,)).fetchone()
            if row:
                if now - row["acquired_at"] > ttl_s:
                    # Expired lock -> take over
                    conn.execute("UPDATE gbrain_locks SET session_id = ?, acquired_at = ? WHERE lock_name = ?", (session_id, now, lock_name))
                    conn.commit()
                    return True
                return row["session_id"] == session_id
            else:
                conn.execute("INSERT INTO gbrain_locks (lock_name, session_id, acquired_at) VALUES (?, ?, ?)", (lock_name, session_id, now))
                conn.commit()
                return True

    def release_lock(self, lock_name: str = "global_brain", session_id: str = "default_session") -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM gbrain_locks WHERE lock_name = ? AND session_id = ?", (lock_name, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def export_context_for_prompt(self, query: str = "", limit: int = 5) -> str:
        facts = self.recall_facts(query, limit=limit)
        if not facts:
            return ""
        lines = ["## GBrain Institutional Knowledge (Persistent Context):"]
        for f in facts:
            lines.append(f"- [{f.key}] {f.text} (Source: {f.source})")
        return "\n".join(lines)
