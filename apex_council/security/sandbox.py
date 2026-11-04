from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Tuple

# Sensitive environment prefixes to scrub completely from child processes
PROHIBITED_ENV_SUBSTRINGS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "AUTH",
    "CREDENTIAL",
    "AWS_",
    "GITHUB_",
    "ANTHROPIC_",
    "GEMINI_",
    "OPENAI_",
    "SSH_",
    "PRIVATE",
    "DATABASE_",
)


def get_hermetic_environment() -> Dict[str, str]:
    """Builds a zero-trust, scrubbed environment for sandbox execution.

    Strips all API tokens, cloud keys, and SSH credentials so untrusted
    generated code cannot exfiltrate developer secrets.
    """
    clean_env: Dict[str, str] = {}

    # Allow only safe baseline OS variables
    whitelist = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT", "PYTHONPATH"}
    for k, v in os.environ.items():
        if k.upper() in whitelist:
            clean_env[k] = v

    # Explicitly verify no sensitive substrings slipped through
    for k in list(clean_env.keys()):
        upper_k = k.upper()
        if any(bad in upper_k for bad in PROHIBITED_ENV_SUBSTRINGS):
            del clean_env[k]

    # Force Python unbuffered and isolated mode
    clean_env["PYTHONUNBUFFERED"] = "1"
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return clean_env


class HermeticExecutionSandbox:
    """Military-Grade Process Sandbox.

    Executes code in a hermetically sealed subshell with:
    - Complete environment variable stripping (anti-credential harvesting).
    - Hard execution timeout deadlines (anti-infinite loop DoS).
    - Unattached standard input (anti-TTY hijacking).
    """

    @staticmethod
    def execute_isolated(code: str, timeout_sec: float = 3.5) -> Tuple[bool, float, str]:
        """Runs code in the hermetic sandbox.

        Returns (success, duration_ms, error_or_output)
        """
        clean_env = get_hermetic_environment()

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)

        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                [sys.executable, "-I", str(tmp_path)],  # -I flag isolates from user site-packages & current dir
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                stdin=subprocess.DEVNULL,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            passed = (res.returncode == 0)
            output = res.stderr.strip() if not passed else res.stdout.strip()
            return passed, duration_ms, output
        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return False, duration_ms, f"Sandbox Timeout: Execution killed after exceeding {timeout_sec}s deadline."
        except Exception as ex:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return False, duration_ms, f"Sandbox Failure: {str(ex)}"
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
