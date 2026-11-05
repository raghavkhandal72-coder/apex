#!/usr/bin/env python3
"""
Apex-Sovereign: Pure Python Zero-Dependency Transformer REST Server
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
from typing import Any, Dict, Optional

from apex_council.transformer.engine import TransformerInferenceEngine


class _TransformerHTTPHandler(http.server.BaseHTTPRequestHandler):
    server_context: Any = None

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "healthy", "model": "apex-transformer-v3"})
        elif self.path == "/metrics":
            metrics = self.server_context.engine.model.config.__dict__
            text_metrics = f"# HELP apex_transformer_info Model architectural dimensions\n"
            text_metrics += f"apex_transformer_vocab_size {metrics.get('vocab_size', 280)}\n"
            text_metrics += f"apex_transformer_d_model {metrics.get('d_model', 32)}\n"
            self._send_text(text_metrics)
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self) -> None:
        if self.path in ("/v1/completions", "/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)
            try:
                data = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                self._send_json({"error": f"Invalid JSON: {e}"}, 400)
                return

            prompt = data.get("prompt", "")
            max_tokens = int(data.get("max_tokens", 8))
            temperature = float(data.get("temperature", 0.0))

            res = self.server_context.engine.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            response = {
                "id": "cmpl-apex-transformer",
                "object": "text_completion",
                "text": res.text,
                "choices": [
                    {
                        "text": res.text,
                        "index": 0,
                        "finish_reason": "length",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(res.tokens) - max_tokens,
                    "completion_tokens": max_tokens,
                    "total_tokens": len(res.tokens),
                },
                "latency_ms": res.latency_ms,
            }
            self._send_json(response)
        else:
            self._send_json({"error": "Endpoint Not Found"}, 404)

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default stdio log spam


class TransformerServer:
    """
    Lightweight REST HTTP Server exposing completions, health, and metrics.
    """

    def __init__(
        self,
        engine: TransformerInferenceEngine,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self.engine = engine
        self.host = host
        self.port = port
        self.server_port = port
        self._httpd: Optional[socketserver.TCPServer] = None

    def start(self) -> None:
        handler_cls = type("BoundHandler", (_TransformerHTTPHandler,), {"server_context": self})
        # If port is 0 or busy, bind dynamically
        self._httpd = socketserver.TCPServer((self.host, self.port), handler_cls)
        # Update actual assigned port (crucial when port=0)
        self.port = self._httpd.server_address[1]
        self.server_port = self.port
        self._httpd.serve_forever()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
