import tempfile
import unittest
from pathlib import Path

from apex_council.security.ledger import CryptographicLedger


class TestCryptographicLedger(unittest.TestCase):
    def test_ledger_genesis_and_chaining(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "audit_chain.jsonl"
            ledger = CryptographicLedger(ledger_path=ledger_file)

            # Genesis should be present
            latest = ledger.get_latest_block()
            self.assertEqual(latest.index, 0)
            self.assertEqual(latest.action, "GENESIS")

            # Record two events
            b1 = ledger.record_event(
                action="ARCHITECT_SPEC",
                actor="StaffArchitect",
                payload="Blueprint created",
                details={"symbols": ["lock_manager.py"]},
            )
            self.assertEqual(b1.index, 1)
            self.assertEqual(b1.prev_hash, latest.block_hash)

            b2 = ledger.record_event(
                action="GATEKEEPER_SIGN",
                actor="SovereignGatekeeper",
                payload="def safe(): return 42",
                details={"status": "PASSED"},
            )
            self.assertEqual(b2.index, 2)
            self.assertEqual(b2.prev_hash, b1.block_hash)

            # Verify entire chain
            valid, count, msg = ledger.verify_chain()
            self.assertTrue(valid)
            self.assertEqual(count, 3)  # Genesis + 2 events

    def test_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_file = Path(tmpdir) / "audit_chain.jsonl"
            ledger = CryptographicLedger(ledger_path=ledger_file)

            ledger.record_event(action="PATCH", actor="ModelA", payload="a = 1")
            ledger.record_event(action="SIGN", actor="Gatekeeper", payload="b = 2")

            # Verify initially clean
            valid, _, _ = ledger.verify_chain()
            self.assertTrue(valid)

            # Malicious tamper: edit block 1 text
            lines = ledger_file.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1].replace("ModelA", "HackerActor")
            ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

            # Verification MUST fail!
            valid_after_tamper, count, err = ledger.verify_chain()
            self.assertFalse(valid_after_tamper)
            self.assertIn("tamper detected", err.lower())


if __name__ == "__main__":
    unittest.main()
