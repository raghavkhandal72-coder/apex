from __future__ import annotations

import os
from typing import Dict

from ..models import ModelProvider
from .base import BaseLLMProvider
from .live_http import LiveClaudeProvider, LiveGeminiProvider, LiveLlamafileProvider, LiveOllamaProvider, LiveOpenAIProvider
from .simulator import SimulatedProvider


PLACEHOLDER_KEYS = {"...", "TODO", "your_gemini_api_key", "your_api_key_here", "sk-..."}


def _is_valid_key(key: str | None) -> bool:
    if not key:
        return False
    clean = key.strip()
    return bool(clean and clean not in PLACEHOLDER_KEYS and len(clean) >= 6)


def get_providers(force_offline: bool = False, strict: bool = False) -> Dict[ModelProvider, BaseLLMProvider]:
    """Returns active providers for Gemini, Claude, and OpenAI (or local Ollama / Apex-Coder).

    Automatically uses live API adapters if API keys are found in environment variables,
    otherwise connects to local Ollama models (Apex-Coder, Qwen) if available,
    falling back to high-fidelity simulated models.
    """
    providers: Dict[ModelProvider, BaseLLMProvider] = {}

    ollama_model = os.getenv("OLLAMA_MODEL")
    use_ollama = os.getenv("APEX_USE_OLLAMA", "1") not in ("0", "false", "False")

    installed_models = []
    if not force_offline and use_ollama:
        try:
            from .ollama_engine import OllamaEngine
            engine = OllamaEngine()
            if engine.is_running(timeout=0.3):
                installed_models = [m.get("name", "") for m in engine.list_models()]
        except Exception:
            pass

    # Check if Mozilla llamafile server is active on port 8080
    llamafile_running = False
    if not force_offline:
        try:
            from .llamafile_engine import LlamafileEngine
            llamafile_running = LlamafileEngine().is_running(timeout=0.2)
        except Exception:
            pass

    # 1. Google Gemini (or local Mozilla Llamafile)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if _is_valid_key(gemini_key) and not force_offline:
        providers[ModelProvider.GEMINI] = LiveGeminiProvider(gemini_key.strip(), strict=strict)
    elif not force_offline and llamafile_running:
        providers[ModelProvider.GEMINI] = LiveLlamafileProvider(
            provider=ModelProvider.GEMINI,
            display_name="Mozilla Llamafile (Port 8080)",
            strict=strict,
        )
    else:
        providers[ModelProvider.GEMINI] = SimulatedProvider(ModelProvider.GEMINI, "Gemini 2.5 Pro (Simulated)")

    # 2. Anthropic Claude (or local Qwen Coder)
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    if _is_valid_key(claude_key) and not force_offline:
        providers[ModelProvider.CLAUDE] = LiveClaudeProvider(claude_key.strip(), strict=strict)
    elif not force_offline and any("qwen" in m for m in installed_models):
        qwen_m = next((m for m in installed_models if "qwen" in m), "qwen2.5-coder:0.5b")
        providers[ModelProvider.CLAUDE] = LiveOllamaProvider(
            model_name=qwen_m,
            provider=ModelProvider.CLAUDE,
            display_name="Qwen 2.5 Coder (Local)",
            strict=strict,
        )
    else:
        providers[ModelProvider.CLAUDE] = SimulatedProvider(ModelProvider.CLAUDE, "Claude 3.5 Sonnet (Simulated)")

    # 3. OpenAI / Sovereign Apex-Coder
    openai_key = os.getenv("OPENAI_API_KEY")
    if _is_valid_key(openai_key) and not force_offline:
        providers[ModelProvider.OPENAI] = LiveOpenAIProvider(openai_key.strip(), strict=strict)
    elif not force_offline and (ollama_model or installed_models):
        target_m = ollama_model or next((m for m in installed_models if "apex" in m), installed_models[0])
        disp = f"Apex-Coder ({target_m})" if "apex" in target_m else f"Ollama ({target_m})"
        providers[ModelProvider.OPENAI] = LiveOllamaProvider(
            model_name=target_m,
            provider=ModelProvider.OPENAI,
            display_name=disp,
            strict=strict,
        )
    else:
        providers[ModelProvider.OPENAI] = SimulatedProvider(ModelProvider.OPENAI, "GPT-4o (Simulated)")

    return providers
