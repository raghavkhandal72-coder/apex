from __future__ import annotations

import os
from pathlib import Path


class SecurityJailBreach(PermissionError):
    """Raised when an attacker attempts directory traversal, symlink escape, or jailbreak."""
    pass


class FilesystemJail:
    """Zero-Trust Filesystem Chroot Jail.

    Enforces strict canonical boundary containment, defeating:
    - Path traversal attacks (../../)
    - Symlink escape exploits
    - Null-byte poison strings
    - Windows NTFS Alternate Data Streams (ADS)
    """

    @staticmethod
    def resolve_safe_path(base_dir: Path | str, untrusted_rel_path: str) -> Path:
        base = Path(base_dir).resolve()

        # Check 1: Null-byte injection
        if "\0" in str(untrusted_rel_path):
            raise SecurityJailBreach("Null-byte poison detected in file path")

        # Check 2: Windows Alternate Data Stream (file:stream)
        if ":" in str(untrusted_rel_path) and not (len(str(untrusted_rel_path)) >= 2 and str(untrusted_rel_path)[1] == ":"):
            raise SecurityJailBreach("Alternate Data Stream (ADS) traversal exploit detected")

        # Normalize and resolve real path
        target = (base / untrusted_rel_path).resolve()

        # Check 3: Canonical parent containment check
        try:
            target.relative_to(base)
        except ValueError:
            raise SecurityJailBreach(f"Jailbreak detected: Path '{target}' escapes restricted base '{base}'")

        # Check 4: Symlink traversal check
        if os.path.islink(target):
            real_dest = Path(os.path.realpath(target))
            try:
                real_dest.relative_to(base)
            except ValueError:
                raise SecurityJailBreach(f"Symlink Escape Exploit: Symlink points outside sandbox to '{real_dest}'")

        return target
