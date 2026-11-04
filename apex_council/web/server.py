from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from ..engine import CouncilEngine

HTML_FILE = Path(__file__).parent / "index.html"


class CouncilWebHandler(BaseHTTPRequestHandler):
    engine = CouncilEngine(force_offline=False)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_FILE.read_bytes())
        elif self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "version": "1.0.0"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/deliberate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                prompt = data.get("prompt", "Build a high performance LRU cache")
                result = self.engine.convene_council(prompt)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result.to_dict()).encode("utf-8"))
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
                prompt = data.get("prompt", "Design a rate limiter")
                relay_result = self.engine.collaborative_relay(prompt)

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
        # Clean logging
        sys_stderr = getattr(self, "log_error", None)
        # Suppress standard noisy access logs


def run_server(host: str = "127.0.0.1", port: int = 8080):
    server = HTTPServer((host, port), CouncilWebHandler)
    print(f"\n[APEX-COUNCIL] Web Dashboard live at: http://{host}:{port}")
    print("[APEX-COUNCIL] Press Ctrl+C to stop server.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[APEX-COUNCIL] Server shut down cleanly.")
