"""Pure Python cross-platform telemetry collector (CPU, RAM, disk, network, process).
Zero third-party dependencies (pip = 0).
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
from typing import Any, Dict, Optional, Tuple

from .models import TelemetrySnapshot


class _WindowsNativeMetrics:
    """Windows ctypes API bindings for kernel32 / psapi."""

    def __init__(self) -> None:
        self.available = False
        if platform.system() == "Windows":
            try:
                import ctypes

                class _FILETIME(ctypes.Structure):
                    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

                class _MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ("cb", ctypes.c_ulong),
                        ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                    ]

                self.ctypes = ctypes
                self._FILETIME = _FILETIME
                self._MEMORYSTATUSEX = _MEMORYSTATUSEX
                self._PROCESS_MEMORY_COUNTERS = _PROCESS_MEMORY_COUNTERS
                self.kernel32 = ctypes.windll.kernel32
                self.available = True
            except Exception:
                self.available = False

    @staticmethod
    def _filetime_to_int(ft: Any) -> int:
        return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

    def get_system_times(self) -> Tuple[int, int, int]:
        """Returns (idle, kernel, user) tick counts."""
        if not self.available:
            return 0, 0, 0
        idle = self._FILETIME()
        kernel = self._FILETIME()
        user = self._FILETIME()
        if self.kernel32.GetSystemTimes(self.ctypes.byref(idle), self.ctypes.byref(kernel), self.ctypes.byref(user)):
            return (
                self._filetime_to_int(idle),
                self._filetime_to_int(kernel),
                self._filetime_to_int(user),
            )
        return 0, 0, 0

    def get_memory_status(self) -> Tuple[int, int, float]:
        """Returns (total_bytes, used_bytes, percent)."""
        if not self.available:
            return 0, 0, 0.0
        stat = self._MEMORYSTATUSEX()
        stat.dwLength = self.ctypes.sizeof(self._MEMORYSTATUSEX)
        if self.kernel32.GlobalMemoryStatusEx(self.ctypes.byref(stat)):
            total = stat.ullTotalPhys
            avail = stat.ullAvailPhys
            used = total - avail
            percent = float(stat.dwMemoryLoad)
            return total, used, percent
        return 0, 0, 0.0

    def get_process_count(self) -> int:
        """Returns the number of active processes."""
        if not self.available:
            return 0
        pids = (self.ctypes.c_ulong * 4096)()
        bytes_returned = self.ctypes.c_ulong()
        if self.kernel32.K32EnumProcesses(pids, self.ctypes.sizeof(pids), self.ctypes.byref(bytes_returned)):
            return bytes_returned.value // self.ctypes.sizeof(self.ctypes.c_ulong)
        return 0

    def get_process_memory_bytes(self) -> int:
        """Returns working set size of the current process."""
        if not self.available:
            return 0
        try:
            h_proc = self.kernel32.GetCurrentProcess()
            pmc = self._PROCESS_MEMORY_COUNTERS()
            pmc.cb = self.ctypes.sizeof(self._PROCESS_MEMORY_COUNTERS)
            if self.kernel32.K32GetProcessMemoryInfo(h_proc, self.ctypes.byref(pmc), self.ctypes.sizeof(pmc)):
                return int(pmc.WorkingSetSize)
        except Exception:
            pass
        return 0


class TelemetryCollector:
    """
    Cross-platform telemetry collector tracking system state and computing rolling rates.
    """

    def __init__(self, target_path: str = ".") -> None:
        self.target_path = target_path
        self.start_time = time.time()
        self.os_type = platform.system()
        self.cpu_cores = os.cpu_count() or 1
        self._win = _WindowsNativeMetrics() if self.os_type == "Windows" else None

        # Previous state for delta calculations
        self._last_sample_time: float = time.time()
        self._last_cpu_ticks: Optional[Tuple[int, int, int]] = None  # (idle, kernel, user)
        self._last_proc_cpu_time: float = time.process_time()
        self._last_proc_time: float = time.time()

        # Network & Disk I/O previous counters
        self._last_net_bytes: Tuple[int, int] = (0, 0)  # (recv, sent)
        self._last_disk_io_bytes: Tuple[int, int] = (0, 0)  # (read, write)
        self._init_baselines()

    def _init_baselines(self) -> None:
        if self._win and self._win.available:
            self._last_cpu_ticks = self._win.get_system_times()
        elif self.os_type == "Linux":
            self._last_cpu_ticks = self._read_linux_cpu_ticks()
            self._last_net_bytes = self._read_linux_network_bytes()
            self._last_disk_io_bytes = self._read_linux_disk_io_bytes()

    def _read_linux_cpu_ticks(self) -> Tuple[int, int, int]:
        try:
            with open("/proc/stat", "r", encoding="utf-8") as f:
                first_line = f.readline()
                parts = first_line.split()
                if parts and parts[0] == "cpu":
                    vals = [int(p) for p in parts[1:8]]
                    user, nice, system, idle, iowait, irq, softirq = vals
                    idle_all = idle + iowait
                    kernel_all = system + irq + softirq
                    user_all = user + nice
                    return idle_all, kernel_all, user_all
        except Exception:
            pass
        return 0, 0, 0

    def _read_linux_network_bytes(self) -> Tuple[int, int]:
        recv, sent = 0, 0
        try:
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        parts = line.split(":", 1)[1].split()
                        recv += int(parts[0])
                        sent += int(parts[8])
        except Exception:
            pass
        return recv, sent

    def _read_linux_disk_io_bytes(self) -> Tuple[int, int]:
        read_bytes, write_bytes = 0, 0
        try:
            with open("/proc/diskstats", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 14:
                        # sectors read (field 5) and sectors written (field 9), 512 bytes/sector
                        read_bytes += int(parts[5]) * 512
                        write_bytes += int(parts[9]) * 512
        except Exception:
            pass
        return read_bytes, write_bytes

    def _get_cpu_utilization(self, now: float) -> float:
        if self._win and self._win.available:
            curr_ticks = self._win.get_system_times()
            if self._last_cpu_ticks:
                i1, k1, u1 = self._last_cpu_ticks
                i2, k2, u2 = curr_ticks
                d_idle = i2 - i1
                d_kernel = k2 - k1
                d_user = u2 - u1
                total = d_kernel + d_user
                busy = total - d_idle
                self._last_cpu_ticks = curr_ticks
                if total > 0:
                    return max(0.0, min(100.0, (busy / total) * 100.0))
            self._last_cpu_ticks = curr_ticks
            return 0.0

        if self.os_type == "Linux":
            curr_ticks = self._read_linux_cpu_ticks()
            if self._last_cpu_ticks:
                i1, k1, u1 = self._last_cpu_ticks
                i2, k2, u2 = curr_ticks
                d_idle = i2 - i1
                d_total = (i2 + k2 + u2) - (i1 + k1 + u1)
                busy = d_total - d_idle
                self._last_cpu_ticks = curr_ticks
                if d_total > 0:
                    return max(0.0, min(100.0, (busy / d_total) * 100.0))
            self._last_cpu_ticks = curr_ticks
            return 0.0

        # Generic POSIX / macOS fallback
        try:
            load = os.getloadavg()[0]
            return max(0.0, min(100.0, (load / self.cpu_cores) * 100.0))
        except Exception:
            return 0.0

    def _get_memory_metrics(self) -> Tuple[float, float, float]:
        """Returns (used_mb, total_mb, percent)."""
        if self._win and self._win.available:
            tot, used, pct = self._win.get_memory_status()
            if tot > 0:
                return used / (1024 * 1024), tot / (1024 * 1024), pct

        if self.os_type == "Linux":
            try:
                mem_total_kb, mem_avail_kb = 0, 0
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            mem_total_kb = int(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            mem_avail_kb = int(line.split()[1])
                if mem_total_kb > 0:
                    mem_used_kb = mem_total_kb - mem_avail_kb
                    return (
                        mem_used_kb / 1024.0,
                        mem_total_kb / 1024.0,
                        (mem_used_kb / mem_total_kb) * 100.0,
                    )
            except Exception:
                pass

        # Generic fallback
        total_mb = 8192.0
        used_mb = 2048.0
        return used_mb, total_mb, (used_mb / total_mb) * 100.0

    def _get_disk_metrics(self) -> Tuple[float, float, float]:
        """Returns (used_mb, total_mb, percent)."""
        try:
            total, used, free = shutil.disk_usage(self.target_path)
            tot_mb = total / (1024 * 1024)
            used_mb = used / (1024 * 1024)
            pct = (used / total) * 100.0 if total > 0 else 0.0
            return used_mb, tot_mb, pct
        except Exception:
            return 0.0, 1.0, 0.0

    def _get_process_metrics(self, dt: float) -> Tuple[int, float, float]:
        """Returns (count, current_proc_cpu_pct, current_proc_mem_mb)."""
        # 1. Process count
        count = 0
        if self._win and self._win.available:
            count = self._win.get_process_count()
        elif self.os_type == "Linux":
            try:
                count = len([d for d in os.listdir("/proc") if d.isdigit()])
            except Exception:
                count = 0
        if count == 0:
            count = 1

        # 2. Current process memory
        proc_mem_mb = 0.0
        if self._win and self._win.available:
            proc_mem_mb = self._win.get_process_memory_bytes() / (1024 * 1024)
        else:
            try:
                import resource
                rusage = resource.getrusage(resource.RUSAGE_SELF)
                # On Linux maxrss is in kilobytes, on macOS in bytes
                if sys.platform == "darwin":
                    proc_mem_mb = rusage.ru_maxrss / (1024 * 1024)
                else:
                    proc_mem_mb = rusage.ru_maxrss / 1024.0
            except Exception:
                pass

        # 3. Current process CPU percentage
        proc_cpu_pct = 0.0
        now_proc_cpu = time.process_time()
        d_cpu = now_proc_cpu - self._last_proc_cpu_time
        if dt > 0:
            proc_cpu_pct = min(100.0, max(0.0, (d_cpu / dt) * 100.0))
        self._last_proc_cpu_time = now_proc_cpu

        return count, proc_cpu_pct, proc_mem_mb

    def _get_io_rates(self, dt: float) -> Tuple[float, float, float, float]:
        """Returns (disk_read_Bps, disk_write_Bps, net_recv_Bps, net_sent_Bps)."""
        if self.os_type == "Linux" and dt > 0:
            curr_disk = self._read_linux_disk_io_bytes()
            curr_net = self._read_linux_network_bytes()
            d_read = max(0, curr_disk[0] - self._last_disk_io_bytes[0]) / dt
            d_write = max(0, curr_disk[1] - self._last_disk_io_bytes[1]) / dt
            d_recv = max(0, curr_net[0] - self._last_net_bytes[0]) / dt
            d_sent = max(0, curr_net[1] - self._last_net_bytes[1]) / dt
            self._last_disk_io_bytes = curr_disk
            self._last_net_bytes = curr_net
            return d_read, d_write, d_recv, d_sent
        return 0.0, 0.0, 0.0, 0.0

    def sample(self) -> TelemetrySnapshot:
        """Captures a complete point-in-time snapshot."""
        now = time.time()
        dt = max(0.001, now - self._last_sample_time)
        self._last_sample_time = now

        cpu_util = self._get_cpu_utilization(now)
        mem_used, mem_total, mem_pct = self._get_memory_metrics()
        disk_used, disk_total, disk_pct = self._get_disk_metrics()
        proc_count, proc_cpu, proc_mem = self._get_process_metrics(dt)
        d_read, d_write, n_recv, n_sent = self._get_io_rates(dt)
        uptime = now - self.start_time

        return TelemetrySnapshot(
            timestamp=now,
            cpu_util_pct=cpu_util,
            cpu_cores=self.cpu_cores,
            memory_used_mb=mem_used,
            memory_total_mb=mem_total,
            memory_percent=mem_pct,
            disk_used_mb=disk_used,
            disk_total_mb=disk_total,
            disk_percent=disk_pct,
            disk_read_bytes_sec=d_read,
            disk_write_bytes_sec=d_write,
            network_recv_bytes_sec=n_recv,
            network_sent_bytes_sec=n_sent,
            process_count=proc_count,
            process_cpu_pct=proc_cpu,
            process_memory_mb=proc_mem,
            uptime_seconds=uptime,
            metadata={
                "os": self.os_type,
                "platform": platform.platform(),
                "python_version": platform.python_version(),
            },
        )


# Global default collector instance
_DEFAULT_COLLECTOR: Optional[TelemetryCollector] = None


def get_default_collector() -> TelemetryCollector:
    global _DEFAULT_COLLECTOR
    if _DEFAULT_COLLECTOR is None:
        _DEFAULT_COLLECTOR = TelemetryCollector()
    return _DEFAULT_COLLECTOR


def collect_snapshot(target_path: str = ".") -> TelemetrySnapshot:
    """Captures and returns a rich TelemetrySnapshot."""
    collector = get_default_collector()
    if target_path != collector.target_path:
        return TelemetryCollector(target_path).sample()
    return collector.sample()


def collect_system_metrics() -> Dict[str, float]:
    """
    Public platform interface contract:
    Returns dict with cpu_util_pct, memory_used_mb, disk_used_mb, process_count.
    """
    snapshot = collect_snapshot()
    return snapshot.to_summary_dict()
