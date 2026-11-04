from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..engine import CouncilEngine
from .runtime_eval import evaluate_runtime
from .security_eval import evaluate_security


@dataclass
class HealingAttempt:
    iteration: int
    security_score: float
    syntax_valid: bool
    runtime_passed: bool
    error_message: str
    duration_ms: float


@dataclass
class SelfHealingResult:
    file_path: Path
    healed: bool
    iterations_run: int
    initial_security_score: float
    final_security_score: float
    initial_error: str
    final_error: str
    healed_code: str
    attempts: List[HealingAttempt]
    total_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "healed": self.healed,
            "iterations_run": self.iterations_run,
            "initial_security_score": self.initial_security_score,
            "final_security_score": self.final_security_score,
            "initial_error": self.initial_error,
            "final_error": self.final_error,
            "total_time_ms": round(self.total_time_ms, 2),
            "attempts": [
                {
                    "iteration": a.iteration,
                    "security_score": a.security_score,
                    "runtime_passed": a.runtime_passed,
                    "error_message": a.error_message,
                    "duration_ms": round(a.duration_ms, 2),
                }
                for a in self.attempts
            ],
        }


class SelfHealingLoop:
    """Autonomous Closed-Loop Code Repair Engine.

    Detects failures (syntax errors, runtime tracebacks, security vulnerabilities),
    convenes the Supreme Council, generates patches, tests in an isolated sandbox,
    and iterates until 100% test pass rate and clean security score are achieved.
    """

    def __init__(self, engine: Optional[CouncilEngine] = None, force_offline: bool = False):
        self.engine = engine or CouncilEngine(force_offline=force_offline)

    def heal(
        self,
        target_file: Path | str,
        test_script: str = "",
        max_attempts: int = 3,
        auto_write: bool = True,
    ) -> SelfHealingResult:
        start_time = time.perf_counter()
        file_path = Path(target_file).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        current_code = file_path.read_text(encoding="utf-8", errors="ignore")
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")

        # Initial Diagnostic
        initial_sec, initial_issues = evaluate_security(current_code)
        init_syntax, init_run, _, init_err = evaluate_runtime(current_code, test_script)

        # If already clean and passing
        if initial_sec >= 95.0 and init_syntax and init_run:
            total_ms = (time.perf_counter() - start_time) * 1000
            return SelfHealingResult(
                file_path=file_path,
                healed=True,
                iterations_run=0,
                initial_security_score=initial_sec,
                final_security_score=initial_sec,
                initial_error="",
                final_error="",
                healed_code=current_code,
                attempts=[],
                total_time_ms=total_ms,
            )

        # Create atomic backup before modifying
        shutil.copyfile(file_path, backup_path)

        attempts: List[HealingAttempt] = []
        healed = False
        last_error = init_err or ("Security vulnerabilities detected: " + ", ".join(initial_issues))
        working_code = current_code

        for i in range(1, max_attempts + 1):
            iter_start = time.perf_counter()

            # Convene Council with failure diagnostic feedback loop
            prompt = (
                f"Autonomous Self-Healing Task for file {file_path.name} (Iteration {i}/{max_attempts}):\n"
                f"Fix all runtime exceptions, syntax errors, and security vulnerabilities.\n\n"
                f"Error Diagnostic:\n{last_error}\n\n"
                f"Current Code:\n```\n{working_code}\n```\n\n"
                f"Return only the complete, functional, refactored code."
            )

            council_result = self.engine.convene_council(prompt, test_harness=test_script)
            candidate_code = council_result.consensus_code

            # Evaluate candidate in isolated sandbox
            cand_sec, cand_issues = evaluate_security(candidate_code)
            cand_syntax, cand_run, _, cand_err = evaluate_runtime(candidate_code, test_script)
            iter_ms = (time.perf_counter() - iter_start) * 1000

            attempt = HealingAttempt(
                iteration=i,
                security_score=cand_sec,
                syntax_valid=cand_syntax,
                runtime_passed=cand_run,
                error_message=cand_err,
                duration_ms=iter_ms,
            )
            attempts.append(attempt)

            # Check if solved
            if cand_syntax and cand_run and cand_sec >= 80.0:
                healed = True
                working_code = candidate_code
                break
            else:
                last_error = cand_err or (f"Remaining security issues: {cand_issues}")
                working_code = candidate_code

        total_time_ms = (time.perf_counter() - start_time) * 1000
        final_sec, _ = evaluate_security(working_code)
        _, final_run, _, final_err = evaluate_runtime(working_code, test_script)

        if healed and auto_write:
            file_path.write_text(working_code, encoding="utf-8")
            backup_path.unlink(missing_ok=True)
        elif not healed:
            # Revert from backup if failed
            if backup_path.exists():
                shutil.copyfile(backup_path, file_path)
                backup_path.unlink(missing_ok=True)

        return SelfHealingResult(
            file_path=file_path,
            healed=healed,
            iterations_run=len(attempts),
            initial_security_score=initial_sec,
            final_security_score=final_sec,
            initial_error=init_err,
            final_error=final_err,
            healed_code=working_code,
            attempts=attempts,
            total_time_ms=total_time_ms,
        )
