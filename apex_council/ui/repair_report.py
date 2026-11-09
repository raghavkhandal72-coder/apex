"""Delightful, honest terminal report for a program repair (stdlib only).

Shows: where the bug is suspected, the exact minimal change (token-level), and
whether it was verified on visible AND hidden tests. Respects NO_COLOR, non-TTY
pipes (no ANSI), and terminals that cannot print box characters (ASCII fallback).
"""
from __future__ import annotations

import difflib
import os
import re
import sys
from typing import List, Optional, Sequence, Tuple

TOKEN = re.compile(r"\s+|\w+|<=|>=|==|!=|//|\*\*|->|\+=|-=|\*=|/=|<<|>>|[^\w\s]")


def _supports_color(stream) -> bool:
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


def _unicode_ok(stream) -> bool:
    enc = (getattr(stream, "encoding", None) or "ascii").lower()
    try:
        "█▏─✓✗→".encode(enc)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


class Style:
    def __init__(self, color: bool, uni: bool):
        self.color, self.uni = color, uni
        if color and os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                h_out = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(h_out, ctypes.byref(mode))
                kernel32.SetConsoleMode(h_out, mode.value | 0x0004)
            except Exception:
                pass

    def c(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def bold(self, t: str) -> str:
        return self.c(t, "1")

    def dim(self, t: str) -> str:
        return self.c(t, "2")

    def red(self, t: str) -> str:
        return self.c(t, "31")

    def green(self, t: str) -> str:
        return self.c(t, "32")

    def yellow(self, t: str) -> str:
        return self.c(t, "33")

    def cyan(self, t: str) -> str:
        return self.c(t, "36")

    def red_bg(self, t: str) -> str:
        return self.c(t, "41;97")

    def green_bg(self, t: str) -> str:
        return self.c(t, "42;30")

    @property
    def bar(self) -> str:
        return "█" if self.uni else "#"

    @property
    def rule(self) -> str:
        return "─" if self.uni else "-"

    @property
    def ok(self) -> str:
        return "✓" if self.uni else "OK"

    @property
    def bad(self) -> str:
        return "✗" if self.uni else "X"

    @property
    def arrow(self) -> str:
        return "→" if self.uni else "->"


def token_changes(old: str, new: str) -> List[Tuple[str, str]]:
    """Return [(old_token, new_token)] for the changed tokens of one line."""
    a, b = TOKEN.findall(old), TOKEN.findall(new)
    out: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append(("".join(a[i1:i2]).strip(), "".join(b[j1:j2]).strip()))
    return out


def _highlight(old: str, new: str, st: Style) -> Tuple[str, str]:
    a, b = TOKEN.findall(old), TOKEN.findall(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    left, right = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        x, y = "".join(a[i1:i2]), "".join(b[j1:j2])
        if tag == "equal":
            left.append(x)
            right.append(y)
        else:
            if x:
                left.append(st.red_bg(x))
            if y:
                right.append(st.green_bg(y))
    return "".join(left), "".join(right)


def render_repair(
    buggy_src: str,
    fixed_src: str,
    filename: str = "program.py",
    suspects: Optional[Sequence[Tuple[int, float]]] = None,  # [(line_no, score 0..1)]
    visible: Tuple[int, int] = (0, 0),  # (passed, total)
    hidden: Optional[Tuple[int, int]] = None,
    seconds: Optional[float] = None,
    candidates: Optional[int] = None,
    stream=None,
) -> str:
    stream = stream or sys.stdout
    st = Style(_supports_color(stream), _unicode_ok(stream))
    old_lines, new_lines = buggy_src.splitlines(), fixed_src.splitlines()
    out: List[str] = []
    w = 64

    out.append(st.bold(f"APEX  {st.arrow}  {filename}"))
    out.append(st.dim(st.rule * w))

    if suspects:
        out.append(st.bold("Suspicious lines"))
        for ln, score in list(suspects)[:3]:
            n = max(1, round(score * 20))
            bar = st.bar * n
            src = old_lines[ln - 1].strip() if 0 < ln <= len(old_lines) else ""
            out.append(
                f"  {st.yellow(f'L{ln:<3}')} {st.red(bar):<{20 if not st.color else 20 + 9}} {score:.2f}  {st.dim(src[:36])}"
            )
        out.append(st.dim("  (a hint from test coverage, not a verdict)"))
        out.append("")

    changes: List[Tuple[str, str]] = []
    out.append(st.bold("The fix"))
    sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                o, n = old_lines[i1 + k], new_lines[j1 + k]
                changes += token_changes(o, n)
                lo, ln_ = _highlight(o, n, st)
                out.append(f"  {st.red('-')} {st.dim(f'{i1 + k + 1:>3}')}  {lo}")
                out.append(f"  {st.green('+')} {st.dim(f'{j1 + k + 1:>3}')}  {ln_}")
        else:
            for o in old_lines[i1:i2]:
                out.append(f"  {st.red('-')}      {st.red(o)}")
            for n in new_lines[j1:j2]:
                out.append(f"  {st.green('+')}      {st.green(n)}")
            changes += [("<block>", "<block>")]
    if not changes:
        out.append(st.dim("  (no change produced)"))
    out.append("")

    if changes and all(c[0] != "<block>" for c in changes):
        parts = ", ".join(f"`{a or '∅'}` {st.arrow} `{b or '∅'}`" for a, b in changes[:3])
        out.append(f"  {st.cyan(f'{len(changes)}-token change')}: {parts}")

    p, t = visible
    out.append(f"  {st.green(st.ok) if p == t and t else st.red(st.bad)} visible tests  {p}/{t}")
    if hidden is not None:
        hp, ht = hidden
        out.append(
            f"  {st.green(st.ok) if hp == ht and ht else st.red(st.bad)} hidden probes  {hp}/{ht}"
            + st.dim("  (inputs Apex never saw)")
        )
    meta = []
    if candidates is not None:
        meta.append(f"{candidates} candidates")
    if seconds is not None:
        meta.append(f"{seconds:.1f}s")
    if meta:
        out.append(st.dim("  " + " · ".join(meta)))
    out.append(st.dim(st.rule * w))
    out.append(st.dim("Bounded search over a small mutation grammar. Passing tests is not a proof."))
    return "\n".join(out)
