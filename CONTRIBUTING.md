# Contributing

Thanks for helping. The project rule: **standard library only** at runtime (`python tools/check_stdlib_only.py` enforces it).

## Setup
```bash
git clone https://github.com/YOUR_USER/apex && cd apex
python -m unittest discover -s tests
```

## Good first contributions
- **Add a mutation operator** (e.g. `and`<->`or`, `+1`/`-1` on a constant). Add a test with a buggy and a fixed snippet.
- **Add a QuixBugs program** that the runner currently skips, and make it evaluable.
- **Add a lint rule** in `apex_council/lint/rules.py` with a positive and a negative test.
- **Report a bug Apex cannot fix**: open an issue with the file and failing tests.

## Pull requests
1. One logical change per PR, with tests.
2. No new runtime dependencies. Dev tools (ruff, mypy) are fine in CI only.
3. Claims in docs must be backed by a test or a benchmark. Prefer "bounded" and "heuristic" over "proven".
