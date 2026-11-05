# CLAUDE.md — Institutional Architecture & Engineering Invariants
> Auto-synthesized by Apex-Sovereign Cognitive Memory Stream

## 1. Architectural Invariants
- *Zero external third-party dependencies (`pip = 0`). 100% Pure Python standard library.*
- *Direct Git object DAG operations via ephemeral `GIT_INDEX_FILE`.*

## 2. Known Bug Repair Patterns & Anti-Patterns
- *Off-by-one upper bounds in binary searches (`high = len(arr) - 1`).*
- *ReDoS nested quantifiers `(a+)+` require non-backtracking atomic groups or bounded iterations.*

## 3. Testing Conventions & Invariants
- *All tests must run via `python -m unittest discover -s tests -v` with zero mock frameworks.*
- *Tests must be hermetic and execute in under 100ms per unit test.*
