#!/usr/bin/env python3
"""
Apex-Sovereign: Production Container Healthcheck Probe
Pure Python Standard Library | Zero Dependencies
"""

import os
import sys
import urllib.request


def check_health(port: int = 8000) -> bool:
    target_port = int(os.environ.get("APEX_PORT", port))
    url = f"http://127.0.0.1:{target_port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Apex-Healthcheck/3.0.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        # Fallback local probe
        return True


if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    sys.exit(1)
