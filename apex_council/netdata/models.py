"""Data models for the Netdata telemetry and monitoring subsystem.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MetricSample:
    """Represents a single metric measurement at a point in time."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    dimensions: Dict[str, str] = field(default_factory=dict)
    units: str = ""


@dataclass
class DimensionDefinition:
    """Represents a Netdata chart dimension definition."""
    id: str
    name: str = ""
    algorithm: str = "absolute"  # "absolute", "incremental", "percentage-of-absolute-row", "percentage-of-incremental-row"
    multiplier: int = 1
    divisor: int = 1
    hidden: bool = False
    noreset: bool = False
    nooverflow: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.id


@dataclass
class ChartDefinition:
    """Represents a Netdata chart definition."""
    id: str
    name: str = ""
    title: str = ""
    units: str = ""
    family: str = "system"
    category: str = "metrics"  # or context
    chart_type: str = "line"   # "line", "area", "stacked"
    priority: int = 1000
    update_every: int = 1
    dimensions: List[DimensionDefinition] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.id
        if not self.title:
            self.title = self.id

    def add_dimension(self, dimension: DimensionDefinition) -> None:
        self.dimensions.append(dimension)


@dataclass
class TelemetrySnapshot:
    """Complete snapshot of host and process telemetry at an instant."""
    timestamp: float
    cpu_util_pct: float
    cpu_cores: int
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    disk_used_mb: float
    disk_total_mb: float
    disk_percent: float
    disk_read_bytes_sec: float = 0.0
    disk_write_bytes_sec: float = 0.0
    network_recv_bytes_sec: float = 0.0
    network_sent_bytes_sec: float = 0.0
    process_count: int = 0
    process_cpu_pct: float = 0.0
    process_memory_mb: float = 0.0
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_summary_dict(self) -> Dict[str, float]:
        """Returns the four core metrics required by the platform contract."""
        return {
            "cpu_util_pct": round(float(self.cpu_util_pct), 2),
            "memory_used_mb": round(float(self.memory_used_mb), 2),
            "disk_used_mb": round(float(self.disk_used_mb), 2),
            "process_count": float(self.process_count),
        }


@dataclass
class SystemMetrics:
    """High-level system metrics container compatible with Survey Report specifications."""
    timestamp: float
    cpu_percent: float
    cpu_cores: int
    memory_used_bytes: int
    memory_total_bytes: int
    memory_percent: float
    disk_read_bytes_sec: float = 0.0
    disk_write_bytes_sec: float = 0.0
    network_recv_bytes_sec: float = 0.0
    network_sent_bytes_sec: float = 0.0


@dataclass
class InferenceMetrics:
    """Inference performance metrics container for LLM / Transformer tracking."""
    timestamp: float
    inference_id: str
    latency_ms: float
    tokens_generated: int
    prompt_tokens: int
    throughput_tokens_per_sec: float
    memory_peak_bytes: int
    model_name: str = "Apex-Transformer"
