"""Apex Sovereign Linux Kernel Subsystem & torvalds/linux Integration.
Zero external dependencies (pip = 0). Standard library only.
"""

from .engine import LinuxKernelEngine, handle_linux_cli

__all__ = ["LinuxKernelEngine", "handle_linux_cli"]
