from __future__ import annotations

import time
from typing import Dict


class EnterpriseTelemetry:
    """Enterprise Prometheus & OpenMetrics Telemetry Engine."""

    _requests_total: Dict[str, int] = {}
    _model_wins_total: Dict[str, int] = {}
    _security_violations_total: int = 0
    _total_latency_seconds: float = 0.0

    @classmethod
    def record_request(cls, action: str, duration_sec: float, winner: str, security_violations: int = 0):
        cls._requests_total[action] = cls._requests_total.get(action, 0) + 1
        cls._model_wins_total[winner] = cls._model_wins_total.get(winner, 0) + 1
        cls._security_violations_total += security_violations
        cls._total_latency_seconds += duration_sec

    @classmethod
    def export_metrics(cls) -> str:
        lines = []
        lines.append("# HELP apex_council_requests_total Total number of Council operations processed")
        lines.append("# TYPE apex_council_requests_total counter")
        for action, count in cls._requests_total.items():
            lines.append(f'apex_council_requests_total{{action="{action}"}} {count}')

        lines.append("# HELP apex_council_model_wins_total Total Council consensus wins by model provider")
        lines.append("# TYPE apex_council_model_wins_total counter")
        for model, wins in cls._model_wins_total.items():
            lines.append(f'apex_council_model_wins_total{{model="{model}"}} {wins}')

        lines.append("# HELP apex_council_security_violations_total Total security vulnerabilities mitigated")
        lines.append("# TYPE apex_council_security_violations_total counter")
        lines.append(f"apex_council_security_violations_total {cls._security_violations_total}")

        lines.append("# HELP apex_council_deliberation_duration_seconds_total Total duration in seconds")
        lines.append("# TYPE apex_council_deliberation_duration_seconds_total counter")
        lines.append(f"apex_council_deliberation_duration_seconds_total {cls._total_latency_seconds:.4f}")

        return "\n".join(lines) + "\n"
