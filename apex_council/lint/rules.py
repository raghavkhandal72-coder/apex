"""
Tiny built-in linter (stdlib `ast` only). Emits reviewdog rdjson so the PR Action
works on day one with no other tool installed.

Rules (deliberately few, low false-positive):
  APX001 bare `except:`                      APX004 `eval()` / `exec()`
  APX002 mutable default argument            APX005 subprocess/os.system with shell
  APX003 hardcoded credential-looking string APX006 `assert` used on a tuple (always true)

Usage:
  python -m apex_council.lint.rules src/ other.py --format rdjson
  python -m apex_council.lint.rules src/ --format text
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List

SECRET_NAME = re.compile(r"(password|passwd|secret|api[_-]?key|token|private[_-]?key)", re.I)
SECRET_VALUE = re.compile(r"^(AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_\-]{30,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,})$")
PLACEHOLDER = re.compile(r"^(|\.\.\.|changeme|xxx+|<.*>|your[_-].*|\$\{.*\}|none|null|example.*)$", re.I)


def _finding(path, node, code, msg, sev="WARNING"):
    return {
        "message": msg,
        "severity": sev,
        "code": {"value": code},
        "location": {
            "path": path.replace("\\", "/"),
            "range": {
                "start": {
                    "line": getattr(node, "lineno", 1),
                    "column": getattr(node, "col_offset", 0) + 1,
                }
            },
        },
    }


def _is_call(node, names):
    f = getattr(node, "func", None)
    if isinstance(f, ast.Name):
        return f.id in names
    if isinstance(f, ast.Attribute):
        return f.attr in names
    return False


def lint_source(source: str, path: str = "<memory>") -> List[dict]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [
            {
                "message": f"Syntax error: {exc.msg}",
                "severity": "ERROR",
                "code": {"value": "APX000"},
                "location": {
                    "path": path.replace("\\", "/"),
                    "range": {"start": {"line": exc.lineno or 1}},
                },
            }
        ]
    out: List[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            out.append(
                _finding(
                    path,
                    node,
                    "APX001",
                    "Bare `except:` also catches KeyboardInterrupt/SystemExit. Use `except Exception:`.",
                )
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for d in list(node.args.defaults) + [x for x in node.args.kw_defaults if x is not None]:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)) or (
                    isinstance(d, ast.Call)
                    and isinstance(d.func, ast.Name)
                    and d.func.id in {"list", "dict", "set"}
                ):
                    out.append(
                        _finding(
                            path,
                            d,
                            "APX002",
                            "Mutable default argument is shared between calls. Use `None` and create it inside.",
                        )
                    )
        elif isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                val = node.value.value
                names = [t.id for t in node.targets if isinstance(t, ast.Name)] + [
                    t.attr for t in node.targets if isinstance(t, ast.Attribute)
                ]
                if SECRET_VALUE.match(val) or (
                    any(SECRET_NAME.search(n) for n in names)
                    and len(val) >= 8
                    and not PLACEHOLDER.match(val)
                ):
                    out.append(
                        _finding(
                            path,
                            node,
                            "APX003",
                            "Possible hardcoded credential. Load it from the environment instead.",
                            "ERROR",
                        )
                    )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                out.append(
                    _finding(
                        path,
                        node,
                        "APX004",
                        f"`{node.func.id}()` runs arbitrary code. Avoid it on untrusted input.",
                        "ERROR",
                    )
                )
            elif (
                _is_call(node, {"system", "popen"})
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                out.append(
                    _finding(
                        path,
                        node,
                        "APX005",
                        "`os.system` goes through the shell. Prefer `subprocess.run([...])`.",
                        "ERROR",
                    )
                )
            elif _is_call(node, {"run", "call", "Popen", "check_output", "check_call"}):
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        out.append(
                            _finding(
                                path,
                                node,
                                "APX005",
                                "`shell=True` enables shell injection. Pass an argument list instead.",
                                "ERROR",
                            )
                        )
        elif isinstance(node, ast.Assert) and isinstance(node.test, ast.Tuple) and node.test.elts:
            out.append(
                _finding(
                    path,
                    node,
                    "APX006",
                    "`assert (cond, msg)` is a non-empty tuple and always true. Remove the parentheses.",
                )
            )
    return out


def iter_files(paths: Iterable[str]):
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.rglob("*.py")):
                if not any(
                    part in {".git", "venv", ".venv", "node_modules", "__pycache__"} for part in f.parts
                ):
                    yield f
        elif pp.suffix == ".py":
            yield pp


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apex built-in linter")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--format", choices=["rdjson", "text"], default="text")
    ap.add_argument("--fail-on-error", action="store_true")
    args = ap.parse_args(argv)

    diags: List[dict] = []
    for f in iter_files(args.paths):
        diags += lint_source(f.read_text(encoding="utf-8", errors="replace"), str(f))
    if args.format == "rdjson":
        print(json.dumps({"source": {"name": "apex-lint"}, "diagnostics": diags}))
    else:
        for d in diags:
            loc = d["location"]
            print(f"{loc['path']}:{loc['range']['start']['line']}: [{d['code']['value']}] {d['message']}")
        print(f"{len(diags)} finding(s)")
    return 1 if args.fail_on_error and any(d["severity"] == "ERROR" for d in diags) else 0


if __name__ == "__main__":
    sys.exit(main())
