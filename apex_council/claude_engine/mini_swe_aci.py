#!/usr/bin/env python3
"""
Apex-Sovereign: Mini-SWE Agent-Computer Interface (ACI)
Inspired by mini-swe-agent, SWE-agent, & Aider Architect-Editor
100% Pure Python Standard Library | Zero Dependencies

Provides a typed, deterministic Agent-Computer Interface (ACI) with
instant Linter-in-the-Loop feedback (<1ms) to eliminate syntax hallucinations
before test execution.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from .ast_navigator import ASTSymbolNavigator
from .cognitive_memory import CognitiveMemoryStream
from .oracle_synthesizer import BugReproductionOracle


@dataclasses.dataclass(frozen=True)
class ACIAction:
    action_type: str  # "VIEW_FILE", "FIND_SYMBOL", "APPLY_REPLACE", "LINT_SYNTAX", "RUN_ORACLE"
    arguments: Dict[str, Any]


@dataclasses.dataclass(frozen=True)
class ACIResult:
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class MiniSWEAgentACI:
    """
    Minimalist Agent-Computer Interface (ACI) with Linter-in-the-Loop.
    Executes surgical operations on codebases with strict type safety.
    """

    def __init__(
        self,
        workspace_dir: str | pathlib.Path = ".",
        memory_stream: Optional[CognitiveMemoryStream] = None,
    ) -> None:
        self.workspace_dir = pathlib.Path(workspace_dir).resolve()
        self.navigator = ASTSymbolNavigator(self.workspace_dir)
        self.memory = memory_stream or CognitiveMemoryStream()

    def dispatch(self, action: ACIAction) -> ACIResult:
        """Dispatches an action safely through the ACI interface."""
        act = action.action_type.upper()
        args = action.arguments

        if act == "VIEW_FILE":
            return self._action_view_file(args.get("path", ""), args.get("start_line", 1), args.get("end_line", 100))
        elif act == "FIND_SYMBOL":
            return self._action_find_symbol(args.get("name", ""))
        elif act == "APPLY_REPLACE":
            return self._action_apply_replace(args.get("path", ""), args.get("old_str", ""), args.get("new_str", ""))
        elif act == "LINT_SYNTAX":
            return self._action_lint_syntax(args.get("code", ""))
        elif act == "RUN_ORACLE":
            return self._action_run_oracle(args.get("script", ""))
        else:
            return ACIResult(success=False, output="", error=f"Unknown ACI action: {action.action_type}")

    def _action_view_file(self, rel_path: str, start_line: int, end_line: int) -> ACIResult:
        p = (self.workspace_dir / rel_path).resolve()
        if not p.exists():
            return ACIResult(success=False, output="", error=f"File not found: {rel_path}")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)
            numbered = [f"{i + 1:4d} | {lines[i]}" for i in range(start_idx, end_idx)]
            return ACIResult(success=True, output="".join(numbered))
        except OSError as exc:
            return ACIResult(success=False, output="", error=str(exc))

    def _action_find_symbol(self, name: str) -> ACIResult:
        matches = self.navigator.search_function(name) + self.navigator.search_class(name) + self.navigator.search_method(name)
        if not matches:
            return ACIResult(success=False, output="", error=f"Symbol not found: {name}")
        output_lines = []
        for m in matches:
            output_lines.append(f"[{m.kind.upper()}] {m.name} in {m.file_path}:{m.lineno}-{m.end_lineno}")
            if m.parameters:
                output_lines.append(f"  params: ({', '.join(m.parameters)})")
            if m.docstring:
                output_lines.append(f"  doc: {m.docstring.strip()[:80]}...")
        return ACIResult(success=True, output="\n".join(output_lines))

    def _action_lint_syntax(self, code: str) -> ACIResult:
        """Validates code syntax via AST in <1ms without running subprocesses."""
        try:
            ast.parse(code)
            compile(code, "<lint>", "exec")
            return ACIResult(success=True, output="Syntax validation passed: AST clean.")
        except SyntaxError as syn_err:
            return ACIResult(
                success=False,
                output="",
                error=f"SyntaxError at line {syn_err.lineno}, col {syn_err.offset}: {syn_err.msg}",
            )

    def _action_apply_replace(self, rel_path: str, old_str: str, new_str: str) -> ACIResult:
        p = (self.workspace_dir / rel_path).resolve()
        if not p.exists():
            return ACIResult(success=False, output="", error=f"File not found: {rel_path}")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            if old_str not in content:
                return ACIResult(success=False, output="", error="Target old_str not found in file.")

            occurrences = content.count(old_str)
            if occurrences > 1:
                return ACIResult(
                    success=False,
                    output="",
                    error=f"Ambiguous replacement: old_str appears {occurrences} times. Provide more context.",
                )

            new_content = content.replace(old_str, new_str)
            # Linter check on new content before saving
            lint_res = self._action_lint_syntax(new_content)
            if not lint_res.success:
                return ACIResult(
                    success=False,
                    output="",
                    error=f"Replacement rejected by Linter-in-the-Loop: {lint_res.error}",
                )

            with open(p, "w", encoding="utf-8") as f:
                f.write(new_content)

            # Re-index navigator
            self.navigator.index_file(p)
            return ACIResult(success=True, output=f"Successfully updated {rel_path} with 1 verified replacement.")
        except OSError as exc:
            return ACIResult(success=False, output="", error=str(exc))

    def _action_run_oracle(self, script_code: str) -> ACIResult:
        success, code, stdout, stderr = BugReproductionOracle.execute_oracle(
            script_code, cwd=self.workspace_dir
        )
        return ACIResult(
            success=success,
            output=stdout.strip(),
            error=stderr.strip() if not success else None,
        )

    def solve_issue_loop(
        self,
        issue_text: str,
        patch_candidate_fn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end autonomous resolution workflow:
        1. Synthesizes reproduction oracle from issue text.
        2. Proves baseline failure.
        3. Identifies target symbol/file.
        4. Applies patch candidate and checks Linter-in-the-Loop.
        5. Verifies oracle passes on patched code.
        """
        # Step 1: Oracle synthesis
        oracle_spec = BugReproductionOracle.parse_issue(issue_text)

        # Step 2: Baseline run
        base_res = self.dispatch(ACIAction("RUN_ORACLE", {"script": oracle_spec.reproduction_code}))
        defect_reproduced = not base_res.success

        # Step 3: Localization context
        symbol_info = None
        if oracle_spec.target_symbol:
            sym_res = self.dispatch(ACIAction("FIND_SYMBOL", {"name": oracle_spec.target_symbol}))
            if sym_res.success:
                symbol_info = sym_res.output

        # Step 4: Patch execution (if candidate provider given)
        patch_applied = False
        patch_verified = False
        if patch_candidate_fn and defect_reproduced:
            patch_applied = patch_candidate_fn(self)
            if patch_applied:
                # Step 5: Oracle re-run
                after_res = self.dispatch(ACIAction("RUN_ORACLE", {"script": oracle_spec.reproduction_code}))
                patch_verified = after_res.success

        return {
            "defect_reproduced": defect_reproduced,
            "target_file": oracle_spec.target_file,
            "target_symbol": oracle_spec.target_symbol,
            "symbol_context": symbol_info,
            "patch_applied": patch_applied,
            "patch_verified": patch_verified,
            "oracle_script": oracle_spec.reproduction_code,
        }
