from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Tuple


def evaluate_runtime(code: str, test_script: str = "") -> Tuple[bool, bool, float, str]:
    """Evaluates Python code syntax and runtime execution in an isolated subshell.

    Returns:
        (syntax_valid, runtime_passed, execution_time_ms, error_message)
    """
    # 1. Syntax check via AST
    try:
        ast.parse(code)
        syntax_valid = True
    except SyntaxError as e:
        return False, False, 0.0, f"SyntaxError: {e.msg} at line {e.lineno}"

    # If there is no test harness or main block, append a basic validity invocation
    executable_code = code
    if test_script:
        executable_code = f"{code}\n\n# --- AUTOMATED TEST HARNESS ---\n{test_script}"
    elif "if __name__" not in code and "__main__" not in code:
        # Just compile & import-check
        executable_code = f"{code}\n# Compiled and imported cleanly"

    # 2. Run in temporary file with isolation
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(executable_code)
        tmp_path = Path(tmp.name)

    start_time = time.perf_counter()
    try:
        res = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=4.0,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000
        passed = (res.returncode == 0)
        err = res.stderr.strip() if not passed else ""
        return syntax_valid, passed, duration_ms, err
    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return syntax_valid, False, duration_ms, "Execution timed out (> 4.0s)"
    except Exception as ex:
        duration_ms = (time.perf_counter() - start_time) * 1000
        return syntax_valid, False, duration_ms, str(ex)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
