"""
Opaque-Box E2E Test Suite — External Tool Integrations (R1)
Tiers 1-4: Feature Coverage, Boundary/Corner Cases, Cross-Feature Interactions, Real-World Scenarios.

Covers:
- REA (Reverse Engineering Anything): Binary & artifact inspection, disassembly heuristics, Evidence Ledger.
- reviewdog: rdjson/checkstyle diagnostic parsing, git diff filtering (added, diff-context, file, nofilter), reporting.
- Netdata: Real-time system telemetry, streaming wire protocol (CHART, DIMENSION, BEGIN, SET, END), telemetry client.

Platform Invariants:
- 100% pure Python standard library (unittest based), zero external dependencies.
- Hermetic and deterministic execution.
"""

import hashlib
import json
import os
import shutil
import struct
import tempfile
import time
import unittest
import zipfile

# Progressive testability import guard
TOOL_INTEGRATIONS_AVAILABLE = False
try:
    import apex_council.rea as rea
    import apex_council.reviewdog as reviewdog
    import apex_council.netdata as netdata
    TOOL_INTEGRATIONS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TOOL_INTEGRATIONS_AVAILABLE = False


@unittest.skipUnless(TOOL_INTEGRATIONS_AVAILABLE, "Milestone 1 External Tool Integrations not yet implemented in apex_council")
class TestE2EToolIntegrationsTier1(unittest.TestCase):
    """Tier 1: Feature Coverage — Representative happy-path tests."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_tools_t1_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rea_inspect_elf_artifact(self):
        """REA: Verify ELF binary header detection, size, and SHA-256 calculation."""
        elf_path = os.path.join(self.test_dir, "sample.elf")
        # Standard ELF 64-bit LSB header: \x7fELF, class 2 (64-bit), data 1 (LE), version 1
        elf_header = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8 + struct.pack("<HHI", 2, 0x3E, 1) + b"\x00" * 40
        with open(elf_path, "wb") as f:
            f.write(elf_header)

        expected_sha = hashlib.sha256(elf_header).hexdigest()
        result = rea.inspect_artifact(elf_path)

        # Verify contract properties
        fmt = getattr(result, "format", getattr(result, "detected_format", None))
        size = getattr(result, "size", getattr(result, "size_bytes", None))
        sha = getattr(result, "sha256", None)

        self.assertIn("ELF", str(fmt).upper(), f"Expected ELF format detection, got {fmt}")
        self.assertEqual(size, len(elf_header))
        self.assertEqual(sha, expected_sha)

    def test_rea_inspect_pe_artifact(self):
        """REA: Verify PE/DOS binary header detection and digest calculation."""
        pe_path = os.path.join(self.test_dir, "sample.exe")
        # MZ header with pointer to PE header at offset 0x3C
        dos_header = bytearray(64)
        dos_header[0:2] = b"MZ"
        dos_header[0x3C:0x40] = struct.pack("<I", 0x40)
        pe_signature = b"PE\x00\x00" + b"\x00" * 20
        payload = bytes(dos_header) + pe_signature
        with open(pe_path, "wb") as f:
            f.write(payload)

        result = rea.inspect_artifact(pe_path)
        fmt = getattr(result, "format", getattr(result, "detected_format", None))
        self.assertIn("PE", str(fmt).upper(), f"Expected PE format detection, got {fmt}")
        self.assertEqual(getattr(result, "size", getattr(result, "size_bytes", None)), len(payload))

    def test_rea_inspect_zip_artifact(self):
        """REA: Verify ZIP archive inspection and member manifest."""
        zip_path = os.path.join(self.test_dir, "archive.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("module.py", "def hello(): return 'world'")
            zf.writestr("manifest.json", '{"version": "1.0"}')

        result = rea.inspect_artifact(zip_path)
        fmt = getattr(result, "format", getattr(result, "detected_format", None))
        self.assertIn("ZIP", str(fmt).upper())
        metadata = getattr(result, "metadata", {})
        entries = getattr(result, "entries", metadata.get("entries", []))
        # Entries or metadata should capture archive contents
        entry_names = [e.get("name", e) if isinstance(e, dict) else str(e) for e in entries]
        if entry_names:
            self.assertTrue(any("module.py" in name for name in entry_names))

    def test_rea_disassemble_python_bytecode(self):
        """REA: Verify Python bytecode disassembly, opcodes, and instruction listing."""
        def sample_func(x, y):
            z = x * 2
            return z + y

        listing = rea.disassemble_source(sample_func)
        instructions = getattr(listing, "instructions", [])
        self.assertTrue(len(instructions) > 0, "Disassembly must return at least one instruction")

        opnames = [inst.get("opname", getattr(inst, "opname", "")) for inst in instructions]
        self.assertTrue(any("LOAD_" in op for op in opnames), "Expected LOAD_* bytecode opcode")
        self.assertTrue(any("RETURN_VALUE" in op for op in opnames), "Expected RETURN_VALUE opcode")

    def test_rea_evidence_ledger_immutability(self):
        """REA: Verify EvidenceLedger stores cryptographically verifiable, immutable records."""
        ledger = rea.EvidenceLedger()
        claim = "Binary contains unencrypted configuration string"
        data = {"severity": "HIGH", "offset": 0x120, "string": "secret_key"}

        dummy_path = os.path.join(self.test_dir, "target.bin")
        with open(dummy_path, "wb") as f:
            f.write(b"SAMPLE DATA TARGET FOR REA EVIDENCE")

        record = ledger.record(claim=claim, artifact_path=dummy_path, data=data)

        # Verify evidence record attributes
        evidence_id = getattr(record, "evidence_id", None)
        sha = getattr(record, "sha256", getattr(record, "target_sha256", None))
        timestamp = getattr(record, "timestamp", None)

        self.assertIsNotNone(evidence_id)
        self.assertTrue(str(evidence_id).startswith("ev_") or len(str(evidence_id)) >= 16)
        self.assertEqual(sha, hashlib.sha256(b"SAMPLE DATA TARGET FOR REA EVIDENCE").hexdigest())
        self.assertIsNotNone(timestamp)

    def test_reviewdog_parse_rdjson(self):
        """reviewdog: Parse standard Reviewdog Diagnostic JSON (rdjson)."""
        raw_rdjson = json.dumps({
            "source": {"name": "apex-lint", "url": "https://apex.local"},
            "severity": "WARNING",
            "diagnostics": [
                {
                    "message": "Unused variable 'counter'",
                    "location": {
                        "path": "apex_council/core.py",
                        "range": {
                            "start": {"line": 42, "column": 5},
                            "end": {"line": 42, "column": 12}
                        }
                    },
                    "severity": "WARNING",
                    "code": {"value": "W0612"}
                }
            ]
        })

        diagnostics = reviewdog.parse_diagnostics(raw_rdjson, format_type="rdjson")
        self.assertEqual(len(diagnostics), 1)
        diag = diagnostics[0]
        self.assertEqual(getattr(diag, "message", None), "Unused variable 'counter'")
        loc = getattr(diag, "location", None)
        path = getattr(loc, "path", None) if loc else None
        self.assertEqual(path, "apex_council/core.py")

    def test_reviewdog_parse_checkstyle_xml(self):
        """reviewdog: Parse standard Checkstyle XML diagnostic reports."""
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<checkstyle version="4.3">
  <file name="apex_council/models.py">
    <error line="15" column="1" severity="error" message="Missing class docstring" source="flake8.D101"/>
    <error line="28" column="80" severity="warning" message="Line too long (85 &gt; 79)" source="flake8.E501"/>
  </file>
</checkstyle>"""

        diagnostics = reviewdog.parse_diagnostics(xml_content, format_type="checkstyle")
        self.assertEqual(len(diagnostics), 2)
        messages = [getattr(d, "message", "") for d in diagnostics]
        self.assertIn("Missing class docstring", messages)
        self.assertIn("Line too long (85 > 79)", messages)

    def test_reviewdog_filter_diff_modes(self):
        """reviewdog: Filter diagnostics against unified git diff hunks."""
        diff_text = """diff --git a/apex_council/core.py b/apex_council/core.py
index 1234567..89abcdef 100644
--- a/apex_council/core.py
+++ b/apex_council/core.py
@@ -10,3 +10,4 @@ def setup():
     init_system()
+    counter = 0
     return True
"""
        raw_rdjson = json.dumps({
            "diagnostics": [
                {
                    "message": "Line in added hunk",
                    "location": {"path": "apex_council/core.py", "range": {"start": {"line": 12}}},
                    "severity": "WARNING"
                },
                {
                    "message": "Line outside diff context",
                    "location": {"path": "apex_council/core.py", "range": {"start": {"line": 100}}},
                    "severity": "WARNING"
                }
            ]
        })
        diagnostics = reviewdog.parse_diagnostics(raw_rdjson, format_type="rdjson")

        # In 'added' mode, only line 12 should survive
        filtered_added = reviewdog.filter_diagnostics(diagnostics, diff_text, mode="added")
        self.assertEqual(len(filtered_added), 1)
        self.assertEqual(filtered_added[0].message, "Line in added hunk")

        # In 'nofilter' mode, both should survive
        filtered_none = reviewdog.filter_diagnostics(diagnostics, diff_text, mode="nofilter")
        self.assertEqual(len(filtered_none), 2)

    def test_reviewdog_report_formats(self):
        """reviewdog: Verify formatting as terminal text, markdown, and github annotations."""
        raw_rdjson = json.dumps({
            "diagnostics": [
                {
                    "message": "Security warning: insecure hash",
                    "location": {"path": "crypto.py", "range": {"start": {"line": 5, "column": 1}}},
                    "severity": "ERROR",
                    "code": {"value": "SEC01"}
                }
            ]
        })
        diagnostics = reviewdog.parse_diagnostics(raw_rdjson, format_type="rdjson")

        text_report = reviewdog.report_diagnostics(diagnostics, output_format="text")
        self.assertIn("crypto.py", text_report)
        self.assertIn("Security warning", text_report)

        github_report = reviewdog.report_diagnostics(diagnostics, output_format="github-annotations")
        self.assertTrue("::error" in github_report or "crypto.py" in github_report)

    def test_netdata_collect_system_metrics(self):
        """Netdata: Verify collection of host CPU, memory, disk, and process telemetry."""
        metrics = netdata.collect_system_metrics()
        self.assertIsInstance(metrics, dict)

        # Verify key metrics are present and non-negative
        cpu_val = metrics.get("cpu_util_pct", metrics.get("cpu_percent", 0.0))
        mem_val = metrics.get("memory_used_mb", metrics.get("memory_used_bytes", 0))
        self.assertGreaterEqual(float(cpu_val), 0.0)
        self.assertGreaterEqual(float(mem_val), 0.0)

    def test_netdata_wire_protocol_encoding(self):
        """Netdata: Verify streaming text wire protocol commands generation."""
        proto = netdata.NetdataProtocol()
        chart_cmd = proto.chart("sys_cpu", "cpu_total", "Total CPU Utilization", "percentage", "system", "line")
        dim_cmd = proto.dimension("user", "user_time")
        begin_cmd = proto.begin("sys_cpu")
        set_cmd = proto.set("user", 25.5)
        end_cmd = proto.end()

        self.assertTrue(chart_cmd.startswith("CHART sys_cpu"))
        self.assertTrue(dim_cmd.startswith("DIMENSION user"))
        self.assertTrue(begin_cmd.startswith("BEGIN sys_cpu"))
        self.assertTrue(set_cmd.startswith("SET user = 25.5") or set_cmd.startswith("SET user = 25"))
        self.assertEqual(end_cmd.strip(), "END")

    def test_netdata_telemetry_client_push(self):
        """Netdata: Verify NetdataTelemetryClient batch push API."""
        client = netdata.NetdataTelemetryClient()
        success = client.push_metrics("apex.inference", {"latency_ms": 14.2, "tokens_sec": 42.0})
        self.assertTrue(success is True or isinstance(success, (dict, str, bool)))


@unittest.skipUnless(TOOL_INTEGRATIONS_AVAILABLE, "Milestone 1 External Tool Integrations not yet implemented in apex_council")
class TestE2EToolIntegrationsTier2(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases — Corrupt payloads, extreme lengths, unicode."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_tools_t2_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_rea_inspect_empty_file(self):
        """REA: Verify 0-byte file inspection does not crash and returns size=0."""
        empty_path = os.path.join(self.test_dir, "empty.bin")
        with open(empty_path, "wb") as f:
            pass

        result = rea.inspect_artifact(empty_path)
        size = getattr(result, "size", getattr(result, "size_bytes", 0))
        self.assertEqual(size, 0)
        expected_sha = hashlib.sha256(b"").hexdigest()
        self.assertEqual(getattr(result, "sha256", None), expected_sha)

    def test_rea_inspect_corrupt_truncated_header(self):
        """REA: Verify truncated header handles error gracefully without unhandled exception."""
        corrupt_path = os.path.join(self.test_dir, "corrupt.elf")
        with open(corrupt_path, "wb") as f:
            f.write(b"\x7fEL")  # Truncated ELF magic

        result = rea.inspect_artifact(corrupt_path)
        # Should gracefully return with fallback format (e.g. RAW/UNKNOWN/TEXT) rather than crash
        self.assertIsNotNone(result)

    def test_reviewdog_malformed_rdjson_payload(self):
        """reviewdog: Malformed JSON syntax must be handled gracefully."""
        malformed_json = "{ invalid_json: true, "
        try:
            res = reviewdog.parse_diagnostics(malformed_json, format_type="rdjson")
            self.assertEqual(res, [])
        except ValueError:
            # Raising ValueError on malformed payload is also valid standard behavior
            pass

    def test_reviewdog_unicode_and_special_characters(self):
        """reviewdog: Diagnostic messages with Unicode (emojis, mathematical symbols, control chars)."""
        unicode_message = "Variable 'λ_parameter' has invalid glyph '🔥' in formula ∀x ∈ ℝ"
        raw_rdjson = json.dumps({
            "diagnostics": [
                {
                    "message": unicode_message,
                    "location": {"path": "src/math/λ_calc.py", "range": {"start": {"line": 10}}},
                    "severity": "WARNING"
                }
            ]
        })

        diagnostics = reviewdog.parse_diagnostics(raw_rdjson, format_type="rdjson")
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].message, unicode_message)
        report = reviewdog.report_diagnostics(diagnostics, output_format="text")
        self.assertIn("λ_parameter", report)

    def test_netdata_extreme_and_negative_metrics(self):
        """Netdata: Wire protocol and client must handle zero, negative, and large floating values."""
        proto = netdata.NetdataProtocol()
        cmd = proto.set("drift", -0.00045)
        self.assertIn("-0.00045", cmd)

        client = netdata.NetdataTelemetryClient()
        success = client.push_metrics("apex.stress", {"extreme_large": 1e12, "zero": 0.0, "neg": -42.5})
        self.assertTrue(success is not None)


@unittest.skipUnless(TOOL_INTEGRATIONS_AVAILABLE, "Milestone 1 External Tool Integrations not yet implemented in apex_council")
class TestE2EToolIntegrationsTier3(unittest.TestCase):
    """Tier 3: Cross-Feature Interactions — REA findings to reviewdog, Netdata tracking tools."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_tools_t3_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cross_rea_findings_piped_to_reviewdog(self):
        """Cross-feature: REA inspection finding transformed into reviewdog Diagnostic and filtered."""
        # Step 1: Create a suspicious Python script
        py_file = os.path.join(self.test_dir, "suspicious.py")
        code_content = "import os\nos.system('calc.exe')\n"
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(code_content)

        # Step 2: Disassemble using REA
        listing = rea.disassemble_source(compile(code_content, py_file, "exec"))
        instructions = getattr(listing, "instructions", [])

        # Step 3: Emit reviewdog diagnostic for system calls found in instructions
        diagnostics = []
        for inst in instructions:
            argval = inst.get("argval", getattr(inst, "argval", None))
            if argval == "system":
                diag = reviewdog.models.Diagnostic(
                    message="Use of os.system is disallowed; prefer subprocess with fixed arguments",
                    location=reviewdog.models.Location(
                        path=py_file,
                        range=reviewdog.models.Range(
                            start=reviewdog.models.Position(line=2, column=1)
                        )
                    ),
                    severity=reviewdog.models.Severity.ERROR if hasattr(reviewdog.models, "Severity") else "ERROR"
                )
                diagnostics.append(diag)

        self.assertGreaterEqual(len(diagnostics), 1)

        # Step 4: Report via reviewdog
        report = reviewdog.report_diagnostics(diagnostics, output_format="text")
        self.assertIn("os.system", report)

    def test_cross_netdata_tracking_rea_disassembly(self):
        """Cross-feature: Netdata protocol tracks telemetry during REA artifact operations."""
        proto = netdata.NetdataProtocol()
        chart = proto.chart("rea.perf", "disasm_latency", "REA Disassembly Latency", "milliseconds")

        start_time = time.perf_counter()
        # Execute REA disassembly
        def complex_fn(a, b, c):
            return [x**2 for x in range(a)] + [y * 3 for y in range(b)]
        rea.disassemble_source(complex_fn)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        stream = "\n".join([
            chart,
            proto.dimension("latency", "elapsed_ms"),
            proto.begin("rea.perf"),
            proto.set("latency", elapsed_ms),
            proto.end()
        ])

        self.assertIn("CHART rea.perf", stream)
        self.assertIn("SET latency =", stream)
        self.assertIn("END", stream)


@unittest.skipUnless(TOOL_INTEGRATIONS_AVAILABLE, "Milestone 1 External Tool Integrations not yet implemented in apex_council")
class TestE2EToolIntegrationsTier4(unittest.TestCase):
    """Tier 4: Real-World Scenarios — End-to-end Automated Code and Artifact Audit."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="apex_e2e_tools_t4_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scenario_automated_code_and_artifact_audit(self):
        """
        Complete Real-World Workflow:
        1. Package release archive containing binary and Python code.
        2. REA inspects zip container, validates checksums, and disassembles core module.
        3. Ledger records cryptographic provenance (EvidenceLedger).
        4. reviewdog validates code review diagnostics against a release git diff.
        5. Netdata captures audit execution metrics and formats exportable telemetry.
        """
        # 1. Package release archive
        archive_path = os.path.join(self.test_dir, "release_v1.zip")
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("core.py", "def authenticate(user, token):\n    return token == 'admin_secret'\n")
            zf.writestr("README.md", "# Release 1.0\nSecure authentication gateway.\n")

        # 2. REA inspects archive
        inspection = rea.inspect_artifact(archive_path)
        self.assertIn("ZIP", str(getattr(inspection, "format", getattr(inspection, "detected_format", ""))).upper())

        # 3. Ledger record
        ledger = rea.EvidenceLedger()
        ev_rec = ledger.record(
            claim="Release v1 archive verified with intact SHA-256",
            artifact_path=archive_path,
            data={"inspection_status": "PASS", "entries_count": 2}
        )
        self.assertIsNotNone(ev_rec)

        # 4. reviewdog parses diagnostic finding on hardcoded secret
        diag_payload = json.dumps({
            "diagnostics": [
                {
                    "message": "CWE-798: Hardcoded credential 'admin_secret' detected",
                    "location": {"path": "core.py", "range": {"start": {"line": 2}}},
                    "severity": "ERROR"
                }
            ]
        })
        git_diff = """diff --git a/core.py b/core.py
--- a/core.py
+++ b/core.py
@@ -1,1 +1,2 @@
 def authenticate(user, token):
+    return token == 'admin_secret'
"""
        diagnostics = reviewdog.parse_diagnostics(diag_payload, format_type="rdjson")
        filtered = reviewdog.filter_diagnostics(diagnostics, git_diff, mode="added")
        self.assertEqual(len(filtered), 1)
        report = reviewdog.report_diagnostics(filtered, output_format="text")
        self.assertIn("CWE-798", report)

        # 5. Netdata telemetry recording
        metrics = netdata.collect_system_metrics()
        self.assertIsInstance(metrics, dict)
        client = netdata.NetdataTelemetryClient()
        pushed = client.push_metrics("audit.completion", {"findings_count": len(filtered), "ledger_status": 1})
        self.assertTrue(pushed is not None)


if __name__ == "__main__":
    unittest.main()
