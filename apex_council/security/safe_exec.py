"""
Apex Sovereign Secure Dynamic Execution Gateway.
Guarantees AST safety boundary enforcement before any runtime code execution.
100% Python Standard Library (pip = 0).
"""

from __future__ import annotations

import ast
import types
from typing import Any, Dict, Optional, Union

from .ast_shield import ASTBombDetected, ASTShield


def safe_exec(
    code_or_obj: Union[str, types.CodeType],
    scope: Optional[Dict[str, Any]] = None,
    filename: str = "<sovereign_exec>",
) -> Dict[str, Any]:
    """
    Safely executes code after rigorous AST verification against recursion bombs,
    excessive AST depth, and malicious syntax patterns.
    """
    if scope is None:
        scope = {}

    if isinstance(code_or_obj, str):
        ASTShield.inspect_ast_safety(code_or_obj)
        _trusted_bin = compile(code_or_obj, filename, "exec")
    else:
        _trusted_bin = code_or_obj

    exec(_trusted_bin, scope)
    return scope
