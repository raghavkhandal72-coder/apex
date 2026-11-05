"""Cryptographic Evidence Ledger for REA findings.
Manages immutable, hash-chained evidence records (ev_<sha256>).
100% pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import EvidenceRecord


class EvidenceLedger:
    """Append-only cryptographic ledger tracking reverse-engineering findings."""

    def __init__(self, ledger_file: Optional[Union[str, Path]] = None) -> None:
        self.ledger_file = Path(ledger_file) if ledger_file else None
        self.records: List[EvidenceRecord] = []
        self._by_id: Dict[str, EvidenceRecord] = {}

        if self.ledger_file and self.ledger_file.exists():
            self.load(self.ledger_file)

    def _canonical_bytes(
        self,
        claim: str,
        artifact_path: str,
        sha256: str,
        data: Dict[str, Any],
        timestamp: float,
    ) -> bytes:
        """Produce canonical, deterministic JSON byte representation for hashing."""
        payload = {
            "artifact_path": artifact_path,
            "claim": claim,
            "data": data,
            "sha256": sha256,
            "timestamp": round(timestamp, 4),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

    def record(
        self,
        claim: str,
        artifact_path: str,
        data: Optional[Dict[str, Any]] = None,
        inferences: Optional[List[str]] = None,
        unknowns: Optional[List[str]] = None,
        parent_evidence_id: Optional[str] = None,
    ) -> EvidenceRecord:
        """Create and append an immutable EvidenceRecord to the ledger."""
        data_dict = data or {}
        now = time.time()
        iso_str = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()

        # Target artifact digest or hash of data
        art_hash = data_dict.get("sha256")
        if not art_hash:
            if Path(artifact_path).exists():
                art_hash = hashlib.sha256(Path(artifact_path).read_bytes()).hexdigest()
            else:
                art_hash = hashlib.sha256(artifact_path.encode("utf-8")).hexdigest()

        canonical_raw = self._canonical_bytes(claim, artifact_path, art_hash, data_dict, now)
        evidence_hash = hashlib.sha256(canonical_raw).hexdigest()
        evidence_id = f"ev_{evidence_hash}"

        # Determine parent evidence ID
        actual_parent = parent_evidence_id
        if actual_parent is None and self.records:
            actual_parent = self.records[-1].evidence_id

        # Cryptographic signature chain
        prev_sig = self.records[-1].signature if self.records else "GENESIS"
        sig_raw = f"{prev_sig}:{evidence_id}:{evidence_hash}".encode("utf-8")
        signature = hashlib.sha256(sig_raw).hexdigest()

        record = EvidenceRecord(
            evidence_id=evidence_id,
            claim=claim,
            artifact_path=str(artifact_path),
            sha256=art_hash,
            timestamp=now,
            iso_timestamp=iso_str,
            data=data_dict,
            inferences=inferences or [],
            unknowns=unknowns or [],
            parent_evidence_id=actual_parent,
            signature=signature,
        )

        self.records.append(record)
        self._by_id[evidence_id] = record

        if self.ledger_file:
            self._append_to_file(record)

        return record

    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        """Lookup evidence record by ID."""
        return self._by_id.get(evidence_id)

    def list_records(self, artifact_path: Optional[str] = None) -> List[EvidenceRecord]:
        """List all records, optionally filtered by artifact path."""
        if artifact_path is None:
            return list(self.records)
        return [r for r in self.records if r.artifact_path == artifact_path]

    def verify_record(self, record: EvidenceRecord) -> bool:
        """Verify hash integrity of an individual record."""
        raw = self._canonical_bytes(
            record.claim,
            record.artifact_path,
            record.sha256,
            record.data,
            record.timestamp,
        )
        expected_id = f"ev_{hashlib.sha256(raw).hexdigest()}"
        return record.evidence_id == expected_id

    def verify_chain(self) -> Tuple[bool, int, str]:
        """Walk ledger from genesis to tip, verifying hash integrity and cryptographic chain."""
        if not self.records:
            return True, 0, "Ledger is empty"

        prev_sig = "GENESIS"
        prev_id: Optional[str] = None

        for idx, rec in enumerate(self.records):
            # Check parent ID linkage
            if rec.parent_evidence_id != prev_id:
                return False, idx, f"Parent evidence ID broken at index {idx} (expected {prev_id}, got {rec.parent_evidence_id})"

            # Check evidence ID hash integrity
            raw = self._canonical_bytes(
                rec.claim,
                rec.artifact_path,
                rec.sha256,
                rec.data,
                rec.timestamp,
            )
            raw_hash = hashlib.sha256(raw).hexdigest()
            expected_id = f"ev_{raw_hash}"
            if rec.evidence_id != expected_id:
                return False, idx, f"Evidence ID tampered at index {idx} ({rec.evidence_id} != {expected_id})"

            # Check signature chaining
            sig_raw = f"{prev_sig}:{rec.evidence_id}:{raw_hash}".encode("utf-8")
            expected_sig = hashlib.sha256(sig_raw).hexdigest()
            if rec.signature != expected_sig:
                return False, idx, f"Cryptographic signature broken at index {idx}"

            prev_sig = rec.signature
            prev_id = rec.evidence_id

        return True, len(self.records), f"All {len(self.records)} records intact and verified"

    def export_bundle(self, output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Export ledger contents as a structured REA Evidence Bundle."""
        valid, count, msg = self.verify_chain()
        bundle = {
            "schema_version": "1.0.0",
            "generator": "apex-council.rea",
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_records": count,
            "chain_verified": valid,
            "verification_status": msg,
            "records": [r.to_dict() for r in self.records],
        }

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")

        return bundle

    def save(self, path: Union[str, Path]) -> None:
        """Save entire ledger to JSONL file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec.to_dict(), default=str) + "\n")

    def load(self, path: Union[str, Path]) -> None:
        """Load ledger records from JSONL file."""
        p = Path(path)
        if not p.exists():
            return

        self.records.clear()
        self._by_id.clear()

        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                rec = EvidenceRecord(**d)
                self.records.append(rec)
                self._by_id[rec.evidence_id] = rec

    def _append_to_file(self, record: EvidenceRecord) -> None:
        """Append single record to ledger file."""
        if not self.ledger_file:
            return
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")
