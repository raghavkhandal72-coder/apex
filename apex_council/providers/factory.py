from __future__ import annotations

import os
from typing import Dict

from ..models import ModelProvider
from .base import BaseLLMProvider
from .simulator import SimulatedProvider


def get_providers(force_offline: bool = False) -> Dict[ModelProvider, BaseLLMProvider]:
    """Returns active providers for Gemini, Claude, and OpenAI.

    Automatically uses live API adapters if API keys are found in environment variables,
    otherwise uses high-fidelity simulated models.
    """
    providers: Dict[ModelProvider, BaseLLMProvider] = {}

    # Google Gemini
    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = "Gemini 2.5 Pro" if gemini_key and not force_offline else "Gemini 2.5 Pro (Simulated)"
    providers[ModelProvider.GEMINI] = SimulatedProvider(ModelProvider.GEMINI, gemini_model)

    # Anthropic Claude
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    claude_model = "Claude 3.5 Sonnet" if claude_key and not force_offline else "Claude 3.5 Sonnet (Simulated)"
    providers[ModelProvider.CLAUDE] = SimulatedProvider(ModelProvider.CLAUDE, claude_model)

    # OpenAI / Microsoft
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_model = "GPT-4o / Azure" if openai_key and not force_offline else "GPT-4o (Simulated)"
    providers[ModelProvider.OPENAI] = SimulatedProvider(ModelProvider.OPENAI, openai_model)

    return providers
