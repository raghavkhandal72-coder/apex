#!/usr/bin/env python3
"""
Apex-Sovereign: Inference Telemetry Tracker & Netdata Wire Exporter
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict, List


class InferenceTelemetryTracker:
    """
    Real-time inference telemetry tracking Time To First Token (TTFT),
    Inter-Token Latency (ITL), total latency, and tokens per second,
    exportable to Netdata streaming wire protocol.
    """

    def __init__(self) -> None:
        self.records: List[Dict[str, float]] = []

    def record_inference(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        ttft_ms: float,
        total_ms: float,
    ) -> None:
        tps = (completion_tokens / (total_ms / 1000.0)) if total_ms > 0 else 0.0
        itl_ms = ((total_ms - ttft_ms) / max(1, completion_tokens - 1)) if completion_tokens > 1 else ttft_ms

        self.records.append({
            "prompt_tokens": float(prompt_tokens),
            "completion_tokens": float(completion_tokens),
            "ttft_ms": ttft_ms,
            "itl_ms": itl_ms,
            "total_ms": total_ms,
            "tokens_per_sec": tps,
            "timestamp": time.time(),
        })

    def get_metrics(self) -> Dict[str, Any]:
        if not self.records:
            return {"ttft_ms": 0.0, "itl_ms": 0.0, "total_ms": 0.0, "tokens_per_sec": 0.0}

        latest = self.records[-1]
        avg_ttft = sum(r["ttft_ms"] for r in self.records) / len(self.records)
        avg_tps = sum(r["tokens_per_sec"] for r in self.records) / len(self.records)

        return {
            "ttft_ms": round(latest["ttft_ms"], 2),
            "avg_ttft_ms": round(avg_ttft, 2),
            "itl_ms": round(latest["itl_ms"], 2),
            "total_ms": round(latest["total_ms"], 2),
            "tokens_per_sec": round(avg_tps, 2),
            "total_inferences": len(self.records),
        }

    def to_netdata_wire(self) -> str:
        metrics = self.get_metrics()
        lines = [
            "CHART apex.transformer_inference '' 'Transformer Inference Latency' 'ms' 'performance' '' line 100 1",
            "DIMENSION ttft 'TTFT' absolute 1 1",
            "DIMENSION itl 'ITL' absolute 1 1",
            "BEGIN apex.transformer_inference",
            f"SET ttft = {int(metrics['ttft_ms'])}",
            f"SET itl = {int(metrics['itl_ms'])}",
            "END",
        ]
        return "\n".join(lines) + "\n"
