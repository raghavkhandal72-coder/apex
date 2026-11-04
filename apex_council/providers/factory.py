from __future__ import annotations

import os
from typing import Dict

from ..models import ModelProvider
from .base import BaseLLMProvider
from .live_http import LiveClaudeProvider, LiveGeminiProvider, LiveOpenAIProvider
from .simulator import SimulatedProvider


def get_providers(force_offline: bool = False) -> Dict[ModelProvider, BaseLLMProvider]:
    """Returns active providers for Gemini, Claude, and OpenAI.

    Automatically uses live API adapters if API keys are found in environment variables,
    otherwise uses high-fidelity simulated models.
    """
    providers: Dict[ModelProvider, BaseLLMProvider] = {}

    # Google Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and not force_offline:
        providers[ModelProvider.GEMINI] = LiveGeminiProvider(gemini_key)
    else:
        providers[ModelProvider.GEMINI] = SimulatedProvider(ModelProvider.GEMINI, "Gemini 2.5 Pro (Simulated)")

    # Anthropic Claude
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    if claude_key and not force_offline:
        providers[ModelProvider.CLAUDE] = LiveClaudeProvider(claude_key)
    else:
        providers[ModelProvider.CLAUDE] = SimulatedProvider(ModelProvider.CLAUDE, "Claude 3.5 Sonnet (Simulated)")

    # OpenAI / Microsoft
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and not force_offline:
        providers[ModelProvider.OPENAI] = LiveOpenAIProvider(openai_key)
    else:
        providers[ModelProvider.OPENAI] = SimulatedProvider(ModelProvider.OPENAI, "GPT-4o (Simulated)")

    return providers
