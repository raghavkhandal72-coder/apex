#!/usr/bin/env python3
"""
Apex OpenCodex (ocx) Bridge Engine.
Zero-Pip (100% Python standard library).
Universal Provider Proxy Integration between Apex Sovereign and OpenCodex (port 10100).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..security.safe_net import safe_http_request
from ..ui.terminal import TerminalColors

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class OpenCodexBridge:
    """Manages connection, health checks, and lifecycle of OpenCodex proxy."""

    DEFAULT_HOST = "http://127.0.0.1:10100"

    def __init__(self, host: Optional[str] = None):
        self.host = (host or os.environ.get("OPENCODEX_HOST") or os.environ.get("OCX_HOST") or self.DEFAULT_HOST).rstrip("/")

    def is_running(self, timeout: float = 0.5) -> bool:
        """Checks if OpenCodex proxy is active and responding on port 10100."""
        for endpoint in [f"{self.host}/v1/models", f"{self.host}/health", f"{self.host}/"]:
            try:
                req = safe_http_request(endpoint, headers={"User-Agent": "Apex-OpenCodex-Bridge"}, allow_loopback=True)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status in (200, 302, 304):
                        return True
            except Exception:
                pass
        return False

    def list_models(self, timeout: float = 1.5) -> List[Dict[str, Any]]:
        """Returns list of models routed through OpenCodex."""
        try:
            req = safe_http_request(f"{self.host}/v1/models", headers={"User-Agent": "Apex-OpenCodex-Bridge"}, allow_loopback=True)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("data", []) or data.get("models", [])
        except Exception:
            return []

    def start_proxy(self, background: bool = True) -> Tuple[bool, str]:
        """Launches OpenCodex proxy daemon."""
        if self.is_running():
            return True, f"OpenCodex proxy is already active on {self.host}"

        ocx_bin = shutil.which("ocx")
        if not ocx_bin:
            # Check local scratch repo bin/ocx.mjs
            local_repo = Path(__file__).resolve().parent.parent.parent.parent / "scratch" / "opencodex" / "bin" / "ocx.mjs"
            if local_repo.exists() and shutil.which("node"):
                cmd = ["node", str(local_repo), "start"]
            else:
                return False, "Could not locate 'ocx' binary in PATH or local opencodex clone. Run 'npm install -g --allow-scripts=bun @bitkyc08/opencodex'."
        else:
            cmd = [ocx_bin, "start"]

        try:
            if background:
                if sys.platform == "win32":
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000,  # CREATE_NO_WINDOW
                    )
                else:
                    subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                # Wait briefly for startup
                for _ in range(10):
                    time.sleep(0.5)
                    if self.is_running(timeout=0.3):
                        return True, f"OpenCodex proxy successfully started on {self.host} (Web Dashboard: {self.host})"
                return True, f"OpenCodex launch triggered on {self.host}. Checking readiness..."
            else:
                proc = subprocess.run(cmd)
                return proc.returncode == 0, f"OpenCodex exited with code {proc.returncode}"
        except Exception as e:
            return False, f"Failed to start OpenCodex proxy: {e}"

    def stop_proxy(self) -> bool:
        """Terminates running OpenCodex instances."""
        stopped = False
        if sys.platform == "win32":
            proc = subprocess.run('taskkill /F /IM node.exe /FI "WINDOWTITLE eq *opencodex*"', shell=True, capture_output=True)
            if proc.returncode == 0:
                stopped = True
        return stopped

    def open_dashboard(self) -> None:
        """Opens OpenCodex Web Dashboard in default browser."""
        webbrowser.open(self.host)

    def render_status(self) -> str:
        """Renders rich Cyberpunk status card for OpenCodex."""
        c = TerminalColors
        running = self.is_running()
        models = self.list_models() if running else []
        badge = f"{c.NEON_GREEN}● ONLINE{c.RESET}" if running else f"{c.RED}○ OFFLINE{c.RESET}"

        lines = [
            "\n" + c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            c.CYAN + c.BOLD + f"  🌐  APEX SOVEREIGN: OPENCODEX (OCX) UNIVERSAL PROXY GATEWAY: {badge}" + c.RESET,
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}Gateway Host   :{c.RESET} {c.GOLD}{self.host}{c.RESET}",
            f"  {c.BOLD}Web Dashboard  :{c.RESET} {c.CYAN}{self.host}{c.RESET} (Interactive Provider GUI)",
            f"  {c.BOLD}Proxy Status   :{c.RESET} {'Active & Listening (Port 10100)' if running else 'Gateway offline'}",
            f"  {c.BOLD}Routed Models  :{c.RESET} {len(models)} model(s) available",
        ]

        if running and models:
            lines.append(f"\n  {c.BOLD}Active OpenCodex Model Routes:{c.RESET}")
            for m in models[:8]:
                m_id = m.get("id") or m.get("name", "unknown")
                lines.append(f"    • {c.NEON_GREEN}{m_id:<32}{c.RESET}")
            if len(models) > 8:
                lines.append(f"    {c.DIM}... and {len(models) - 8} more models (run 'ocx models ls'){c.RESET}")
        elif not running:
            lines.extend([
                f"\n  {c.GOLD}[!] OpenCodex Proxy is not currently running.{c.RESET}",
                f"  {c.BOLD}To launch the Universal Proxy Gateway:{c.RESET}",
                f"    1. Run: {c.NEON_GREEN}apex ocx start{c.RESET} (or 'ocx start')",
                f"    2. Dashboard: {c.CYAN}http://localhost:10100{c.RESET}",
                f"    3. Apex Supreme Council will automatically bind to OpenCodex routes!",
            ])

        lines.extend([
            "",
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}Quick Commands:{c.RESET}",
            f"    apex ocx start        Start the proxy gateway & dashboard",
            f"    apex ocx status       Check proxy health & routed models",
            f"    apex ocx gui          Open the web configuration dashboard",
            f"    apex ocx doctor       Run network & client diagnostics",
            f"    apex ocx claude       Launch Claude Code CLI through the proxy",
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET + "\n",
        ])
        return "\n".join(lines)


def handle_ocx_cli(args_list: List[str]) -> int:
    """Dispatches CLI command: apex ocx [start|status|gui|doctor|models|setup|...]."""
    bridge = OpenCodexBridge()
    if not args_list or args_list[0] in {"status", "info"}:
        print(bridge.render_status())
        return 0

    sub = args_list[0].lower()
    if sub in {"start", "serve", "launch"}:
        print("• Starting OpenCodex Universal Proxy Gateway...")
        ok, msg = bridge.start_proxy(background=True)
        if ok:
            print(f"✓ {msg}")
            print(f"• Opening Web Dashboard: {bridge.host}")
            bridge.open_dashboard()
            return 0
        else:
            print(f"[!] {msg}")
            return 1

    if sub in {"gui", "dashboard", "web"}:
        print(f"• Opening OpenCodex Dashboard: {bridge.host}")
        bridge.open_dashboard()
        return 0

    if sub in {"models", "ls", "list"}:
        if not bridge.is_running():
            print(bridge.render_status())
            return 1
        models = bridge.list_models()
        print(f"\nRouted Models in OpenCodex ({len(models)}):")
        for m in models:
            m_id = m.get("id") or m.get("name", "unknown")
            print(f"  • {m_id}")
        print()
        return 0

    # Forward other commands directly to native ocx CLI if installed
    ocx_bin = shutil.which("ocx")
    if ocx_bin:
        cmd = [ocx_bin] + args_list
        proc = subprocess.run(cmd)
        return proc.returncode
    else:
        print("[!] Native 'ocx' binary not found. Please install via: npm install -g --allow-scripts=bun @bitkyc08/opencodex")
        return 1
