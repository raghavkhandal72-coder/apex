"""Rootless PEP 578 Runtime Audit Hook & Resource Quota Sandbox.
Executes code in user-space without root/sudo privileges using CPython sys.addaudithook
and kernel resource.setrlimit quotas.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


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
    Strips all API tokens, cloud keys, and SSH credentials.
    """
    clean_env: Dict[str, str] = {}
    whitelist = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH", "COMSPEC", "PATHEXT", "PYTHONPATH"}
    for k, v in os.environ.items():
        if k.upper() in whitelist:
            clean_env[k] = v

    for k in list(clean_env.keys()):
        upper_k = k.upper()
        if any(bad in upper_k for bad in PROHIBITED_ENV_SUBSTRINGS):
            del clean_env[k]

    clean_env["PYTHONUNBUFFERED"] = "1"
    clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return clean_env


def generate_pep578_bootstrap(allowed_dir: str) -> str:
    """Generates the in-process Python bootstrap for PEP 578 audit hooks and POSIX resource limits."""
    escaped_allowed_dir = os.path.abspath(allowed_dir).replace("\\", "\\\\")

    return f'''# --- APEX PEP 578 RUNTIME AUDIT HOOK & RESOURCE QUOTAS ---
import sys, os

# 1. OS Kernel Resource Quotas (POSIX: Linux/macOS)
try:
    import resource
    # RLIMIT_CPU: 4s soft, 5s hard
    resource.setrlimit(resource.RLIMIT_CPU, (4, 5))
    # RLIMIT_AS: 512MB RAM cap
    ram_limit = 512 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (ram_limit, ram_limit))
    # RLIMIT_NPROC: anti-fork-bomb cap (max 16 processes)
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    # RLIMIT_FSIZE: max 15MB file write
    resource.setrlimit(resource.RLIMIT_FSIZE, (15 * 1024 * 1024, 15 * 1024 * 1024))
except (ImportError, AttributeError, ValueError, OSError):
    pass

# 2. PEP 578 CPython Audit Hook (Rootless User-Space C-Level Interception)
ALLOWED_ROOT = os.path.abspath(r"{escaped_allowed_dir}")
ALLOWED_TEMP = os.path.abspath(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")))

def _apex_pep578_audit_hook(event, args):
    # Block shell & subprocess execution
    if event in ("os.system", "subprocess.Popen", "os.spawn", "os.posix_spawn", "pty.spawn", "posix.system"):
        raise PermissionError(f"[APEX-PEP578-BLOCK] Subprocess execution is strictly forbidden: {{event}}")

    # Block network socket operations
    if event in ("socket.connect", "socket.bind", "socket.sendto", "socket.sendmsg", "socket.listen"):
        raise PermissionError(f"[APEX-PEP578-BLOCK] Network exfiltration is strictly forbidden: {{event}}")

    # Block ctypes / low-level memory tampering
    if event.startswith("ctypes.dlopen") or event.startswith("ctypes.dlsym"):
        raise PermissionError(f"[APEX-PEP578-BLOCK] Interpreter memory manipulation forbidden: {{event}}")

    # Enforce filesystem access boundary on writes
    if event == "open":
        file_path = str(args[0]) if args else ""
        mode = str(args[1]) if len(args) > 1 else ""
        flags = args[2] if len(args) > 2 else 0
        is_write = any(m in mode for m in ("w", "a", "+", "x")) or (
            isinstance(flags, int) and (flags & (getattr(os, "O_WRONLY", 1) | getattr(os, "O_RDWR", 2) | getattr(os, "O_CREAT", 64)))
        )
        if is_write and file_path:
            norm_path = os.path.abspath(file_path)
            if not norm_path.startswith(ALLOWED_ROOT) and not norm_path.startswith(ALLOWED_TEMP):
                raise PermissionError(f"[APEX-PEP578-BLOCK] Unauthorized file write outside sandbox: {{file_path}}")

try:
    sys.addaudithook(_apex_pep578_audit_hook)
except Exception:
    pass
# --- END APEX PEP 578 BOOTSTRAP ---

'''


def combine_with_pep578_bootstrap(code: str, bootstrap: str) -> str:
    """Combines user code with PEP 578 bootstrap, preserving any __future__ imports at the very top."""
    lines = code.splitlines(keepends=True)
    future_lines = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            future_lines.append(line)
            idx += 1
        elif stripped.startswith("from __future__ import"):
            future_lines.append(line)
            idx += 1
        else:
            break

    other_lines = lines[idx:]
    if any("from __future__ import" in l for l in future_lines):
        return "".join(future_lines) + "\n" + bootstrap + "\n" + "".join(other_lines)
    return bootstrap + "\n" + code


class HermeticExecutionSandbox:
    """Rootless Process Sandbox powered by PEP 578 Audit Hooks and Resource Quotas.
    Runs 100% in user-space without requiring sudo or root.
    """

    @staticmethod
    def execute_isolated(
        code: str,
        timeout_sec: float = 3.5,
        allowed_dir: Optional[str | Path] = None,
    ) -> Tuple[bool, float, str]:
        """Runs code in the hermetic sandbox with PEP 578 audit hooks and resource limits.
        Returns: (success: bool, duration_ms: float, output: str)
        """
        clean_env = get_hermetic_environment()
        target_dir = str(allowed_dir) if allowed_dir else tempfile.gettempdir()
        bootstrap = generate_pep578_bootstrap(target_dir)

        combined_code = combine_with_pep578_bootstrap(code, bootstrap)

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(combined_code)
            tmp_path = Path(tmp.name)

        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                [sys.executable, "-I", str(tmp_path)],
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
