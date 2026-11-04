"""Cryptographic Hash-Chained Tamper-Evident Audit Ledger.
Chains every autonomous swarm event, mutation test, and signed commit like a blockchain block.
Pure Python standard library implementation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


GENESIS_PREV_HASH = "0" * 64
DEFAULT_LEDGER_SECRET = b"apex-sovereign-audit-chain-secret-key-v2"


@dataclass
class AuditBlock:
    index: int
    timestamp: str
    action: str
    actor: str
    payload_hash: str
    details: Dict[str, Any]
    prev_hash: str
    block_hash: str


class CryptographicLedger:
    """Tamper-evident HMAC-SHA512 blockchain-style audit ledger."""

    def __init__(
        self,
        ledger_path: Path | str = ".apex/audit_chain.jsonl",
        secret_key: bytes = DEFAULT_LEDGER_SECRET,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.secret_key = secret_key
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self._init_genesis()

    @staticmethod
    def compute_sha256(content: str | bytes) -> str:
        b = content.encode("utf-8") if isinstance(content, str) else content
        return hashlib.sha256(b).hexdigest()

    def _calculate_block_hash(
        self,
        index: int,
        timestamp: str,
        action: str,
        actor: str,
        payload_hash: str,
        prev_hash: str,
    ) -> str:
        raw_msg = f"{index}|{timestamp}|{action}|{actor}|{payload_hash}|{prev_hash}"
        return hmac.new(self.secret_key, raw_msg.encode("utf-8"), hashlib.sha512).hexdigest()

    def _init_genesis(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        payload_hash = self.compute_sha256("APEX_SOVEREIGN_GENESIS_BLOCK")
        block_hash = self._calculate_block_hash(
            index=0,
            timestamp=now,
            action="GENESIS",
            actor="SYSTEM",
            payload_hash=payload_hash,
            prev_hash=GENESIS_PREV_HASH,
        )
        genesis = AuditBlock(
            index=0,
            timestamp=now,
            action="GENESIS",
            actor="SYSTEM",
            payload_hash=payload_hash,
            details={"msg": "Apex-Sovereign Cryptographic Ledger Initialized"},
            prev_hash=GENESIS_PREV_HASH,
            block_hash=block_hash,
        )
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(asdict(genesis)) + "\n")

    def get_latest_block(self) -> AuditBlock:
        if not self.ledger_path.exists():
            self._init_genesis()
        last_line = ""
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if not last_line:
            self._init_genesis()
            return self.get_latest_block()
        data = json.loads(last_line)
        return AuditBlock(**data)

    def record_event(
        self,
        action: str,
        actor: str,
        payload: str | bytes | Dict[str, Any],
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditBlock:
        latest = self.get_latest_block()
        now = datetime.now(timezone.utc).isoformat()
        new_index = latest.index + 1
        
        if isinstance(payload, dict):
            payload_str = json.dumps(payload, sort_keys=True)
        elif isinstance(payload, bytes):
            payload_str = payload.hex()
        else:
            payload_str = str(payload)

        payload_hash = self.compute_sha256(payload_str)
        prev_hash = latest.block_hash

        block_hash = self._calculate_block_hash(
            index=new_index,
            timestamp=now,
            action=action,
            actor=actor,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
        )

        new_block = AuditBlock(
            index=new_index,
            timestamp=now,
            action=action,
            actor=actor,
            payload_hash=payload_hash,
            details=details or {},
            prev_hash=prev_hash,
            block_hash=block_hash,
        )

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(new_block)) + "\n")

        return new_block

    def verify_chain(self) -> Tuple[bool, int, str]:
        """Validates all blocks from genesis to tip.
        Returns: (is_valid: bool, total_blocks: int, error_message: str)
        """
        if not self.ledger_path.exists():
            return False, 0, "Ledger file does not exist"

        expected_prev_hash = GENESIS_PREV_HASH
        block_count = 0

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    block = AuditBlock(**data)
                except Exception as ex:
                    return False, block_count, f"Block #{line_idx} malformed JSON: {str(ex)}"

                if block.index != line_idx:
                    return False, block_count, f"Block index discontinuity: expected #{line_idx}, found #{block.index}"

                if block.prev_hash != expected_prev_hash:
                    return False, block_count, f"Hash chain break at block #{block.index}: prev_hash mismatch"

                # Recompute HMAC-SHA512
                recalculated = self._calculate_block_hash(
                    index=block.index,
                    timestamp=block.timestamp,
                    action=block.action,
                    actor=block.actor,
                    payload_hash=block.payload_hash,
                    prev_hash=block.prev_hash,
                )

                if recalculated != block.block_hash:
                    return False, block_count, f"Cryptographic tamper detected in block #{block.index}: hash mismatch"

                expected_prev_hash = block.block_hash
                block_count += 1

        return True, block_count, "All cryptographic hash chains verified and intact."
