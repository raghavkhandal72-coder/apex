"""Live Zero-SDK LLM Client for Local Ollama and Cloud Frontier Endpoints.
Connects strictly to real live HTTP JSON endpoints via pure standard library urllib.request.
ZERO MOCKS, ZERO FAKE DATA.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LiveLLMResponse:
    provider: str
    model: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class LiveLLMClient:
    """Pure-Python HTTP client for local Ollama and Cloud LLMs with zero external dependencies."""

    def __init__(self, timeout_sec: float = 30.0) -> None:
        self.timeout_sec = timeout_sec

    @staticmethod
    def is_ollama_available(host: str = "http://localhost:11434") -> bool:
        """Checks if a local Ollama daemon is running."""
        try:
            req = urllib.request.Request(f"{host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    @staticmethod
    def get_available_cloud_providers() -> List[str]:
        """Detects available frontier cloud providers based on environment variables."""
        providers = []
        if os.environ.get("OPENAI_API_KEY"):
            providers.append("openai")
        if os.environ.get("ANTHROPIC_API_KEY"):
            providers.append("anthropic")
        if os.environ.get("GEMINI_API_KEY"):
            providers.append("gemini")
        return providers

    def call_ollama(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
    ) -> LiveLLMResponse:
        url = f"{host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        start = time.perf_counter()
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("response", "")
            return LiveLLMResponse(
                provider="ollama",
                model=model,
                content=content,
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                latency_ms=(time.perf_counter() - start) * 1000,
                raw_payload=data,
            )

    def call_openai(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = "gpt-4o",
    ) -> LiveLLMResponse:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is missing")

        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        start = time.perf_counter()
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LiveLLMResponse(
                provider="openai",
                model=model,
                content=content,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=(time.perf_counter() - start) * 1000,
                raw_payload=data,
            )
