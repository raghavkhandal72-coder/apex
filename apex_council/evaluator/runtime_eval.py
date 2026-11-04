from __future__ import annotations

import ast
from typing import Tuple

from ..security.ast_shield import ASTBombDetected, ASTShield
from ..security.sandbox import HermeticExecutionSandbox


def evaluate_runtime(code: str, test_script: str = "") -> Tuple[bool, bool, float, str]:
    """Evaluates Python code syntax and runtime execution in a military-grade hermetic sandbox.

    Enforces:
    - AST Bomb & Recursion depth safety checks.
    - Hermetically sealed subshell (strips all credentials, tokens, and SSH keys).
    - Unattached standard input (anti-TTY injection).

    Returns:
        (syntax_valid, runtime_passed, execution_time_ms, error_message)
    """
    # 1. AST Bomb & Recursion Depth Pre-Check
    try:
        ASTShield.inspect_ast_safety(code)
    except ASTBombDetected as ex:
        return False, False, 0.0, f"Security Breach: {str(ex)}"
    except Exception:
        pass

    # 2. Syntax check via AST
    try:
        ast.parse(code)
        syntax_valid = True
    except SyntaxError as e:
        return False, False, 0.0, f"SyntaxError: {e.msg} at line {e.lineno}"

    # If there is no test harness, append validity check
    executable_code = code
    if test_script:
        executable_code = f"{code}\n\n# --- AUTOMATED TEST HARNESS ---\n{test_script}"
    elif "if __name__" not in code and "__main__" not in code:
        executable_code = f"{code}\n# Compiled and imported cleanly"

    # 3. Hermetic Sandbox Process Execution
    passed, duration_ms, output = HermeticExecutionSandbox.execute_isolated(executable_code, timeout_sec=4.0)

    err = output if not passed else ""
    return syntax_valid, passed, duration_ms, err
