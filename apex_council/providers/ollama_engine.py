#!/usr/bin/env python3
"""
Apex Ollama Integration Engine: First-class local offline LLM runner.
100% Pure Python Standard Library (pip = 0). Uses urllib.request.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class OllamaEngine:
    """Manages local Ollama daemon connection, models, and inference."""

    DEFAULT_HOST = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen2.5-coder"

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or os.environ.get("OLLAMA_HOST") or self.DEFAULT_HOST).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or self.DEFAULT_MODEL

    def is_running(self, timeout: float = 0.5) -> bool:
        """Checks if the local Ollama daemon is active and responding."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "Apex-Ollama"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self, timeout: float = 2.0) -> List[Dict[str, Any]]:
        """Returns list of models installed locally in Ollama."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "Apex-Ollama"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("models", [])
        except Exception:
            return []

    def generate(self, prompt: str, model: Optional[str] = None, timeout: float = 45.0) -> str:
        """Sends inference request to Ollama and returns generated text."""
        target_model = model or self.model
        url = f"{self.host}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Apex-Ollama"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json.get("response", "").strip()

    def set_active_model(self, model_name: str) -> None:
        """Sets active model for the session and updates environment."""
        self.model = model_name
        os.environ["OLLAMA_MODEL"] = model_name
        os.environ["APEX_USE_OLLAMA"] = "1"

    def render_status(self) -> str:
        """Renders rich terminal status card for Ollama integration."""
        running = self.is_running()
        models = self.list_models() if running else []
        status_badge = "\033[38;5;114m● ONLINE\033[0m" if running else "\033[38;5;203m○ OFFLINE\033[0m"

        lines = [
            "\n" + "=" * 68,
            f" 🦙 APEX OLLAMA LOCAL AI ENGINE STATUS: {status_badge}",
            "=" * 68,
            f"  Daemon Host   : {self.host}",
            f"  Active Model  : \033[1m{self.model}\033[0m",
            f"  Models Found  : {len(models)} local model(s)",
        ]

        if running and models:
            lines.append("\n  \033[1mInstalled Local Models:\033[0m")
            for m in models:
                name = m.get("name", "unknown")
                size_gb = m.get("size", 0) / (1024 ** 3)
                modified = m.get("modified_at", "")[:10]
                mark = "👉 (active)" if name == self.model or name.startswith(self.model) else "  "
                lines.append(f"    {mark} {name:<28} {size_gb:5.1f} GB   updated: {modified}")
        elif not running:
            lines.extend([
                "\n  \033[38;5;220m[!] Ollama daemon not detected on " + self.host + "\033[0m",
                "  To start using local models:",
                "    1. Install Ollama: \033[4mhttps://ollama.com/download\033[0m",
                "    2. In PowerShell run: \033[1mollama run qwen2.5-coder\033[0m (or llama3.2)",
                "    3. Apex will auto-bind to your local GPU/CPU model instantly!",
            ])
        lines.append("=" * 68 + "\n")
        return "\n".join(lines)


def handle_ollama_cli(args_list: List[str]) -> int:
    """Dispatches CLI subcommand: apex ollama [status|list|use <model>|run <prompt>]."""
    engine = OllamaEngine()
    if not args_list or args_list[0] in {"status", "info"}:
        print(engine.render_status())
        return 0

    sub = args_list[0].lower()
    if sub in {"list", "ls", "models"}:
        models = engine.list_models()
        if not models:
            if not engine.is_running():
                print("Ollama is not running. Start Ollama with 'ollama serve'.")
            else:
                print("No local models installed. Run 'ollama pull qwen2.5-coder'.")
            return 1
        print(f"\nInstalled Ollama Models ({len(models)}):")
        for m in models:
            size_gb = m.get("size", 0) / (1024 ** 3)
            print(f"  • {m.get('name', 'unknown'):<28} ({size_gb:.1f} GB)")
        print()
        return 0

    if sub in {"use", "set", "select"}:
        if len(args_list) < 2:
            print("Usage: apex ollama use <model_name>")
            return 1
        model_name = args_list[1]
        engine.set_active_model(model_name)
        print(f"✓ Active Ollama model set to: {model_name}")
        return 0

    if sub in {"run", "prompt", "ask"}:
        if len(args_list) < 2:
            print("Usage: apex ollama run <prompt>")
            return 1
        prompt = " ".join(args_list[1:])
        if not engine.is_running():
            print(engine.render_status())
            return 1
        print(f"• Generating via Ollama ({engine.model})...")
        t0 = time.perf_counter()
        resp = engine.generate(prompt)
        elapsed = time.perf_counter() - t0
        print(f"\n{resp}\n")
        print(f"[{engine.model} completed in {elapsed:.2f}s]")
        return 0

    print("Usage: apex ollama [status|list|use <model>|run <prompt>]")
    return 0


if __name__ == "__main__":
    sys.exit(handle_ollama_cli(sys.argv[1:]))
