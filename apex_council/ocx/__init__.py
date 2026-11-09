"""Apex OpenCodex Bridge: Universal provider proxy integration.
100% Pure Python Standard Library (pip = 0).
Integrates lidge-jun/opencodex with Apex Sovereign.
"""

from .bridge import OpenCodexBridge, handle_ocx_cli

__all__ = ["OpenCodexBridge", "handle_ocx_cli"]
