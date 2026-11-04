from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ModelProvider(str, Enum):
    GEMINI = "Google Gemini"
    CLAUDE = "Anthropic Claude"
    OPENAI = "OpenAI / Microsoft"


@dataclass
class CodeSubmission:
    provider: ModelProvider
    model_name: str
    code: str
    explanation: str
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "code": self.code,
            "explanation": self.explanation,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class Critique:
    reviewer: ModelProvider
    target: ModelProvider
    score: float  # 0 to 10
    identified_flaws: List[str]
    feedback: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer.value,
            "target": self.target.value,
            "score": round(self.score, 1),
            "identified_flaws": self.identified_flaws,
            "feedback": self.feedback,
        }


@dataclass
class EvaluationScore:
    security_score: float  # 0 to 100
    security_issues: List[str] = field(default_factory=list)
    syntax_valid: bool = True
    runtime_passed: bool = True
    execution_time_ms: float = 0.0
    peer_review_avg: float = 0.0
    overall_score: float = 0.0

    def compute_overall(self) -> float:
        # Weighted score: 40% Security, 30% Peer Review (scaled to 100), 30% Runtime/Syntax
        syntax_runtime_pts = (50 if self.syntax_valid else 0) + (50 if self.runtime_passed else 0)
        peer_pts = self.peer_review_avg * 10
        self.overall_score = round(
            (0.40 * self.security_score) + (0.35 * peer_pts) + (0.25 * syntax_runtime_pts),
            1,
        )
        return self.overall_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "security_score": round(self.security_score, 1),
            "security_issues": self.security_issues,
            "syntax_valid": self.syntax_valid,
            "runtime_passed": self.runtime_passed,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "peer_review_avg": round(self.peer_review_avg, 1),
            "overall_score": round(self.overall_score, 1),
        }


@dataclass
class CouncilResult:
    task_prompt: str
    submissions: Dict[ModelProvider, CodeSubmission]
    critiques: List[Critique]
    evaluations: Dict[ModelProvider, EvaluationScore]
    winner: ModelProvider
    consensus_code: str
    verdict_summary: str
    total_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_prompt": self.task_prompt,
            "winner": self.winner.value,
            "verdict_summary": self.verdict_summary,
            "total_time_ms": round(self.total_time_ms, 2),
            "submissions": {k.value: v.to_dict() for k, v in self.submissions.items()},
            "critiques": [c.to_dict() for c in self.critiques],
            "evaluations": {k.value: v.to_dict() for k, v in self.evaluations.items()},
            "consensus_code": self.consensus_code,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
