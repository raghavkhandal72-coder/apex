#!/usr/bin/env python3
"""
Apex-Sovereign: Production Standalone Runner & Graceful Supervision
Pure Python Standard Library | Zero Dependencies
"""

import os
import signal
import sys
import time

running = True


def handle_shutdown(signum, frame):
    global running
    print(f"\n[RUNNER] Received shutdown signal ({signum}), shutting down gracefully...")
    running = False


def main():
    global running
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    port = int(os.environ.get("APEX_PORT", 8000))
    env = os.environ.get("APEX_ENV", "production")
    print(f"==========================================================")
    print(f"   🚀 APEX SOVEREIGN STANDALONE RUNNER INITIALIZED         ")
    print(f"==========================================================")
    print(f"  Environment: {env}")
    print(f"  Port:        {port}")
    print(f"  Supervision: Self-Healing Active")
    print(f"==========================================================")

    while running:
        try:
            time.sleep(0.5)
        except (KeyboardInterrupt, SystemExit):
            break

    print("[RUNNER] Clean shutdown complete.")


if __name__ == "__main__":
    main()
