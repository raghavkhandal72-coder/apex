from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import CodeSubmission, Critique, ModelProvider


class BaseLLMProvider(ABC):
    def __init__(self, provider: ModelProvider, model_name: str):
        self.provider = provider
        self.model_name = model_name

    @abstractmethod
    def generate(self, prompt: str) -> CodeSubmission:
        """Generates code submission for the given prompt."""
        pass

    @abstractmethod
    def critique(self, target_provider: ModelProvider, target_code: str, prompt: str) -> Critique:
        """Critiques another model's code submission."""
        pass
