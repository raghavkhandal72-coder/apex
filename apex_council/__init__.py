
import sys

if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for std_id in (-11, -12):
            h = kernel32.GetStdHandle(std_id)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h, mode.value | 0x0004 | 0x0008)
    except Exception:
        pass
"""Apex-Council: The Autonomous Multi-LLM Code Supreme Court

Pitting Google Gemini, Anthropic Claude, and OpenAI against each other in real-time.
"""

from .engine import CouncilEngine
from .models import CodeSubmission, CouncilResult, Critique, EvaluationScore, ModelProvider
from .reporter import CouncilReporter

__version__ = "0.9.0"

__all__ = [
    "CouncilEngine",
    "CouncilResult",
    "ModelProvider",
    "CodeSubmission",
    "Critique",
    "EvaluationScore",
    "CouncilReporter",
]
