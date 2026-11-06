"""
Apex Mutation Challenge: Lightweight stdlib mutation testing.
Challenges your test suite with targeted single-token AST mutants.
Distinguishes real test verification from fake line coverage!
"""
from __future__ import annotations

import ast
import difflib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from apex_council.security.sandbox import HermeticExecutionSandbox
from apex_council.synthesis.cegis_engine import CEGISEngine
from apex_council.ui.repair_report import Style, token_changes, _supports_color, _unicode_ok


@dataclass(frozen=True)
class MutantResult:
    mutant_id: int
    mutated_code: str
    diff_desc: str
    status: str  # "KILLED" | "SURVIVED" | "TIMEOUT"


@dataclass(frozen=True)
class ChallengeReport:
    total_mutants: int
    killed: int
    survived: int
    timed_out: int
    score_pct: float
    survived_mutants: List[MutantResult]
    duration_sec: float


def run_mutation_challenge(
    target_src: str,
    test_src: str,
    target_name: str = "program.py",
    max_mutants: int = 30,
    timeout_sec: float = 2.0,
) -> ChallengeReport:
    """Executes mutation testing against target code and test suite."""
    start_t = time.perf_counter()

    # 1. Baseline: tests must pass on original code
    baseline_harness = f"{target_src}\n\n{test_src}"
    base_ok, _, base_out = HermeticExecutionSandbox.execute_isolated(baseline_harness, timeout_sec=timeout_sec)
    if not base_ok:
        raise ValueError(f"Tests already fail on original code: {base_out.strip()[:100]}")

    # 2. Generate candidate mutants using CEGIS mutation grammar
    candidates = CEGISEngine.generate_candidate_programs(target_src)
    candidates = candidates[:max_mutants]

    killed = 0
    survived = 0
    timed_out = 0
    survived_list: List[MutantResult] = []

    for idx, mutant in enumerate(candidates, 1):
        mutant_harness = f"{mutant}\n\n{test_src}"
        passed, _, out = HermeticExecutionSandbox.execute_isolated(mutant_harness, timeout_sec=timeout_sec)

        # Compute diff description
        changes = []
        old_lines = target_src.splitlines()
        new_lines = mutant.splitlines()
        sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                o = "".join(old_lines[i1:i2]).strip()
                n = "".join(new_lines[j1:j2]).strip()
                changes.append(f"{o} -> {n}")
        diff_str = "; ".join(changes) if changes else "mutation"

        if "TIMEOUT" in out:
            timed_out += 1
            killed += 1  # Timeout is considered killed (infinite loop caught)
        elif not passed:
            killed += 1
        else:
            survived += 1
            survived_list.append(MutantResult(
                mutant_id=idx,
                mutated_code=mutant,
                diff_desc=diff_str,
                status="SURVIVED",
            ))

    total = len(candidates)
    score = (killed / total * 100.0) if total > 0 else 100.0
    duration = time.perf_counter() - start_t

    return ChallengeReport(
        total_mutants=total,
        killed=killed,
        survived=survived,
        timed_out=timed_out,
        score_pct=round(score, 1),
        survived_mutants=survived_list,
        duration_sec=round(duration, 2),
    )


def render_challenge_report(rep: ChallengeReport, filename: str = "program.py", stream=None) -> str:
    """Formats terminal report for mutation challenge."""
    stream = stream or sys.stdout
    st = Style(_supports_color(stream), _unicode_ok(stream))
    w = 64
    out: List[str] = []

    out.append(st.bold(f"APEX MUTATION CHALLENGE  {st.arrow}  {filename}"))
    out.append(st.dim(st.rule * w))
    out.append(f"  Mutants Evaluated: {rep.total_mutants}")
    out.append(f"  {st.green('Mutants Killed:')}   {rep.killed}  (tests correctly caught the defect)")
    out.append(f"  {st.red('Mutants Survived:')} {rep.survived}  (blindspots in your test suite!)")
    out.append(f"  Execution Time:    {rep.duration_sec:.1f}s")
    out.append("")

    color_fn = st.green if rep.score_pct >= 80.0 else (st.yellow if rep.score_pct >= 50.0 else st.red)
    out.append(f"  {st.bold('Mutation Resilience Score:')} {color_fn(f'{rep.score_pct:.1f}%')}")
    out.append("")

    if rep.survived_mutants:
        out.append(st.bold(st.red("Test Suite Blindspots (Mutants that passed your tests undetected):")))
        for m in rep.survived_mutants[:5]:
            out.append(f"  {st.bad} Mutant #{m.mutant_id}: {m.diff_desc}")
            out.append(st.dim("    -> Tests still passed! Add an assertion verifying this boundary."))
    else:
        out.append(st.green(f"  {st.ok} Flawless suite! All mutants were killed by tests."))

    out.append(st.dim(st.rule * w))
    return "\n".join(out)
