"""Pure Python Standalone Executable Compiler using standard library zipapp.
Bundles the entire Apex-Sovereign codebase into an airtight zero-dependency apex.pyz executable.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import zipapp
from pathlib import Path


def build_standalone_pyz(output_path: str = "dist/apex.pyz") -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    src_package = repo_root / "apex_council"
    out_file = repo_root / output_path
    out_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[*] Packaging Apex-Sovereign from: {src_package}")

    with tempfile.TemporaryDirectory() as staging_dir:
        staging_path = Path(staging_dir)
        target_pkg = staging_path / "apex_council"
        
        # Copy source package, excluding caches
        shutil.copytree(
            src_package,
            target_pkg,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git*"),
        )

        # Copy benchmarks and scripts modules so self-contained commands work in zipapp
        if (repo_root / "benchmarks").exists():
            shutil.copytree(
                repo_root / "benchmarks",
                staging_path / "benchmarks",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
        if (repo_root / "scripts").exists():
            shutil.copytree(
                repo_root / "scripts",
                staging_path / "scripts",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )

        # Create __main__.py inside staging root
        main_py = staging_path / "__main__.py"
        main_py.write_text(
            '"""Apex-Sovereign Standalone Executable Entrypoint."""\n'
            "import sys\n"
            "from apex_council.cli import main\n\n"
            'if __name__ == "__main__":\n'
            "    sys.exit(main())\n",
            encoding="utf-8",
        )

        # Build zipapp executable archive
        zipapp.create_archive(
            source=staging_path,
            target=out_file,
            interpreter="/usr/bin/env python3",
            main=None,  # Handled by __main__.py
            compressed=True,
        )

    # Set executable permissions on POSIX
    try:
        out_file.chmod(out_file.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass

    size_kb = out_file.stat().st_size / 1024
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"[OK] Successfully compiled standalone executable: {out_file} ({size_kb:.1f} KB)")
    return out_file


if __name__ == "__main__":
    build_standalone_pyz()
