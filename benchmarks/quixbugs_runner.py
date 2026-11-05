#!/usr/bin/env python3
"""
QuixBugs benchmark runner for `apex cegis` (stdlib only).

Why this exists: a benchmark written by the tool's own author is circular.
QuixBugs (https://github.com/jkoppel/QuixBugs) is an external, standard
program-repair benchmark: 40 small Python programs, each with one buggy line.

Honest protocol
  * Only a few "visible" test cases are given to Apex.
  * The repaired code is then checked, independently of Apex, against ALL cases
    (including hidden ones) and against the reference implementation's outputs.
  * Statuses: REPAIRED (passes everything), OVERFIT (passes visible, fails
    hidden), UNREPAIRED, TIMEOUT, ERROR.
  * Programs whose reference solution cannot be evaluated from JSON test cases
    (e.g. graph-node programs) are SKIPPED and reported as skipped, not hidden.

Usage
  git clone https://github.com/jkoppel/QuixBugs
  python benchmarks/quixbugs_runner.py --quixbugs QuixBugs --apex dist/apex.pyz
  python benchmarks/quixbugs_runner.py --quixbugs QuixBugs --only bitcount gcd

Assumed CLI:
  python apex.pyz cegis <file.py> --tests "<assert line>\n<assert line>..."
Assumed output: repaired code printed after the line
  --- SYNTHESIZED REPAIRED CODE ---
and terminated by a line made of '=' characters (or end of output).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MARKER = "--- SYNTHESIZED REPAIRED CODE ---"

HARNESS = r'''
import copy, json, sys, types
src_path, cases_path, name, mode = sys.argv[1:5]
sys.setrecursionlimit(10000)

def norm(x):
    if isinstance(x, types.GeneratorType):
        x = list(x)
    if isinstance(x, (tuple, list)):
        return [norm(i) for i in x]
    return x

def same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-6
        except Exception:
            return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(i, j) for i, j in zip(a, b))
    return a == b

ns = {"__name__": "candidate"}
try:
    exec(compile(open(src_path, encoding="utf-8").read(), src_path, "exec"), ns)
    fn = ns[name]
except BaseException:
    print(json.dumps(None)); sys.exit(0)

cases = json.load(open(cases_path, encoding="utf-8"))
out = []
for case in cases:
    try:
        if mode == "ref":
            raw = fn(*copy.deepcopy(case))
            gen = isinstance(raw, types.GeneratorType)
            val = list(raw) if gen else raw
            n = norm(val)
            json.dumps(n)
            out.append({"norm": n, "repr": repr(val), "gen": gen})
        else:
            got = norm(fn(*copy.deepcopy(case["args"])))
            out.append(bool(same(got, case["norm"])))
    except BaseException:
        out.append(None if mode == "ref" else False)
print(json.dumps(out))
'''


def run_harness(py_file, name, cases, mode, timeout):
    with tempfile.TemporaryDirectory() as td:
        cp, hp = Path(td) / "cases.json", Path(td) / "harness.py"
        cp.write_text(json.dumps(cases), encoding="utf-8")
        hp.write_text(HARNESS, encoding="utf-8")
        try:
            p = subprocess.run(
                [sys.executable, "-E", "-s", str(hp), str(py_file), str(cp), name, mode],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return "TIMEOUT"
        lines = [l for l in p.stdout.splitlines() if l.strip()]
        if not lines:
            return None
        try:
            return json.loads(lines[-1])
        except ValueError:
            return None


def load_cases(path):
    cases = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            item = json.loads(line)
            cases.append(item[0])  # item = [args, expected]; expected comes from reference
    return cases


def build_command(python, apex, file, tests, extra):
    return [python, str(apex), "cegis", str(file), "--tests", tests] + list(extra)


def extract_repaired(stdout):
    if MARKER not in stdout:
        return None
    body = stdout.split(MARKER, 1)[1]
    keep = []
    for line in body.splitlines():
        if re.fullmatch(r"\s*={5,}\s*", line):
            break
        keep.append(line)
    code = "\n".join(keep).strip()
    return code + "\n" if code else None


def evaluate(name, root, args):
    buggy = root / "python_programs" / f"{name}.py"
    ref = root / "correct_python_programs" / f"{name}.py"
    cases_file = root / "json_testcases" / f"{name}.json"
    if not (buggy.exists() and ref.exists() and cases_file.exists()):
        return "SKIPPED", "missing files", 0.0
    try:
        arg_cases = load_cases(cases_file)
    except Exception as exc:
        return "SKIPPED", f"bad testcases: {exc}", 0.0
    if len(arg_cases) < 2:
        return "SKIPPED", "fewer than 2 test cases", 0.0

    refout = run_harness(ref, name, arg_cases, "ref", args.timeout)
    if not isinstance(refout, list) or any(r is None for r in refout):
        return "SKIPPED", "reference not evaluable from JSON cases", 0.0
    cases = [{"args": a, "norm": r["norm"]} for a, r in zip(arg_cases, refout)]

    base = run_harness(buggy, name, cases, "check", args.timeout)
    if not isinstance(base, list) or all(base):
        return "SKIPPED", "buggy version passes all cases", 0.0

    k = max(1, min(args.visible, len(cases) - 1))
    # Visible set must contain at least one failing case, otherwise Apex has no signal.
    order = sorted(range(len(cases)), key=lambda i: base[i])  # failing first
    visible_idx = sorted(set([order[0]] + [i for i in range(len(cases)) if i != order[0]][: k - 1]))
    hidden_idx = [i for i in range(len(cases)) if i not in visible_idx]

    lines = []
    for i in visible_idx:
        call = f"{name}(*{arg_cases[i]!r})"
        if refout[i]["gen"]:
            call = f"list({call})"
        lines.append(f"assert {call} == {refout[i]['repr']}")
    tests = "\n".join(lines)

    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / f"{name}.py"
        shutil.copyfile(buggy, work)
        cmd = build_command(sys.executable, args.apex, work, tests, args.extra)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        t0 = time.perf_counter()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=args.apex_timeout, env=env)
        except subprocess.TimeoutExpired:
            return "TIMEOUT", "apex exceeded time limit", time.perf_counter() - t0
        dt = time.perf_counter() - t0
        code = extract_repaired(p.stdout)
        if code is None:
            tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or [""]
            status = "ERROR" if p.returncode not in (0, 1) else "UNREPAIRED"
            return status, tail[0][:80], dt
        fixed = Path(td) / f"fixed_{name}.py"
        fixed.write_text(code, encoding="utf-8")
        res = run_harness(fixed, name, cases, "check", args.timeout)

    if not isinstance(res, list):
        return "UNREPAIRED", "repaired code did not run / timed out", dt
    vis_ok = all(res[i] for i in visible_idx)
    hid_ok = all(res[i] for i in hidden_idx)
    if vis_ok and hid_ok:
        return "REPAIRED", f"{len(visible_idx)} visible / {len(hidden_idx)} hidden", dt
    if vis_ok:
        return "OVERFIT", f"passes visible, fails {sum(not res[i] for i in hidden_idx)} hidden", dt
    return "UNREPAIRED", "still fails visible tests", dt


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quixbugs", required=True, type=Path, help="path to cloned QuixBugs repo")
    ap.add_argument("--apex", default=Path("dist/apex.pyz"), type=Path)
    ap.add_argument("--visible", type=int, default=3, help="test cases shown to Apex (rest are hidden)")
    ap.add_argument("--timeout", type=int, default=10, help="seconds per harness run")
    ap.add_argument("--apex-timeout", type=int, default=120, help="seconds per apex run")
    ap.add_argument("--only", nargs="*", help="run only these program names")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--extra", nargs="*", default=[], help="extra args passed to apex cegis, e.g. --strict")
    ap.add_argument("--json-out", type=Path, default=Path("benchmarks/quixbugs_results.json"))
    ap.add_argument("--md-out", type=Path, default=Path("benchmarks/quixbugs_results.md"))
    args = ap.parse_args()

    names = args.only or sorted(p.stem for p in (args.quixbugs / "python_programs").glob("*.py")
                                if not p.stem.endswith("_test") and p.stem != "node")
    if args.limit:
        names = names[: args.limit]

    rows = []
    print(f"{'program':<26}{'status':<12}{'time':>8}  detail")
    print("-" * 78)
    for n in names:
        status, detail, dt = evaluate(n, args.quixbugs, args)
        rows.append({"program": n, "status": status, "detail": detail, "seconds": round(dt, 2)})
        print(f"{n:<26}{status:<12}{dt:>7.1f}s  {detail}", flush=True)

    count = lambda s: sum(r["status"] == s for r in rows)
    attempted = sum(r["status"] != "SKIPPED" for r in rows)
    summary = {
        "total_programs": len(rows), "attempted": attempted, "skipped": count("SKIPPED"),
        "repaired": count("REPAIRED"), "overfit": count("OVERFIT"),
        "unrepaired": count("UNREPAIRED"), "timeout": count("TIMEOUT"), "error": count("ERROR"),
    }
    print("-" * 78)
    print(f"REPAIRED {summary['repaired']} of {attempted} attempted "
          f"({summary['overfit']} overfit, {summary['unrepaired']} unrepaired, "
          f"{summary['timeout']} timeout, {summary['error']} error; {summary['skipped']} skipped)")

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps({"summary": summary, "results": rows}, indent=2), encoding="utf-8")
    md = ["| Program | Status | Time (s) | Detail |", "|---|---|---|---|"]
    md += [f"| {r['program']} | {r['status']} | {r['seconds']} | {r['detail']} |" for r in rows]
    md += ["", f"**Repaired {summary['repaired']} of {attempted} attempted programs** "
               f"({summary['skipped']} skipped as not evaluable). Hidden tests are never shown to Apex."]
    args.md_out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {args.json_out} and {args.md_out}")


if __name__ == "__main__":
    main()
