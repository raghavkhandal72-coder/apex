#!/usr/bin/env python3
"""Fail if the package imports anything outside the standard library (backs the 'pip = 0' claim)."""
import ast
import sys
from pathlib import Path

PKG = sys.argv[1] if len(sys.argv) > 1 else "apex_council"
if not hasattr(sys, "stdlib_module_names"):
    print("Python >= 3.10 required for this check"); sys.exit(0)

std = set(sys.stdlib_module_names) | {PKG, "__future__"}
bad = []
for path in Path(PKG).rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods = [node.module.split(".")[0]]
        for m in mods:
            if m not in std:
                bad.append(f"{path}:{node.lineno}: non-stdlib import '{m}'")
if bad:
    print("\n".join(bad)); sys.exit(1)
print(f"OK: {PKG} imports only the standard library")
