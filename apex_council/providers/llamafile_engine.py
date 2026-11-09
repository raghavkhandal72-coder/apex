#!/usr/bin/env python3
"""
Apex Sovereign Portable Binary Runner Engine.
Zero-Pip (100% Python standard library). Supports Cosmopolitan / portable standalone runtimes on port 8080.
Rebranded natively into the Apex Sovereign AI ecosystem.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..security.safe_net import safe_http_request


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ApexPortableRunner:
    """Manages connection, health checks, and inference with Apex Portable Binary Runtimes."""

    DEFAULT_HOST = "http://127.0.0.1:8080"
    DEFAULT_MODEL = "apex-runner"

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or os.environ.get("APEX_RUNNER_HOST") or os.environ.get("LLAMAFILE_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.model = model or os.environ.get("APEX_RUNNER_MODEL") or os.environ.get("LLAMAFILE_MODEL") or self.DEFAULT_MODEL

    def is_running(self, timeout: float = 0.5) -> bool:
        """Checks if a local portable runner server is active on the target port."""
        try:
            req = safe_http_request(f"{self.host}/v1/models", headers={"User-Agent": "Apex-Sovereign-Runner"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            # Also try /health
            try:
                req = safe_http_request(f"{self.host}/health", headers={"User-Agent": "Apex-Sovereign-Runner"}, allow_loopback=True)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.status == 200
            except Exception:
                return False

    def list_models(self, timeout: float = 1.5) -> List[Dict[str, Any]]:
        """Returns list of models served by the portable runner."""
        try:
            req = safe_http_request(f"{self.host}/v1/models", headers={"User-Agent": "Apex-Sovereign-Runner"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("data", [])
        except Exception:
            return []

    def generate(self, prompt: str, timeout: float = 45.0) -> str:
        """Sends inference request to the runner server using standard /v1/chat/completions."""
        # 1. Try /v1/chat/completions (OpenAI compatible)
        chat_url = f"{self.host}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are Apex-Runner, an expert AI software engineer. Provide concise, production-ready, strictly typed Python code."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = safe_http_request(
            chat_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Apex-Sovereign-Runner"},
            method="POST",
            allow_loopback=True,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

        # 2. Fallback to /completion endpoint
        comp_url = f"{self.host}/completion"
        comp_payload = {
            "prompt": f"Write clean, production-ready Python code.\n\nTask: {prompt}\n\n```python\n",
            "temperature": 0.2,
            "n_predict": 512,
            "stream": False,
        }
        data = json.dumps(comp_payload).encode("utf-8")
        req = safe_http_request(
            comp_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Apex-Sovereign-Runner"},
            method="POST",
            allow_loopback=True,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("content", "").strip()
        except Exception as e:
            return f"# [Apex-Runner error: {e}]"

    def render_status(self) -> str:
        """Renders rich terminal status card for Apex Sovereign Portable Runner."""
        running = self.is_running()
        models = self.list_models() if running else []
        status_badge = "\033[38;5;114m● ONLINE\033[0m" if running else "\033[38;5;203m○ OFFLINE\033[0m"

        lines = [
            "\n" + "=" * 68,
            f" [APEX-RUNNER] APEX SOVEREIGN PORTABLE BINARY RUNNER: {status_badge}",
            "=" * 68,
            f"  Host Endpoint : {self.host}",
            f"  Status        : {'Active & Responding' if running else 'Runner server not detected on port 8080'}",
            f"  Models Found  : {len(models)} active model(s)",
        ]

        if running and models:
            lines.append("\n  \033[1mActive Apex Runner Models:\033[0m")
            for m in models:
                name = m.get("id", "unknown")
                created = m.get("created", "")
                lines.append(f"    • {name:<32} (created: {created})")
        elif not running:
            lines.extend([
                "\n  \033[38;5;220m[i] Apex Portable Runner not detected on " + self.host + "\033[0m",
                "  To launch a sovereign portable binary runtime:",
                "    1. Run your sovereign binary: \033[1m./apex-runner --server --port 8080\033[0m",
                "    2. Apex will auto-detect and bind to it as a Supreme Council Justice!",
            ])
        lines.append("=" * 68 + "\n")
        return "\n".join(lines)


# Backwards compatibility alias
LlamafileEngine = ApexPortableRunner


def handle_runner_cli(args_list: List[str]) -> int:
    """Dispatches CLI subcommand: apex runner [status|run <prompt>|info]."""
    engine = ApexPortableRunner()
    if not args_list or args_list[0] in {"status", "info"}:
        print(engine.render_status())
        return 0

    sub = args_list[0].lower()
    if sub in {"run", "ask", "prompt"}:
        if len(args_list) < 2:
            print("Usage: apex runner run <prompt>")
            return 1
        prompt = " ".join(args_list[1:])
        if not engine.is_running():
            print(engine.render_status())
            return 1
        print(f"• Generating via Apex Sovereign Runner ({engine.host})...")
        t0 = time.perf_counter()
        resp = engine.generate(prompt)
        dt = time.perf_counter() - t0
        print(f"\n{resp}\n")
        print(f"[Completed in {dt:.2f}s]")
        return 0

    print("Usage: apex runner [status|run <prompt>|info]")
    return 0


# Backwards compatibility alias for CLI
handle_llamafile_cli = handle_runner_cli


if __name__ == "__main__":
    sys.exit(handle_runner_cli(sys.argv[1:]))
