from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from ..engine import CouncilEngine
from ..enterprise.audit import CryptographicAuditLogger
from ..enterprise.dlp import EnterpriseDLP
from ..enterprise.telemetry import EnterpriseTelemetry

HTML_FILE = Path(__file__).parent / "index.html"


class CouncilWebHandler(BaseHTTPRequestHandler):
    engine = CouncilEngine(force_offline=False)
    audit_logger = CryptographicAuditLogger()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FILE.read_bytes())

        elif self.path in ("/api/health", "/healthz", "/livez"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "version": "1.0.0"}).encode("utf-8"))

        elif self.path == "/metrics":
            # Prometheus / OpenMetrics endpoint
            metrics_data = EnterpriseTelemetry.export_metrics()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics_data.encode("utf-8"))

        elif self.path == "/api/audit/verify":
            # Cryptographic audit log integrity check
            valid, count, err = self.audit_logger.verify_integrity()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "audit_chain_valid": valid,
                "total_entries_verified": count,
                "error": err,
            }).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/deliberate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                raw_prompt = data.get("prompt", "Build a high performance LRU cache")

                # Enterprise DLP Data Loss Prevention Sanitization
                dlp_res = EnterpriseDLP.sanitize(raw_prompt)
                sanitized_prompt = dlp_res.clean_text

                result = self.engine.convene_council(sanitized_prompt)

                # Record SOC2 Cryptographic Audit Log & Metrics
                self.audit_logger.record_event(
                    action="DELIBERATE",
                    prompt=sanitized_prompt,
                    output_code=result.consensus_code,
                    winner=result.winner.value,
                    security_score=result.evaluations[result.winner].security_score,
                )
                EnterpriseTelemetry.record_request(
                    action="deliberate",
                    duration_sec=result.total_time_ms / 1000.0,
                    winner=result.winner.value,
                )

                resp_data = result.to_dict()
                resp_data["dlp_redactions"] = dlp_res.redactions_count

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp_data).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

        elif self.path == "/api/relay":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                raw_prompt = data.get("prompt", "Design a rate limiter")

                # Enterprise DLP Sanitization
                dlp_res = EnterpriseDLP.sanitize(raw_prompt)
                relay_result = self.engine.collaborative_relay(dlp_res.clean_text)

                self.audit_logger.record_event(
                    action="RELAY",
                    prompt=dlp_res.clean_text,
                    output_code=relay_result["combined_code"],
                    winner="COLLABORATIVE_CONSENSUS",
                    security_score=100.0,
                )
                EnterpriseTelemetry.record_request(
                    action="relay",
                    duration_sec=relay_result["total_time_ms"] / 1000.0,
                    winner="COLLABORATIVE_CONSENSUS",
                )

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(relay_result).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server(host: str = "127.0.0.1", port: int = 8080):
    server = HTTPServer((host, port), CouncilWebHandler)
    print(f"\n[APEX-COUNCIL] Enterprise Web Studio & Metrics live at: http://{host}:{port}")
    print(f"[APEX-COUNCIL] Prometheus Metrics Endpoint: http://{host}:{port}/metrics")
    print(f"[APEX-COUNCIL] SOC2 Audit Verification: http://{host}:{port}/api/audit/verify")
    print("[APEX-COUNCIL] Press Ctrl+C to stop server.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[APEX-COUNCIL] Enterprise server shut down cleanly.")
