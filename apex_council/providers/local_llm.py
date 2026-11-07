#!/usr/bin/env python3
"""
Apex Local LLM Client: Connects to local AI runners (Ollama, LM Studio, LocalAI, vLLM).
Pure Python Standard Library (pip = 0). Uses urllib.request.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple


class LocalLLMClient:
    """Zero-dependency client for local inference engines running on localhost."""

    DEFAULT_ENDPOINTS = [
        ("ollama", "http://127.0.0.1:11434"),
        ("lmstudio", "http://127.0.0.1:1234/v1"),
        ("vllm", "http://127.0.0.1:8000/v1"),
    ]

    @classmethod
    def detect_active_endpoint(cls) -> Optional[Tuple[str, str]]:
        """Probes local endpoints with a short timeout to detect running models."""
        custom_url = os.environ.get("LOCAL_LLM_URL") or os.environ.get("OLLAMA_HOST")
        if custom_url:
            return ("custom", custom_url.rstrip("/"))

        for engine_type, base_url in cls.DEFAULT_ENDPOINTS:
            try:
                probe_url = f"{base_url}/api/tags" if engine_type == "ollama" else f"{base_url}/models"
                req = urllib.request.Request(probe_url, headers={"User-Agent": "Apex-Local-LLM"})
                with urllib.request.urlopen(req, timeout=0.35) as resp:
                    if resp.status == 200:
                        return (engine_type, base_url)
            except Exception:
                continue
        return None

    @classmethod
    def generate(cls, prompt: str, system_prompt: str = "", model_hint: str = "") -> Optional[str]:
        """Queries local LLM if available; returns None if no local runner is responding."""
        detected = cls.detect_active_endpoint()
        if not detected:
            return None

        engine_type, base_url = detected
        try:
            if engine_type == "ollama":
                url = f"{base_url}/api/generate"
                payload = {
                    "model": model_hint or os.environ.get("OLLAMA_MODEL") or "codegemma:2b",
                    "prompt": prompt,
                    "system": system_prompt or "You are an expert Python systems engineer. Write only clean, type-safe Python code.",
                    "stream": False,
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    return res_json.get("response", "").strip()

            else:
                # OpenAI-compatible (LM Studio, LocalAI, vLLM)
                url = f"{base_url}/chat/completions"
                payload = {
                    "model": model_hint or "local-model",
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are an expert Python systems engineer. Output only clean code."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    choices = res_json.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()

        except Exception:
            return None
        return None
