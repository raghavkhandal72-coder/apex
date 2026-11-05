"""Differential oracle for CEGIS verifier probes (stdlib only).

Problem it solves: probes such as `[]`, `[x]`, "missing target" only detect
crashes unless something says what the CORRECT answer is. This module compares
a candidate against a trusted reference implementation (e.g. `bisect`) on
random inputs, so wrong answers become counterexamples too.

NOTE: this runs candidates in-process. Infinite loops cannot be interrupted here,
so call it from the same subprocess runner (with a timeout) that executes candidates.
"""
from __future__ import annotations

import bisect
import copy
import random
from dataclasses import dataclass
from typing import Any, Callable, List, Tuple


@dataclass(frozen=True)
class Counterexample:
    args: Tuple[Any, ...]
    expected: Any
    actual: Any
    kind: str  # wrong_answer | candidate_exception | missing_exception | exception_mismatch

    def describe(self) -> str:
        return f"{self.kind}: args={self.args!r} expected={self.expected!r} actual={self.actual!r}"


def _call(fn: Callable, args: tuple):
    try:
        return True, fn(*copy.deepcopy(args))
    except Exception as exc:  # noqa: BLE001 - we want to classify any failure
        return False, exc


def find_counterexamples(
    candidate: Callable,
    reference: Callable,
    gen: Callable[[random.Random], tuple],
    n: int = 500,
    seed: int = 0,
    max_found: int = 3,
) -> List[Counterexample]:
    """Return up to `max_found` inputs where candidate and reference disagree."""
    rng = random.Random(seed)
    found: List[Counterexample] = []
    seen = set()
    for _ in range(n):
        args = gen(rng)
        key = repr(args)
        if key in seen:
            continue
        seen.add(key)
        ref_ok, ref_val = _call(reference, args)
        cand_ok, cand_val = _call(candidate, args)
        ce = None
        if ref_ok and cand_ok:
            if ref_val != cand_val:
                ce = Counterexample(args, ref_val, cand_val, "wrong_answer")
        elif ref_ok and not cand_ok:
            ce = Counterexample(args, ref_val, repr(cand_val), "candidate_exception")
        elif not ref_ok and cand_ok:
            ce = Counterexample(args, repr(ref_val), cand_val, "missing_exception")
        elif type(ref_val) is not type(cand_val):
            ce = Counterexample(args, repr(ref_val), repr(cand_val), "exception_mismatch")
        if ce:
            found.append(ce)
            if len(found) >= max_found:
                break
    return found


# ---- ready-made generator + reference for search functions -----------------

def sorted_unique_search_gen(rng: random.Random) -> tuple:
    size = rng.choice([0, 1, 1, 2, 3, 5, 8, 20])
    arr = sorted(rng.sample(range(-50, 50), size))
    target = rng.choice(arr) if arr and rng.random() < 0.6 else rng.randint(-60, 60)
    return (arr, target)


def reference_binary_search(arr: list, target: int) -> int:
    """Index of target in a sorted list of unique ints, else -1 (bisect-based)."""
    i = bisect.bisect_left(arr, target)
    return i if i < len(arr) and arr[i] == target else -1


if __name__ == "__main__":
    def buggy(arr, target):
        left, right = 0, len(arr) - 1
        while left < right:
            mid = (left + right) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1

    for ce in find_counterexamples(buggy, reference_binary_search, sorted_unique_search_gen):
        print(ce.describe())
