#!/usr/bin/env python3
"""Interactive terminal walkthrough for Apex demonstration."""

import os
import subprocess
import sys
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  [DEMO] {text}")
    print("=" * 70 + "\n")
    time.sleep(0.5)

def main():
    print_banner("Apex Live Demo: Multi-Agent Consensus & Bounded Verification")
    
    print("Step 1: Pitting Gemini, Claude, and OpenAI against each other on LRU Cache...")
    time.sleep(0.5)
    subprocess.run([sys.executable, "dist/apex.pyz", "Build thread-safe LRU Cache", "--offline"])
    
    time.sleep(1.0)
    print_banner("Step 2: CEGIS Bounded Program Repair on Buggy Calculator")
    time.sleep(0.5)
    subprocess.run([sys.executable, "dist/apex.pyz", "cegis", "examples/calculator.py", "--tests", "assert add(2, 3) == 5"])
    
    time.sleep(1.0)
    print_banner("Step 3: Ochiai & Tarantula SBFL Fault Localization")
    time.sleep(0.5)
    subprocess.run([sys.executable, "dist/apex.pyz", "sbfl", "examples/calculator.py", "--tests", "assert add(2, 3) == 5"])
    
    print("\n[OK] Apex Live Walkthrough Complete!")

if __name__ == "__main__":
    main()
