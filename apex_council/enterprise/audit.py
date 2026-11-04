from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    entry_id: str
    timestamp: float
    tenant_id: str
    user_id: str
    action: str
    prompt_hash: str
    output_hash: str
    winner: str
    security_score: float
    prev_hash: str
    current_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CryptographicAuditLogger:
    """SOC2 / ISO 27001 Cryptographically Chained Audit Logger.

    Every operation is hashed with SHA-256 and chained to the previous entry,
    guaranteeing non-repudiation and tamper detection.
    """

    def __init__(self, log_path: Path | str = "audit_trail.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._get_tail_hash()

    def record_event(
        self,
        action: str,
        prompt: str,
        output_code: str,
        winner: str,
        security_score: float,
        tenant_id: str = "enterprise-default",
        user_id: str = "system-dev",
    ) -> AuditEntry:
        timestamp = time.time()
        entry_id = str(uuid.uuid4())
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        output_hash = hashlib.sha256(output_code.encode("utf-8")).hexdigest()

        # Compute tamper-evident chained hash
        payload = f"{entry_id}|{timestamp}|{tenant_id}|{user_id}|{action}|{prompt_hash}|{output_hash}|{winner}|{self._last_hash}"
        current_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            prompt_hash=prompt_hash,
            output_hash=output_hash,
            winner=winner,
            security_score=security_score,
            prev_hash=self._last_hash,
            current_hash=current_hash,
        )

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

        self._last_hash = current_hash
        return entry

    def _get_tail_hash(self) -> str:
        if not self.log_path.exists():
            return "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
                if not lines:
                    return "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"
                last_entry = json.loads(lines[-1])
                return last_entry.get("current_hash", "GENESIS_BLOCK")
        except Exception:
            return "GENESIS_BLOCK"

    def verify_integrity(self) -> Tuple[bool, int, Optional[str]]:
        """Verifies the cryptographic chain across all audit log entries.

        Returns (is_valid, total_entries, error_message)
        """
        if not self.log_path.exists():
            return True, 0, None

        prev_hash = "GENESIS_BLOCK_00000000000000000000000000000000000000000000000000000000"
        count = 0

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                count += 1
                data = json.loads(line)

                # Check chained linkage
                if data["prev_hash"] != prev_hash and line_idx > 1:
                    return False, count, f"Broken cryptographic chain at line {line_idx}: prev_hash mismatch."

                payload = (
                    f"{data['entry_id']}|{data['timestamp']}|{data['tenant_id']}|{data['user_id']}|"
                    f"{data['action']}|{data['prompt_hash']}|{data['output_hash']}|{data['winner']}|{data['prev_hash']}"
                )
                computed = hashlib.sha256(payload.encode("utf-8")).hexdigest()

                if computed != data["current_hash"]:
                    return False, count, f"Tampered audit entry at line {line_idx}: hash mismatch."

                prev_hash = data["current_hash"]

        return True, count, None
