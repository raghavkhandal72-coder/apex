#!/usr/bin/env python3
"""
Unit tests for Apex Reverse Engineering & Analysis (REA) subsystem.
Validates Artifact Inspection, Disassembler, and Cryptographic Evidence Ledger.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apex_council.rea import (
    ArtifactInspection,
    DisassemblyResult,
    EvidenceLedger,
    EvidenceRecord,
    disassemble_source,
    disassemble_target,
    inspect_artifact,
)


class TestREASubsystem(unittest.TestCase):
    def test_artifact_inspector_text(self):
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write("def add(a, b): return a + b\n")
            tf_path = tf.name

        try:
            res = inspect_artifact(tf_path)
            self.assertEqual(res.format, "TEXT")
            self.assertFalse(res.is_binary)
            self.assertIn("python", res.metadata.get("language", ""))
            self.assertEqual(len(res.sha256), 64)
        finally:
            if os.path.exists(tf_path):
                os.unlink(tf_path)

    def test_artifact_inspector_binary(self):
        # Create a mock zip / binary file
        with tempfile.NamedTemporaryFile(suffix=".bin", mode="wb", delete=False) as tf:
            tf.write(b"PK\x03\x04\x14\x00\x00\x00" + b"\x00" * 30)
            tf_path = tf.name

        try:
            res = inspect_artifact(tf_path)
            self.assertTrue(res.is_binary)
            self.assertIn(res.format, {"ZIP", "UNKNOWN"})
        finally:
            if os.path.exists(tf_path):
                os.unlink(tf_path)

    def test_disassembler_cpython(self):
        code = "def compute(x):\n    if x > 10:\n        return x * 2\n    return x\n"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tf:
            tf.write(code)
            tf_path = tf.name

        try:
            res = disassemble_target(tf_path)
            self.assertEqual(res.architecture, "cpython-bytecode")
            self.assertGreater(len(res.instructions), 0)
            self.assertGreaterEqual(res.complexity_score, 1)
        finally:
            if os.path.exists(tf_path):
                os.unlink(tf_path)

    def test_evidence_ledger(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "evidence_ledger.jsonl"
            ledger = EvidenceLedger(ledger_file=ledger_file)

            # Record evidence
            rec1 = ledger.record(
                claim="Unit test claim A",
                artifact_path="test_a.py",
                data={"metric": 100},
            )
            self.assertTrue(rec1.evidence_id.startswith("ev_"))
            self.assertIsNotNone(rec1.signature)

            # Record child evidence
            rec2 = ledger.record(
                claim="Unit test claim B",
                artifact_path="test_b.py",
                data={"metric": 200},
                parent_evidence_id=rec1.evidence_id,
            )
            self.assertEqual(rec2.parent_evidence_id, rec1.evidence_id)

            # Verify ledger integrity
            is_valid, count, msg = ledger.verify_chain()
            self.assertTrue(is_valid)
            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
