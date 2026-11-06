#!/usr/bin/env python3
"""
Apex: The Zero-Dependency Python Program Repair & Synthesis Platform (pip = 0).
Entrypoint for cloned GitHub repositories:
    python main.py
    python main.py cegis binary_search.py --tests-file tests.txt
    python main.py test-all
"""
import os
import sys

# Ensure local source tree is at head of sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apex_council.cli import main

if __name__ == "__main__":
    sys.exit(main())
