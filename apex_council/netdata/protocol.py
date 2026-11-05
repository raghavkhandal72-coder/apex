"""Netdata external plugin streaming wire protocol encoder & decoder.
Supports: CHART, DIMENSION, BEGIN, SET, END, VARIABLE, CLABEL.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from .models import ChartDefinition, DimensionDefinition, TelemetrySnapshot


class NetdataProtocol:
    """
    Encoder and decoder for the Netdata streaming text protocol.
    """

    @staticmethod
    def chart(
        chart_id: str,
        name: str = "",
        title: str = "",
        units: str = "",
        family: str = "system",
        context: str = "",
        chart_type: str = "line",
        priority: int = 1000,
        update_every: int = 1,
        options: str = "",
    ) -> str:
        """
        Emits: CHART type.id name title units [family [context [charttype [priority [update_every [options]]]]]]
        """
        n = f"'{name}'" if name else "''"
        t = f"'{title}'" if title else "''"
        u = f"'{units}'" if units else "''"
        fam = f"'{family}'" if family else "''"
        ctx = f"'{context}'" if context else "''"
        parts = ["CHART", chart_id, n, t, u, fam, ctx, chart_type, str(priority), str(update_every)]
        if options:
            parts.append(options)
        return " ".join(parts) + "\n"

    @staticmethod
    def dimension(
        dim_id: str,
        name: str = "",
        algorithm: str = "absolute",
        multiplier: int = 1,
        divisor: int = 1,
        options: str = "",
    ) -> str:
        """
        Emits: DIMENSION id [name [algorithm [multiplier [divisor [options]]]]]
        """
        n = f"'{name}'" if name else f"'{dim_id}'"
        parts = ["DIMENSION", dim_id, n, algorithm, str(multiplier), str(divisor)]
        if options:
            parts.append(options)
        return " ".join(parts) + "\n"

    @staticmethod
    def begin(chart_id: str, microseconds: Optional[int] = None) -> str:
        """Emits: BEGIN type.id [microseconds]"""
        if microseconds is not None:
            return f"BEGIN {chart_id} {microseconds}\n"
        return f"BEGIN {chart_id}\n"

    @staticmethod
    def set(dim_id: str, value: Union[float, int]) -> str:
        """Emits: SET id = value"""
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            val_str = str(int(value))
        else:
            val_str = str(value)
        return f"SET {dim_id} = {val_str}\n"

    @staticmethod
    def end() -> str:
        """Emits: END"""
        return "END\n"

    @staticmethod
    def variable(name: str, value: Union[float, int], is_global: bool = True) -> str:
        """Emits: VARIABLE [GLOBAL] name = value"""
        scope = "GLOBAL " if is_global else ""
        return f"VARIABLE {scope}{name} = {value}\n"

    @classmethod
    def encode_chart_definition(cls, chart_def: ChartDefinition) -> str:
        """Encodes complete CHART and DIMENSION definition block."""
        out = [
            cls.chart(
                chart_id=chart_def.id,
                name=chart_def.name,
                title=chart_def.title,
                units=chart_def.units,
                family=chart_def.family,
                context=chart_def.category,
                chart_type=chart_def.chart_type,
                priority=chart_def.priority,
                update_every=chart_def.update_every,
            )
        ]
        for dim in chart_def.dimensions:
            out.append(
                cls.dimension(
                    dim_id=dim.id,
                    name=dim.name,
                    algorithm=dim.algorithm,
                    multiplier=dim.multiplier,
                    divisor=dim.divisor,
                )
            )
        return "".join(out)

    @classmethod
    def encode_frame(
        cls,
        chart_id: str,
        values: Dict[str, Union[float, int]],
        microseconds: Optional[int] = None,
    ) -> str:
        """Encodes BEGIN ... SET ... END frame."""
        lines = [cls.begin(chart_id, microseconds)]
        for dim, val in values.items():
            lines.append(cls.set(dim, val))
        lines.append(cls.end())
        return "".join(lines)

    @classmethod
    def encode_snapshot(cls, snapshot: TelemetrySnapshot) -> str:
        """
        Encodes a TelemetrySnapshot into standardized Netdata wire stream frames:
        apex.cpu, apex.memory, apex.disk, apex.process.
        """
        frames: List[str] = []
        micros = int(snapshot.timestamp * 1_000_000)

        # 1. CPU frame
        cpu_vals = {
            "utilization": round(snapshot.cpu_util_pct, 2),
            "cores": snapshot.cpu_cores,
        }
        frames.append(cls.encode_frame("apex.cpu", cpu_vals, micros))

        # 2. RAM frame
        mem_vals = {
            "used": round(snapshot.memory_used_mb, 2),
            "total": round(snapshot.memory_total_mb, 2),
            "percent": round(snapshot.memory_percent, 2),
        }
        frames.append(cls.encode_frame("apex.memory", mem_vals, micros))

        # 3. Disk frame
        disk_vals = {
            "used": round(snapshot.disk_used_mb, 2),
            "total": round(snapshot.disk_total_mb, 2),
            "percent": round(snapshot.disk_percent, 2),
        }
        frames.append(cls.encode_frame("apex.disk", disk_vals, micros))

        # 4. Process frame
        proc_vals = {
            "count": snapshot.process_count,
            "cpu_percent": round(snapshot.process_cpu_pct, 2),
            "memory_mb": round(snapshot.process_memory_mb, 2),
        }
        frames.append(cls.encode_frame("apex.process", proc_vals, micros))

        return "".join(frames)

    @staticmethod
    def decode_line(line: str) -> Dict[str, Any]:
        """Parses a single Netdata protocol line into structured dictionary."""
        s = line.strip()
        if not s or s.startswith("#"):
            return {"command": "COMMENT", "raw": line}

        tokens = re.findall(r"(?:[^\s']+|'[^']*')+", s)
        tokens = [t.strip("'") for t in tokens]
        cmd = tokens[0].upper()

        if cmd == "CHART":
            return {
                "command": "CHART",
                "id": tokens[1] if len(tokens) > 1 else "",
                "name": tokens[2] if len(tokens) > 2 else "",
                "title": tokens[3] if len(tokens) > 3 else "",
                "units": tokens[4] if len(tokens) > 4 else "",
                "family": tokens[5] if len(tokens) > 5 else "",
                "context": tokens[6] if len(tokens) > 6 else "",
                "chart_type": tokens[7] if len(tokens) > 7 else "line",
                "priority": int(tokens[8]) if len(tokens) > 8 and tokens[8].isdigit() else 1000,
                "update_every": int(tokens[9]) if len(tokens) > 9 and tokens[9].isdigit() else 1,
            }
        elif cmd == "DIMENSION":
            return {
                "command": "DIMENSION",
                "id": tokens[1] if len(tokens) > 1 else "",
                "name": tokens[2] if len(tokens) > 2 else "",
                "algorithm": tokens[3] if len(tokens) > 3 else "absolute",
                "multiplier": int(tokens[4]) if len(tokens) > 4 and tokens[4].isdigit() else 1,
                "divisor": int(tokens[5]) if len(tokens) > 5 and tokens[5].isdigit() else 1,
            }
        elif cmd == "BEGIN":
            return {
                "command": "BEGIN",
                "id": tokens[1] if len(tokens) > 1 else "",
                "microseconds": int(tokens[2]) if len(tokens) > 2 and tokens[2].isdigit() else None,
            }
        elif cmd == "SET":
            # format: SET id = value or SET id value
            dim_id = tokens[1] if len(tokens) > 1 else ""
            val_idx = 3 if len(tokens) > 2 and tokens[2] == "=" else 2
            val = float(tokens[val_idx]) if len(tokens) > val_idx else 0.0
            return {"command": "SET", "dimension": dim_id, "value": val}
        elif cmd == "END":
            return {"command": "END"}
        elif cmd == "VARIABLE":
            is_global = len(tokens) > 1 and tokens[1].upper() == "GLOBAL"
            name_idx = 2 if is_global else 1
            val_idx = name_idx + 2 if len(tokens) > name_idx + 1 and tokens[name_idx + 1] == "=" else name_idx + 1
            name = tokens[name_idx] if len(tokens) > name_idx else ""
            val = float(tokens[val_idx]) if len(tokens) > val_idx else 0.0
            return {"command": "VARIABLE", "global": is_global, "name": name, "value": val}

        return {"command": cmd, "tokens": tokens}

    @classmethod
    def decode_stream(cls, stream_text: str) -> List[Dict[str, Any]]:
        """Parses a multi-line wire stream into structured commands."""
        events: List[Dict[str, Any]] = []
        for line in stream_text.strip().splitlines():
            item = cls.decode_line(line)
            if item.get("command") != "COMMENT":
                events.append(item)
        return events
