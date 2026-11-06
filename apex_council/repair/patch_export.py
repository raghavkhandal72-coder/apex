"""
Apex Patch Exporter (Feature #7).
Generates standard Git-compatible unified .patch / .diff files from CEGIS repairs or file modifications.
Can be applied with standard `git apply fix.patch` or `patch -p1 < fix.patch`.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

import difflib
import os
import sys
from pathlib import Path
from typing import Optional, Tuple


def generate_patch(
    original_code: str,
    modified_code: str,
    filepath: str,
    label: str = "Apex Synthesized Fix",
) -> str:
    """Generate a standard unified diff string for two versions of a file."""
    rel_path = filepath.replace("\\", "/")
    orig_lines = original_code.splitlines(keepends=True)
    mod_lines = modified_code.splitlines(keepends=True)

    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
        n=3,
    )
    diff_text = "".join(diff)
    if not diff_text.strip():
        return ""

    header = f"# {label}\n# Target: {rel_path}\n"
    return header + diff_text


def export_patch_file(
    target_file: str,
    output_patch: Optional[str] = None,
    backup_file: Optional[str] = None,
) -> Tuple[bool, str]:
    """Export unified patch comparing target file against its backup or git version."""
    target_p = Path(target_file)
    if not target_p.exists():
        return False, f"Target file not found: {target_file}"

    # Locate original version
    bak_p = Path(backup_file) if backup_file else target_p.with_suffix(target_p.suffix + ".bak")
    if not bak_p.exists():
        return False, f"Backup file not found ({bak_p}). Run repair or provide --backup."

    orig_content = bak_p.read_text(encoding="utf-8", errors="replace")
    mod_content = target_p.read_text(encoding="utf-8", errors="replace")

    patch_text = generate_patch(orig_content, mod_content, str(target_p))
    if not patch_text:
        return False, "No differences detected between target and backup."

    if output_patch:
        out_p = Path(output_patch)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(patch_text, encoding="utf-8")
        return True, f"Patch successfully written to {output_patch}"
    else:
        return True, patch_text
