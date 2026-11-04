"""Apex-Council: The Autonomous Multi-LLM Code Supreme Court

Pitting Google Gemini, Anthropic Claude, and OpenAI against each other in real-time.
"""

from .engine import CouncilEngine
from .models import CodeSubmission, CouncilResult, Critique, EvaluationScore, ModelProvider
from .reporter import CouncilReporter

__version__ = "1.0.0"

__all__ = [
    "CouncilEngine",
    "CouncilResult",
    "ModelProvider",
    "CodeSubmission",
    "Critique",
    "EvaluationScore",
    "CouncilReporter",
]
