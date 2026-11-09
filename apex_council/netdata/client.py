"""Netdata REST API Client & In-Process Telemetry Emulator Server.
Exposes /api/v1/info, /api/v1/allmetrics, /api/v1/data, /health using pure Python http.server & urllib.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import collections
import http.server
import json
import os
import platform
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Deque, Dict, List, Optional, Tuple

from .collector import collect_snapshot, get_default_collector
from .models import TelemetrySnapshot


class NetdataClient:
    """
    REST API client for Netdata daemon or local emulator.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:19999", timeout: float = 4.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_alive(self) -> bool:
        """Checks if the Netdata daemon / server is reachable."""
        try:
            from ..security.safe_net import safe_http_request
            req = safe_http_request(f"{self.base_url}/api/v1/info", allow_loopback=True)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        """Queries /api/v1/info endpoint."""
        url = f"{self.base_url}/api/v1/info"
        try:
            from ..security.safe_net import safe_http_request
            req = safe_http_request(url, headers={"User-Agent": "Apex-Council-Netdata-Client"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e), "status": "unreachable", "url": url}

    def get_allmetrics(self, format_type: str = "json") -> Dict[str, Any]:
        """Queries /api/v1/allmetrics?format=json endpoint."""
        url = f"{self.base_url}/api/v1/allmetrics?format={format_type}"
        try:
            from ..security.safe_net import safe_http_request
            req = safe_http_request(url, headers={"User-Agent": "Apex-Council-Netdata-Client"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e), "status": "unreachable", "url": url}

    def get_data(
        self,
        chart: str,
        after: int = -60,
        points: int = 60,
        group: str = "average",
    ) -> Dict[str, Any]:
        """Queries /api/v1/data timeseries endpoint."""
        params = urllib.parse.urlencode({
            "chart": chart,
            "after": after,
            "points": points,
            "group": group,
            "format": "json",
        })
        url = f"{self.base_url}/api/v1/data?{params}"
        try:
            from ..security.safe_net import safe_http_request
            req = safe_http_request(url, headers={"User-Agent": "Apex-Council-Netdata-Client"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e), "chart": chart, "status": "unreachable"}

    def push_metrics(self, chart_id: str, values: Dict[str, float]) -> bool:
        """
        Pushes metrics to Netdata daemon or local emulator.
        Fulfills platform interface contract:
        NetdataTelemetryClient: push_metrics(chart_id: str, values: dict[str, float]) -> bool
        """
        payload = json.dumps({"chart": chart_id, "values": values, "timestamp": time.time()}).encode("utf-8")
        url = f"{self.base_url}/api/v1/data"
        try:
            from ..security.safe_net import safe_http_request
            req = safe_http_request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST", allow_loopback=True)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False


# Contract alias
NetdataTelemetryClient = NetdataClient


class _ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class NetdataEmulatorHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP Request Handler emulating Netdata REST endpoints:
    /api/v1/info, /api/v1/allmetrics, /api/v1/data, /health.
    """

    server: "NetdataEmulatorServer"

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server request log noise."""
        pass

    def _send_json(self, status: int, data: Any) -> None:
        content = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json(200, {"status": "healthy", "service": "apex-netdata-emulator"})
            return

        if path == "/api/v1/info":
            snap = collect_snapshot()
            info_data = {
                "version": "v1.44.0-apex",
                "uid": "apex-sovereign-node-01",
                "mirrored_hosts": [],
                "os_name": platform.system(),
                "os_id": platform.system().lower(),
                "os_version": platform.release(),
                "kernel_name": platform.system(),
                "architecture": platform.machine(),
                "cores_total": snap.cpu_cores,
                "total_ram": int(snap.memory_total_mb * 1024 * 1024),
                "uptime": int(snap.uptime_seconds),
                "status": "ok",
            }
            self._send_json(200, info_data)
            return

        if path == "/api/v1/allmetrics":
            snap = collect_snapshot()
            all_metrics = {
                "system.cpu": {
                    "name": "system.cpu",
                    "family": "cpu",
                    "context": "system.cpu",
                    "units": "percentage",
                    "last_updated": int(snap.timestamp),
                    "dimensions": {
                        "utilization": {"name": "utilization", "value": round(snap.cpu_util_pct, 2)},
                        "idle": {"name": "idle", "value": round(max(0.0, 100.0 - snap.cpu_util_pct), 2)},
                    },
                },
                "system.ram": {
                    "name": "system.ram",
                    "family": "ram",
                    "context": "system.ram",
                    "units": "MB",
                    "last_updated": int(snap.timestamp),
                    "dimensions": {
                        "used": {"name": "used", "value": round(snap.memory_used_mb, 2)},
                        "free": {"name": "free", "value": round(max(0.0, snap.memory_total_mb - snap.memory_used_mb), 2)},
                    },
                },
                "system.disk": {
                    "name": "system.disk",
                    "family": "disk",
                    "context": "system.disk",
                    "units": "MB",
                    "last_updated": int(snap.timestamp),
                    "dimensions": {
                        "used": {"name": "used", "value": round(snap.disk_used_mb, 2)},
                        "free": {"name": "free", "value": round(max(0.0, snap.disk_total_mb - snap.disk_used_mb), 2)},
                    },
                },
                "system.processes": {
                    "name": "system.processes",
                    "family": "processes",
                    "context": "system.processes",
                    "units": "count",
                    "last_updated": int(snap.timestamp),
                    "dimensions": {
                        "active": {"name": "active", "value": snap.process_count},
                    },
                },
            }
            self._send_json(200, all_metrics)
            return

        if path == "/api/v1/data":
            chart = params.get("chart", ["system.cpu"])[0]
            pts = int(params.get("points", ["60"])[0])
            history = self.server.get_history(pts)

            if hasattr(self.server, "custom_history") and chart in self.server.custom_history:
                entries = self.server.custom_history[chart][-pts:]
                dim_names = list(entries[-1][1].keys()) if entries else ["value"]
                labels = ["time"] + dim_names
                data = [[t] + [v.get(d, 0.0) for d in dim_names] for t, v in entries]
            elif chart == "system.cpu":
                labels = ["time", "utilization"]
                data = [[int(s.timestamp), round(s.cpu_util_pct, 2)] for s in history]
            elif chart == "system.ram":
                labels = ["time", "used_mb"]
                data = [[int(s.timestamp), round(s.memory_used_mb, 2)] for s in history]
            elif chart == "system.disk":
                labels = ["time", "used_mb"]
                data = [[int(s.timestamp), round(s.disk_used_mb, 2)] for s in history]
            else:
                labels = ["time", "value"]
                data = [[int(s.timestamp), 0.0] for s in history]

            res = {
                "api": 1,
                "id": chart,
                "name": chart,
                "update_every": 1,
                "first_entry": data[0][0] if data else int(time.time()),
                "last_entry": data[-1][0] if data else int(time.time()),
                "labels": labels,
                "data": data,
            }
            self._send_json(200, res)
            return

        self._send_json(404, {"error": "Endpoint not found", "path": path})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/v1/data":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length > 0 else b"{}"
                data = json.loads(body.decode("utf-8"))
                self.server.record_external_metric(data)
                self._send_json(200, {"status": "success", "recorded": True})
                return
            except Exception as e:
                self._send_json(400, {"error": str(e)})
                return
        self._send_json(404, {"error": "Endpoint not found"})


class NetdataEmulatorServer:
    """
    In-process Netdata REST API server & time-series metrics emulator.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 19999, maxlen: int = 3600) -> None:
        self.host = host
        self.port = port
        self.maxlen = maxlen
        self.history: Deque[TelemetrySnapshot] = collections.deque(maxlen=maxlen)
        self.httpd: Optional[_ReusableTCPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._collector_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.custom_metrics: Dict[str, Any] = {}

    def record_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self.history.append(snapshot)

    def record_external_metric(self, payload: Dict[str, Any]) -> None:
        chart = payload.get("chart", "custom")
        values = payload.get("values", {})
        ts = payload.get("timestamp", time.time())
        if not hasattr(self, "custom_history"):
            self.custom_history: Dict[str, List[Tuple[int, Dict[str, Any]]]] = collections.defaultdict(list)
        self.custom_history[chart].append((int(ts), values))
        self.custom_metrics[chart] = values

    def get_history(self, count: int = 60) -> List[TelemetrySnapshot]:
        snaps = list(self.history)
        if not snaps:
            snaps = [collect_snapshot()]
        return snaps[-count:]

    def _collector_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                snap = collect_snapshot()
                self.record_snapshot(snap)
            except Exception:
                pass
            time.sleep(1.0)

    def start(self, background: bool = True) -> int:
        """Starts the emulator server. Returns bound port."""
        handler_cls = NetdataEmulatorHandler
        handler_cls.server = self  # type: ignore

        # Attempt binding to requested port, auto-fallback to ephemeral if occupied
        try:
            self.httpd = _ReusableTCPServer((self.host, self.port), handler_cls)
        except OSError:
            self.httpd = _ReusableTCPServer((self.host, 0), handler_cls)
            self.port = self.httpd.server_address[1]

        self._stop_event.clear()

        # Start metric background collector
        self._collector_thread = threading.Thread(target=self._collector_loop, daemon=True)
        self._collector_thread.start()

        if background:
            self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self._thread.start()
            return self.port
        else:
            try:
                self.httpd.serve_forever()
            except KeyboardInterrupt:
                self.stop()
            return self.port

    def stop(self) -> None:
        """Stops the emulator server and background collector."""
        self._stop_event.set()
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None
