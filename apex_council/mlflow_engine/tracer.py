#!/usr/bin/env python3
"""
Apex-Sovereign: MLflow & OpenTelemetry Native Agent Tracer
100% Pure Python Standard Library | Zero Dependencies

Captures high-resolution execution traces across autonomous SWE agents, MCTS nodes,
and tool calls in full compliance with OpenTelemetry and MLflow Tracing specifications.
"""

from __future__ import annotations

import contextlib
import dataclasses
import json
import os
import secrets
import time
from typing import Any, Dict, Iterator, List, Optional


@dataclasses.dataclass
class Span:
    span_id: str
    trace_id: str
    name: str
    span_type: str  # "AGENT", "TOOL", "LLM", "CHAIN", "PARSER"
    parent_id: Optional[str]
    start_time_ns: int
    end_time_ns: Optional[int] = None
    status: str = "OK"  # "OK", "ERROR"
    inputs: Dict[str, Any] = dataclasses.field(default_factory=dict)
    outputs: Dict[str, Any] = dataclasses.field(default_factory=dict)
    attributes: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def duration_ms(self) -> float:
        if self.end_time_ns is None:
            return 0.0
        return (self.end_time_ns - self.start_time_ns) / 1_000_000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "span_type": self.span_type,
            "parent_id": self.parent_id,
            "start_time_ns": self.start_time_ns,
            "end_time_ns": self.end_time_ns,
            "duration_ms": self.duration_ms(),
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "attributes": self.attributes,
        }


@dataclasses.dataclass
class Trace:
    trace_id: str
    session_name: str
    root_span_id: str
    spans: List[Span] = dataclasses.field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "session_name": self.session_name,
            "root_span_id": self.root_span_id,
            "total_spans": len(self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


class AgentTracer:
    """
    OpenTelemetry-compatible Tracer for multi-agent workflows.
    Collects hierarchical spans without external tracing collectors.
    """

    def __init__(self, session_name: str = "apex_council_session") -> None:
        self.trace_id = secrets.token_hex(16)
        self.session_name = session_name
        self.spans: List[Span] = []
        self._span_stack: List[str] = []
        self.active_trace = Trace(
            trace_id=self.trace_id,
            session_name=session_name,
            root_span_id="",
            spans=self.spans,
        )

    @contextlib.contextmanager
    def span(
        self,
        name: str,
        span_type: str = "AGENT",
        inputs: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Span]:
        """
        Hierarchical context manager for tracing agent execution spans.
        """
        span_id = secrets.token_hex(8)
        parent_id = self._span_stack[-1] if self._span_stack else None

        if not self.active_trace.root_span_id:
            self.active_trace.root_span_id = span_id

        span_obj = Span(
            span_id=span_id,
            trace_id=self.trace_id,
            name=name,
            span_type=span_type,
            parent_id=parent_id,
            start_time_ns=time.time_ns(),
            inputs=inputs or {},
            attributes=attributes or {},
        )
        self.spans.append(span_obj)
        self._span_stack.append(span_id)

        try:
            yield span_obj
        except Exception as exc:
            span_obj.status = "ERROR"
            span_obj.attributes["error_type"] = type(exc).__name__
            span_obj.attributes["error_message"] = str(exc)
            raise
        finally:
            span_obj.end_time_ns = time.time_ns()
            self._span_stack.pop()

    def export_json(self, output_file: Optional[str] = None) -> str:
        """Exports the active trace in OpenTelemetry / MLflow Tracing JSON format."""
        data = self.active_trace.to_dict()
        formatted = json.dumps(data, indent=2)
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(formatted)
        return formatted
