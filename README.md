<h1 align="center">Apex</h1>
<p align="center"><strong>Your bug is one token. Apex finds it.</strong></p>
<p align="center">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen.svg" alt="Dependencies">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/size-~380%20KB-informational.svg" alt="Size">
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
   The entire engine—CEGIS synthesizer, Ochiai/DStar/Tarantula SBFL, AST mutators, HTTP streaming clients, differential oracle, and reviewdog diff-filtering—runs on the **Python standard library alone**. No PyTorch, no pip packages, no C extensions. Ships as a single ~380 KB executable zipapp (`apex.pyz`).
2. **One-Token Minimal Surgery:**
   Apex does not hallucinate new architectures or rewrite 200 lines of your file when you have an off-by-one bug. It explores bounded AST mutations (operator swaps, comparison adjustments, boundary constants) to find the minimal change that turns failing tests green.
3. **Hidden Differential Probes:**
   Passing visible tests is easy to overfit (e.g. changing `right = len(arr) - 1` to `right = len(arr) // 1`). Apex actively probes candidate solutions against differential references and AST boundary invariants (500 randomized probes) that the synthesizer never saw. If a candidate overfits, it is rejected.
4. **Engineering Honesty:**
   No inflated claims. SBFL is an omission-aware hint, not a divine verdict. CEGIS is bounded inductive search, not an SMT solver. When a benchmark or tool has limitations, we document the real numbers.

---

## 🚀 Quickstart

Run directly with Python 3.10+:

```bash
# Clone the repository
git clone https://github.com/your-username/apex-council.git
cd apex-council

# 1. Try the 20-second repair demo
python apex.pyz cegis binary_search.py --tests-file tests.txt

# 2. Spectrum-based fault localization (Ochiai, Tarantula, D*)
python apex.pyz sbfl binary_search.py --tests-file tests.txt

# 3. Multi-LLM Consensus Debate (Live API or Zero-Key Offline Simulation)
export GEMINI_API_KEY="AIzaSy..."
python apex.pyz battle "Build a thread-safe LRU Cache" --strict

# 4. Diff-Aware Code Review (reports only on added lines)
python apex.pyz reviewdog findings.rdjson --git
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
      - uses: YOUR_USER/apex@v0.1.0      # pin a released tag, never a moving branch
        with:
          # Built-in zero-dependency linter runs right away with no setup:
          command: python apex.pyz lint . --format rdjson
          max-comments: "20"
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
Ran 257 tests in 38.214s
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
