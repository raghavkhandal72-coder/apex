"""Netdata Real-Time Telemetry and Monitoring Integration Module for Apex Sovereign.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

from .collector import (
    TelemetryCollector,
    collect_snapshot,
    collect_system_metrics,
    get_default_collector,
)
from .client import (
    NetdataClient,
    NetdataEmulatorHandler,
    NetdataEmulatorServer,
    NetdataTelemetryClient,
)
from .models import (
    ChartDefinition,
    DimensionDefinition,
    InferenceMetrics,
    MetricSample,
    SystemMetrics,
    TelemetrySnapshot,
)
from .protocol import NetdataProtocol

__all__ = [
    "MetricSample",
    "DimensionDefinition",
    "ChartDefinition",
    "TelemetrySnapshot",
    "SystemMetrics",
    "InferenceMetrics",
    "TelemetryCollector",
    "collect_snapshot",
    "collect_system_metrics",
    "get_default_collector",
    "NetdataProtocol",
    "NetdataClient",
    "NetdataTelemetryClient",
    "NetdataEmulatorServer",
    "NetdataEmulatorHandler",
]

__version__ = "1.0.0"
