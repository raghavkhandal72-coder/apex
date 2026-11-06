#!/usr/bin/env python3
"""Apex CLI alias entrypoint."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apex_council.cli import main

if __name__ == "__main__":
    sys.exit(main())
