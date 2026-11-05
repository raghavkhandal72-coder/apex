#!/usr/bin/env python3
"""
Apex-Sovereign: Cognitive Memory Stream & Knowledge Graph
Inspired by claude-mem & everything-claude-code
100% Pure Python Standard Library | Zero Dependencies

Maintains persistent episodic and semantic engineering memory across sessions.
Extracts architectural invariants, bug repair patterns, and code conventions,
exporting structured CLAUDE.md / AGENTS.md prompt caches.
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import re
from typing import Any, Dict, List, Optional, Set


@dataclasses.dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    category: str  # "architectural_invariant", "bug_pattern", "test_convention", "api_quirk"
    title: str
    description: str
    code_example: Optional[str]
    tags: List[str]
    created_at: str
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryRecord":
        return cls(**data)


class CognitiveMemoryStream:
    """
    Persistent memory engine storing institutional knowledge in `.git/apex_memory.json`.
    Provides BM25-style lexical relevance search and generates markdown context guides.
    """

    def __init__(self, storage_path: Optional[str | pathlib.Path] = None) -> None:
        if storage_path:
            self.storage_path = pathlib.Path(storage_path).resolve()
        else:
            # Default to .git/apex_memory.json if in git repo, else current dir
            if pathlib.Path(".git").exists():
                self.storage_path = pathlib.Path(".git/apex_memory.json").resolve()
            else:
                self.storage_path = pathlib.Path(".apex_memory.json").resolve()

        self._records: Dict[str, MemoryRecord] = {}
        self.load()

    def load(self) -> int:
        """Loads records from the JSON store."""
        if not self.storage_path.exists():
            return 0
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            records = payload.get("records", [])
            for item in records:
                rec = MemoryRecord.from_dict(item)
                self._records[rec.record_id] = rec
            return len(self._records)
        except (OSError, json.JSONDecodeError):
            return 0

    def save(self) -> None:
        """Persists records atomically to the JSON store."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0-cognitive",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_records": len(self._records),
            "records": [rec.to_dict() for rec in self._records.values()],
        }
        tmp_file = self.storage_path.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_file, self.storage_path)

    def record_pattern(
        self,
        category: str,
        title: str,
        description: str,
        code_example: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: float = 1.0,
    ) -> MemoryRecord:
        """Creates or updates a memory record."""
        tag_list = sorted(list(set(tags or [])))
        content_for_hash = f"{category}:{title}:{description}:{code_example or ''}"
        record_id = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()[:16]

        rec = MemoryRecord(
            record_id=record_id,
            category=category,
            title=title.strip(),
            description=description.strip(),
            code_example=code_example.strip() if code_example else None,
            tags=tag_list,
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._records[record_id] = rec
        self.save()
        return rec

    def search(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        """
        Token-overlap relevance search ranking records against the query.
        """
        query_tokens = set(re.findall(r"\w+", query.lower()))
        if not query_tokens:
            return list(self._records.values())[:top_k]

        scored: List[Tuple[float, MemoryRecord]] = []
        for rec in self._records.values():
            text = f"{rec.title} {rec.description} {' '.join(rec.tags)} {rec.code_example or ''}".lower()
            doc_tokens = set(re.findall(r"\w+", text))
            if not doc_tokens:
                continue

            intersection = query_tokens.intersection(doc_tokens)
            if not intersection:
                continue

            # Jaccard + confidence weighting
            score = (len(intersection) / len(query_tokens.union(doc_tokens))) * rec.confidence
            scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored[:top_k]]

    def synthesize_claude_md(self, output_file: Optional[str | pathlib.Path] = None) -> str:
        """
        Synthesizes a high-density, cache-optimized `CLAUDE.md` / `AGENTS.md` context document
        containing all institutional memory, architectural invariants, and test conventions.
        """
        lines = [
            "# CLAUDE.md — Institutional Architecture & Engineering Invariants",
            "> Auto-synthesized by Apex-Sovereign Cognitive Memory Stream",
            "",
            "## 1. Architectural Invariants",
        ]

        invariants = [r for r in self._records.values() if r.category == "architectural_invariant"]
        if invariants:
            for inv in invariants:
                lines.append(f"- **{inv.title}**: {inv.description}")
                if inv.code_example:
                    lines.append(f"  ```python\n  {inv.code_example}\n  ```")
        else:
            lines.append("- *Zero external third-party dependencies (`pip = 0`). 100% Pure Python standard library.*")
            lines.append("- *Direct Git object DAG operations via ephemeral `GIT_INDEX_FILE`.*")

        lines.extend(["", "## 2. Known Bug Repair Patterns & Anti-Patterns"])
        bug_patterns = [r for r in self._records.values() if r.category == "bug_pattern"]
        if bug_patterns:
            for bp in bug_patterns:
                lines.append(f"- **{bp.title}**: {bp.description}")
                if bp.code_example:
                    lines.append(f"  ```python\n  {bp.code_example}\n  ```")
        else:
            lines.append("- *Off-by-one upper bounds in binary searches (`high = len(arr) - 1`).*")
            lines.append("- *ReDoS nested quantifiers `(a+)+` require non-backtracking atomic groups or bounded iterations.*")

        lines.extend(["", "## 3. Testing Conventions & Invariants"])
        test_convs = [r for r in self._records.values() if r.category == "test_convention"]
        if test_convs:
            for tc in test_convs:
                lines.append(f"- **{tc.title}**: {tc.description}")
        else:
            lines.append("- *All tests must run via `python -m unittest discover -s tests -v` with zero mock frameworks.*")
            lines.append("- *Tests must be hermetic and execute in under 100ms per unit test.*")

        content = "\n".join(lines) + "\n"

        if output_file:
            out_p = pathlib.Path(output_file).resolve()
            with open(out_p, "w", encoding="utf-8") as f:
                f.write(content)

        return content
