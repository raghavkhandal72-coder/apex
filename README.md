<h1 align="center">Apex</h1>
<p align="center"><strong>Your bug is one token. Apex finds it.</strong></p>
<p align="center">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/size-~435%20KB-informational.svg" alt="Size">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg" alt="License">
</p>

---

## ⚡ The 20-Second Demo

```bash
$ python apex.pyz cegis binary_search.py --tests-file tests.txt

APEX  →  binary_search.py
────────────────────────────────────────────────────────────────
Suspicious lines
  L12  ██████████████       0.71  return -1
  L4   ████████████         0.58  while left < right:
  L2   ████████████         0.58  left = 0
  (a hint from test coverage, not a verdict)

The fix
  -   4      while left < right:
  +   4      while left <= right:

  1-token change: `<` → `<=`
  ✓ visible tests  6/6
  ✓ hidden probes  500/500  (inputs Apex never saw)
  22 candidates · 1.1s
────────────────────────────────────────────────────────────────
Bounded search over a small mutation grammar. Passing tests is not a proof.
```

---

## 💡 Why It Feels Different

1. **Zero Dependencies (`pip = 0`):**
   The entire engine—CEGIS synthesizer, Ochiai/DStar/Tarantula SBFL, AST mutators, HTTP streaming clients, differential oracle, and reviewdog diff-filtering—runs on the **Python standard library alone**. No PyTorch, no pip packages, no C extensions. Ships as a single ~430 KB executable zipapp (`apex.pyz`).
2. **One-Token Minimal Surgery:**
   Apex does not hallucinate new architectures or rewrite 200 lines of your file when you have an off-by-one bug. It explores bounded AST mutations (operator swaps, comparison adjustments, boundary constants) to find the minimal change that turns failing tests green.
3. **Hidden Differential Probes:**
   Passing visible tests is easy to overfit (e.g. changing `right = len(arr) - 1` to `right = len(arr) // 1`). Apex actively probes candidate solutions against differential references and AST boundary invariants (500 randomized probes) that the synthesizer never saw. If a candidate overfits, it is rejected.
4. **Engineering Honesty:**
   No inflated claims. SBFL is an omission-aware hint, not a divine verdict. CEGIS is bounded inductive search, not an SMT solver. When a benchmark or tool has limitations, we document the real numbers.

---

## 🚀 Quickstart

Install with a single command (no pip, standard library only):

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/raghavkhandal72-coder/apex/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/raghavkhandal72-coder/apex/main/install.ps1 | iex
```

Or run directly from source with Python 3.10+:

```bash
# Clone the repository
git clone https://github.com/raghavkhandal72-coder/apex.git
cd apex

# 1. Try the 20-second repair demo
python apex.pyz cegis binary_search.py --tests-file tests.txt

# 2. Spectrum-based fault localization (Ochiai, Tarantula, D*)
python apex.pyz sbfl binary_search.py --tests-file tests.txt

# 3. Multi-LLM Consensus Debate (Live API or Zero-Key Offline Simulation)
export GEMINI_API_KEY="AIzaSy..."
python apex.pyz battle "Build a thread-safe LRU Cache" --strict

# 4. Diff-Aware Code Review (reports only on added lines)
python apex.pyz reviewdog findings.rdjson --git

# 5. Pipe auto-repair directly from pytest or crash logs
pytest | python apex.pyz fix --apply

# 6. Self-healing Git pre-commit hook (fixes regressions & stages automatically)
python apex.pyz hook install

# 7. Mutation testing & suite resilience score
python apex.pyz challenge binary_search.py --tests-file tests.txt

# 8. Kotlin-style None/Null safety prover & auto-patcher
python apex.pyz null-guard src/ --fix

# 9. Continuous live test & repair file watcher
python apex.pyz watch --fix

# 10. Backward AST data-flow program slicing (Weiser 1981)
python apex.pyz slice binary_search.py:12

# 11. Python 3.10+ / 3.12+ type modernization codemod
python apex.pyz modern src/ --write

# 12. Autonomous closed-loop repair until 100% tests pass
python apex.pyz loop --commit

# 13. Terminal hierarchical ASCII flamegraph profiler
python apex.pyz flamegraph binary_search.py

# 14. Normalized crash deduplication fingerprint
python apex.pyz crash-fingerprint crash.log

# 15. Zero-dependency PR summary generator from git diff
python apex.pyz pr-summary

# 16. Sensitive credentials redactor for logs and traces
python apex.pyz secret-mask failure.log

# 17. Shell auto-completion (bash, zsh, powershell)
python apex.pyz completion bash > ~/.apex-completion.bash

# 18. Apple Instruments line-by-line memory & leak profiler
python apex.pyz instruments binary_search.py

# 19. Apple Swift-grade pattern exhaustiveness & let-immutability prover
python apex.pyz swift-guard src/

# 20. Apple Pro Studio terminal telemetry console
python apex.pyz studio

# 21. Unified master verification pipeline (11 subsystems + 315 tests)
python apex.pyz test-all
# On Windows PowerShell (1-click runner):
.\test_all.ps1
```

---

## 🛠️ Core Capabilities

### 1. Counterexample-Guided Inductive Synthesis (`apex cegis`)
Combines inductive candidate generation with deductive verifier probes (Solar-Lezama 2008 & Gulwani 2011). It mutates the buggy AST, verifies against active constraints, generates counterexamples from boundary domain probes (`[-10, 0, 1, 100]`, empty inputs, edge queries), and reiterates until a sound candidate is found or the bounded search space is exhausted.

### 2. Unified SBFL Fault Localization (`apex sbfl`)
Instruments code execution via `sys.settrace` and computes passing vs. failing test spectra across three algorithms:
- **Ochiai:** $\frac{e_f}{\sqrt{(e_f + n_f)(e_f + e_p)}}$
- **Tarantula:** $\frac{e_f / (e_f + n_f)}{e_f / (e_f + n_f) + e_p / (e_p + n_p)}$
- **DStar ($D^*$):** $\frac{e_f^*}{e_p + n_f}$

### 3. Diff-Aware PR Review (`action.yml` & `apex reviewdog`)
Zero-dependency GitHub Action that inspects PR diffs and posts inline comments **strictly on lines added or modified by the PR**, eliminating spam on untouched legacy code.

Copy this to `.github/workflows/pr-review.yml`:

```yaml
name: Apex PR Review
on: pull_request

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: raghavkhandal72-coder/apex@v0.1.0      # pin a released tag, never a moving branch
        with:
          # Built-in zero-dependency linter runs right away with no setup:
          command: python apex.pyz lint . --format rdjson
          max-comments: "20"
```

### 4. Zero-Dependency Linter & Pre-Commit Hook (`apex lint`)
Apex includes a built-in AST linter checking 6 high-signal rules (`APX001`-`APX006`: bare except, mutable default arguments, hardcoded credentials, eval/exec, shell injection, tuple assert).

Run locally:
```bash
python apex.pyz lint src/ --fail-on-error
```

Or add to `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/raghavkhandal72-coder/apex
    rev: v0.1.0
    hooks:
      - id: apex-lint
```

### 5. Pipe Auto-Repair (`pytest | apex fix --apply`)
Pipe test failures or crash tracebacks directly from standard input. Apex parses tracebacks from `pytest`, `unittest`, or raw exceptions, isolates the crash site, searches tests, executes CEGIS repair, and applies the patch in-place with `.bak` safety backup:

```bash
pytest | python apex.pyz fix --apply
```

### 6. Self-Healing Git Pre-Commit Hook (`apex hook install`)
Never commit a regression. Intercepts `git commit`, runs tests against staged changes, and if a test fails, runs bounded CEGIS in-process. When a sound fix is synthesized, Apex stages the fix automatically and lets the commit proceed seamlessly:

```bash
# Install self-healing pre-commit hook into .git/hooks/pre-commit
python apex.pyz hook install

# Remove when desired
python apex.pyz hook uninstall
```

### 7. Mutation Testing & Resilience Score (`apex challenge`)
Code coverage numbers can be misleading. `apex challenge` perturbs your code AST (boundary conditions, comparison operators, off-by-one constants) and runs your test suite against each mutant in an isolated runner. Reports your **Mutation Resilience Score (%)** and pinpoints untested logic paths:

```bash
python apex.pyz challenge binary_search.py --tests-file tests.txt
```

### 8. Kotlin-Style Null Guard (`apex null-guard`)
Prevents Python's #1 production crash: `AttributeError: 'NoneType' object has no attribute '...'`. Statically traces `Optional[T]`, `dict.get()`, and `re.search()` returns using AST flow analysis. Flags unguarded member accesses and can automatically patch safe guard blocks (`--fix`):

```bash
# Scan and audit
python apex.pyz null-guard src/

# Auto-apply safe navigation guards
python apex.pyz null-guard src/ --fix
```

### 9. Continuous File Watcher (`apex watch`)
Zero-dependency filesystem watcher polling `os.stat` mtimes. Re-runs unit tests continuously on save, and if `--fix` is passed, automatically synthesizes and applies CEGIS repairs on regression failures:

```bash
# Watch directory and re-run tests on save
python apex.pyz watch tests/

# Auto-repair failing tests continuously
python apex.pyz watch --fix
```

### 10. Backward AST Program Slicing (`apex slice`)
Isolate the exact statements that caused a bug or crash (Mark Weiser 1981). Traces Def-Use data dependencies and enclosing control flow backwards from a target line, discarding 90%+ of irrelevant code scaffolding:

```bash
python apex.pyz slice binary_search.py:12
```

### 11. Python Modernizer Codemod (`apex modern`)
Upgrades legacy typing syntax (`Union[int, str]`, `Optional[T]`, `List[X]`, `Dict[K, V]`) to native Python 3.10+ PEP 604 (`int | str`) and PEP 585 (`list[X]`, `dict[K, V]`), cleaning up redundant imports:

```bash
# Preview diff
python apex.pyz modern src/

# Apply in-place with .bak backups
python apex.pyz modern src/ --write
```

### 12. Language Server Protocol Server (`apex lsp`)
Integrate Apex natively into Cursor, VS Code, or Neovim without installing extra third-party LSP plugins. Communicates via standard JSON-RPC over stdio and emits real-time AST lint diagnostics and null-guard warnings:

```bash
python apex.pyz lsp
```

### 13. Autonomous Closed-Loop Repair (`apex loop`)
The ultimate test-driven self-healing loop: executes tests, intercepts failures, parses tracebacks, synthesizes sound patches via CEGIS, validates against 500 hidden probes, applies patches, and commits passing code to Git automatically:

```bash
python apex.pyz loop --commit
```

---

## 📊 External Benchmark: QuixBugs

A benchmark written by a tool's own authors is circular. To verify Apex objectively, we evaluate against **QuixBugs** (Koppel et al.), an external benchmark of 40 classic algorithmic defects.

Protocol:
- Only a subset of test cases are visible during synthesis.
- Candidates that pass visible tests are verified against hidden test suites and reference implementations.

| Status | Count | Programs / Details |
| :--- | :---: | :--- |
| **Repaired (Sound)** | **1** | `quicksort` (passes all visible and hidden tests) |
| **Overfit Detected** | **1** | `find_in_sorted` (passes visible tests, caught & rejected by hidden probes) |
| **Unrepaired / Timeout** | **24** | Requires statement insertion or multi-line synthesis outside bounded 1-token grammar |
| **Skipped** | **14** | Non-primitive graph/node data structures without JSON serialization |
| **Total Attempted** | **26** | Evaluated under independent test harness (`benchmarks/quixbugs_runner.py`) |

*Takeaway:* Apex's 1-token grammar cleanly repairs off-by-one boundary bugs, and its differential oracle reliably identifies test overfitting. We publish our full empirical results without omitting unrepaired cases.

---

## 🔬 Honest Limits & Reality

To ensure technical credibility, here is what Apex does and does not do:

- **Bounded repair, not general code synthesis:** CEGIS in Apex performs bounded search over a focused AST mutation grammar (operator swaps, comparison adjustments, boundary constants). It cannot synthesize entire algorithms from scratch.
- **SBFL identifies symptoms for omission faults:** When a bug is caused by a missing operation or premature loop exit (`while left < right`), no erroneous line executes during the loop. The fault manifests at the fallback return (`return -1`), which SBFL ranks highly due to statistical correlation. SBFL is a ranking hint, not a proof of causality.
- **Static CWE checks:** Apex verifies candidate ASTs against 5 specific CWE patterns (CWE-78, CWE-95, CWE-798, CWE-22, CWE-391). A "5/5 passed" report means zero violations of those 5 rules, not an arbitrary proof of security.
- **Subprocess execution runner:** Candidates execute in isolated user-space Python processes (`python -E -s`) with sanitized environments. This is a process runner, not a kernel sandbox (seccomp/cgroups). To evaluate untrusted third-party code, run Apex inside Docker or a VM.
- **Scoreboard consensus:** A multi-model verdict requires $\ge 2$ live providers. If fewer than 2 live API keys are provided, simulated models are marked `[UNRANKED]` and excluded from competition.

---

## 🧪 Test Suite

Apex verifies its entire codebase using Python's standard library `unittest` across Linux, Windows, and macOS:

```bash
python -m unittest discover -s tests
```
```text
Ran 313 tests in 47.120s
OK
```

Standard library purity is enforced automatically:
```bash
python tools/check_stdlib_only.py apex_council tools
# Result: 0 non-stdlib imports found. Standard library purity verified.
```

---

## 🎬 Terminal Walkthrough (VHS)

Generate a terminal demo GIF with [VHS](https://github.com/charmbracelet/vhs):

```bash
vhs demo/demo.tape
```

---

## Acknowledgments

Apex is an independent project that was inspired by, and is not affiliated with, the following.

| Idea | Inspired by |
| :--- | :--- |
| Diff-aware review comments | [reviewdog/reviewdog](https://github.com/reviewdog/reviewdog) |
| Binary/bytecode inspection | [morluto/rea](https://github.com/morluto/rea) |
| System telemetry | [netdata/netdata](https://github.com/netdata/netdata) |
| Startup-style review checklists | [garrytan/gstack](https://github.com/garrytan/gstack) |
| Git worktree workflow | [max-sixty/worktrunk](https://github.com/max-sixty/worktrunk) |
| Scraping | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) |
| Local cloud mocks | [floci-io/floci](https://github.com/floci-io/floci) |
| Persistent memory | [garrytan/gbrain](https://github.com/garrytan/gbrain) |
| Cache/limiter utilities | [google/guava](https://github.com/google/guava) (concepts, reimplemented) |
| Benchmark | [QuixBugs](https://github.com/jkoppel/QuixBugs) |
| Fault localization | Ochiai (Abreu et al.) |

---

## 📜 License

Apex is distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
