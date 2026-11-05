# 🏛️ Apex: Autonomous Multi-Agent Consensus & Bounded Program Repair

> **Stop blindly trusting single-model AI code. Apex coordinates multiple AI models using Monte Carlo Tree Search (MCTS) and repairs edge-case bugs using Counterexample-Guided Inductive Synthesis (CEGIS)—synthesizing bug-resilient software in 100% Pure Python Standard Library (`pip = 0`).**

[![CI Matrix](https://github.com/your-username/apex-council/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external%20pip-brightgreen.svg)]()
[![Tests Passing](https://img.shields.io/badge/tests-246%20passing%20(100%25)-success.svg)]()
[![Single Executable](https://img.shields.io/badge/distribution-388KB%20standalone%20.pyz-orange.svg)]()

---

## ⚡ The 10-Second Pitch

Single LLM coding assistants suffer from hallucinations, brittle edge cases, and silent security vulnerabilities. 

**Apex** treats code generation as an adversarial consensus and bounded verification problem:
1. **Multi-Model Consensus:** Pits specialized agent personas (Commander, Architect, Sentinel, Ninja) against each other.
2. **MCTS Test-Time Compute:** Explores alternative implementation paths with Monte Carlo Tree Search and branch pruning.
3. **CEGIS Bounded Verification:** Actively searches for counterexamples across edge domains (`[-10, 0, 1, 100]`) to falsify and inductively repair proposed code before it lands.
4. **Zero-Dependency Guarantee:** The entire runtime—including HTTP API clients, AST parsing, cryptography, web scraping, and container supervision—runs on the **Python standard library alone**. Zero `pip install` required.

---

## Quickstart

```bash
python apex.pyz --version
export GEMINI_API_KEY=...            # Windows: set GEMINI_API_KEY=...
python apex.pyz "Build a thread-safe LRU Cache" --verbose --strict
```

Without API keys Apex runs in a clearly labeled **offline simulation**. Simulated
providers are never ranked and never count toward consensus. Use `--strict` in CI
and benchmarks so a failed live call aborts instead of falling back.

---

## 🔌 How Model Integration Works: Live vs. Offline Simulation

Apex supports both real live foundation models and an instant offline simulator:

* **Live Multi-Model Execution:** Set your API keys in your environment:
  ```bash
  export GEMINI_API_KEY="AIzaSy..."      # Google Gemini 1.5 Pro / 2.0 Flash
  export ANTHROPIC_API_KEY="sk-ant-..."  # Anthropic Claude 3.5 Sonnet
  export OPENAI_API_KEY="sk-proj-..."    # OpenAI GPT-4o
  # OR use local edge Ollama (Zero-Cost Live Consensus):
  export OLLAMA_MODEL="llama3"           # Local Ollama at http://localhost:11434
  ```
  Apex dispatches to configured foundation models simultaneously. Real LLMs draft implementations and cross-examine each other's code.
* **Default Fallback vs. Strict Mode (`--strict`):**
  - *Default Behavior:* On network timeouts, invalid auth, or rate limits, Apex displays a prominent warning box and falls back to offline simulation so casual CLI exploration does not crash.
  - *Strict Mode (`--strict`):* Disables all simulation fallbacks. If any live API call fails, execution halts immediately with a non-zero exit code (`exit 1`). Recommended for CI/CD pipelines and automated benchmarks.
* **Zero External Dependencies (`pip = 0`):** Apex implements custom HTTP/JSON streaming adapters over standard library `urllib.request`. You do **not** need to install `openai`, `anthropic`, or `google-generativeai`.
* **Instant Offline Simulator:** If no API keys are provided (or if `--offline` is passed), Apex automatically falls back to an offline simulated engine. You can clone the repo and run full council debates and verification workflows immediately with zero tokens or internet access.

---

## 🔬 Claims vs. Reality: Engineering Transparency

To ensure absolute credibility with engineers, here is what Apex does and does not do:

* **What CEGIS is:** Counterexample-Guided Inductive Synthesis (Solar-Lezama 2008 & Gulwani 2011). Given an initial buggy AST and active constraints $E$, the synthesizer explores candidate mutations and tests them in isolated subprocesses. When a candidate satisfies $E$, the deductive verifier challenges it with unverified tests and **automated hidden invariant probes** (empty sequence boundaries, single-element boundaries, out-of-bounds queries, missing targets). When an invariant is violated, the verifier extracts a minimal counterexample $t^*$, appends $t^*$ to $E$, and reiterates synthesis. This is **bounded inductive program repair**, not an arbitrary SMT/Z3 solver or Coq proof assistant.
* **What Ochiai SBFL is:** Spectrum-Based Fault Localization (Abreu et al., 2007). It instruments code execution using Python's tracing subsystem (`sys.settrace`), computes passing vs. failing test coverage spectra, and ranks suspicious lines using the formula:
  $$\text{Ochiai}(s) = \frac{e_f(s)}{\sqrt{(e_f(s) + n_f(s)) \cdot (e_f(s) + e_p(s))}}$$
  *Omission Fault Behavior:* For omission-style faults (e.g. an off-by-one loop condition `while left < right` that exits one iteration too early), no erroneous line executes during the loop—the correct action is omitted. Consequently, failures manifest downstream at the fallback (`return -1`), which SBFL flags as suspicious because its execution correlates with failures. SBFL highlights symptom sites; use it as a ranking hint rather than a definitive causal verdict.
* **What Static CWE Checks are:** Apex inspects candidate ASTs against 5 specific CWE classes (CWE-78, CWE-95, CWE-798, CWE-22, CWE-391). A score of "5/5 pass" verifies compliance against this specific rule set—it is NOT a mathematical guarantee of total software security.
* **Subprocess Runner Notice (Not an OS Security Sandbox):** Candidate code execution runs in an isolated user-space Python subprocess (`python -E -s`) with environment variables scrubbed of credentials and secrets. This is an execution runner, NOT a kernel-level security boundary (seccomp/cgroups). To run completely untrusted third-party code safely, deploy Apex inside Docker or a VM container (see `packaging/Dockerfile`).
* **Runtime Workload Benchmark:** Runtime measurements reflect the duration of isolated Python process execution (including compilation and module import overhead). When a test harness is supplied, the exact same benchmark harness is executed against every candidate.
* **Scoreboard Ranking Integrity:** A true consensus winner is crowned only when $\ge 2$ live models participate. If fewer than 2 live models are active, simulated models are marked `[UNRANKED]` and excluded from competition, and a degraded consensus warning is clearly displayed.

---

## Known Limitations

- **Bounded repair, not formal verification.** CEGIS here is test-guided search over a
  small AST mutation grammar (operator swaps, boundary changes, constants). It cannot
  invent new statements or algorithms. Passing tests does not prove correctness.
- **Test-suite overfitting.** With few tests a candidate can pass them without being right.
  Differential probes (`apex_council/synthesis/differential_oracle.py`) compare against a
  reference implementation when one is provided; without a reference, probes only detect
  crashes and invariant violations, not wrong answers.
- **SBFL (Ochiai) limitations.** Spectrum-based localization ranks lines by execution
  correlation with failures. For omission-style faults (e.g. a loop exiting one iteration
  early) it often points at the symptom (`return -1`) rather than the cause
  (`while left < right`). Use it as a hint, not a verdict.
- **Not a security sandbox.** Candidate code runs in an isolated subprocess (`python -E -s`,
  scrubbed environment). This is not seccomp/cgroups. Run Apex inside Docker or a VM for
  untrusted code.
- **Consensus needs 2+ live models.** With fewer, the scoreboard shows a degraded-consensus
  banner and simulated rows are unranked.
- **Static checks only.** "CWE checks: N/5" are AST/regex rules for CWE-78/95/798/22/391,
  not a security audit.
- **Runtime numbers** are wall-clock in an isolated subprocess and depend on the workload;
  compare them only when the same test harness runs for every candidate.

---

## 🚦 Transparent Feature Status & Tested CLI Commands

All commands below are verified and runnable out-of-the-box with the standalone single executable [`dist/apex.pyz`](dist/apex.pyz):

| Subsystem | Maturity | Status & Verification | Runnable CLI Command |
| :--- | :---: | :--- | :--- |
| **MCTS Consensus** | `Stable` | Multi-agent solution search with branch pruning. | `python dist/apex.pyz "Build thread-safe LRU Cache" --offline` |
| **CEGIS Program Repair** | `Beta` | Bounded counterexample search repairing AST operators. | `python dist/apex.pyz cegis examples/unseen_binary_search.py --tests "assert binary_search([1,2,3,4,5], 5) == 4\nassert binary_search([1,2,3,4,5], 1) == 0"` |
| **Ochiai Bug Localizer** | `Stable` | Statistical coverage ranking locating line numbers of failures. | `python dist/apex.pyz localize examples/calculator.py --tests "assert add(2, 3) == 5"` |
| **Unified SBFL Triad** | `Stable` | Ensemble localization combining Ochiai, Tarantula, and D*. | `python dist/apex.pyz sbfl examples/unseen_binary_search.py --tests "assert binary_search([1,2,3,4,5], 5) == 4"` |
| **REA Disassembly** | `Stable` | Disassembles Python bytecode and parses ELF/PE headers. | `python dist/apex.pyz rea examples/calculator.py --disasm` |
| **Cryptographic Evidence** | `Stable` | Commits inspection findings to SHA-256 evidence ledger. | `python dist/apex.pyz rea examples/calculator.py --evidence --claim "Audit add and divide"` |
| **Diff Reviewdog** | `Stable` | Multi-format diagnostic parser filtered against diff hunks. | `python dist/apex.pyz reviewdog examples/diagnostics.json` |
| **Streaming Telemetry** | `Stable` | Pure Python streaming wire protocol for system metrics. | `python dist/apex.pyz netdata --once` |
| **Startup Review Suite** | `Stable` | Office-hours review, CSO threat audit, and ship gating. | `python dist/apex.pyz gstack office-hours "Build distributed queue"` |
| **GBrain Memory Vault** | `Stable` | SQLite persistent episodic memory with cross-session locks. | `python dist/apex.pyz gbrain recall "security"` |
| **Scrapling DOM Engine** | `Stable` | Anti-detection HTML-to-Markdown parser and table extractor. | `python dist/apex.pyz scrape examples/test_page.html --tables` |
| **Transformer Engine** | `Experimental` | Pure Python decoder model with RoPE, GQA, RMSNorm, SwiGLU. | `python dist/apex.pyz transformer train --data examples/corpus.txt` |
| **Local Cloud Mock (Floci)** | `Beta` | Zero-cost local S3, SQS, and DynamoDB emulator. | `python dist/apex.pyz floci s3 list demo-bucket` |
| **Agent Browser & Electron** | `Beta` | Accessible element tree snapshotting and desktop shell bridge. | `python dist/apex.pyz browser snapshot "https://example.com"` |

---

## Benchmarks

Repair quality is measured on **QuixBugs** (external, standard benchmark), not on bugs
written by the Apex authors. Apex sees only a few visible tests; the repaired program is
then checked independently against all cases, including hidden ones.

```bash
git clone https://github.com/jkoppel/QuixBugs
python benchmarks/quixbugs_runner.py --quixbugs QuixBugs --apex dist/apex.pyz --extra --strict
```

| Metric | Result |
|---|---|
| Programs attempted | 26 |
| Repaired (visible + hidden pass) | 1 |
| Overfit (visible pass, hidden fail) | 1 |
| Unrepaired / timeout / error | 24 |
| Skipped (reference not evaluable) | 14 |

Raw results: `benchmarks/quixbugs_results.json`.
The 8-case internal suite in `benchmarks/cegis_benchmark.py` is a **regression test**, not evidence of generality.

### CEGIS Internal Regression Suite (8 Empirical Cases)

The internal regression suite tests that known single-token operator and boundary mutations remain covered:

| Bug ID | Benchmark Problem | Fault Class | Status | Rounds | Verified Fix |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **BUG-01** | Binary Search Boundary | Relational (`<` $\to$ `<=`) | **REPAIRED** | 1 | `while left <= right:` |
| **BUG-02** | Binary Search Midpoint | Arithmetic (`-` $\to$ `+`) | **REPAIRED** | 2 | `mid = (left + right) // 2` |
| **BUG-03** | Binary Search Branch Step | Step Operator (`+` $\to$ `-`) | **REPAIRED** | 1 | `right = mid - 1` |
| **BUG-04** | Calculator Addition Inversion | Arithmetic (`-` $\to$ `+`) | **REPAIRED** | 1 | `return a + b` |
| **BUG-05** | Strict Positivity Boundary | Relational (`>=` $\to$ `>`) | **REPAIRED** | 2 | `return n > 0` |
| **BUG-06** | Linear Search Sentinel | Constant (`0` $\to$ `-1`) | **REPAIRED** | 2 | `return -1` |
| **BUG-07** | Palindrome Inversion | Relational (`!=` $\to$ `==`) | **REPAIRED** | 1 | `return s == s[::-1]` |
| **BUG-08** | Safe Division Missing Guard | Structural Guard Insertion | **UNREPAIRED** | 1 | *(Beyond bounded operator grammar)* |

* **Internal Regression Rate:** 7 of 8 benchmarks repaired (**87.5%**).
* **Structural Fault Boundary:** Faults requiring arbitrary new block insertion (`if b == 0: return 0.0`) are reported as UNREPAIRED by the single-operator bounded grammar.
* **Run regression suite locally (~12s, Zero Dependencies):**
  ```bash
  python benchmarks/cegis_benchmark.py
  ```

---

## 🚀 Quick Start

### Option A: Portable Standalone Executable (Zero Installation)
Download or build the standalone single-file archive (372 KB):

```bash
# 1. Inspect help
python dist/apex.pyz --help

# 2. Convene multi-model council for a task (offline demo)
python dist/apex.pyz "Build a thread-safe LRU Cache" --offline

# 3. Repair a buggy function with CEGIS inductive synthesis
python dist/apex.pyz cegis examples/calculator.py --tests "assert add(2, 3) == 5"
```

### Option B: Local Repository Installation
```bash
git clone https://github.com/your-username/apex-council.git
cd apex-council

# Optional: Run one-line installer
./scripts/install.sh       # Linux / macOS
.\scripts\install.ps1      # Windows PowerShell

# Run the complete test suite (242 tests, ~38s)
python -m unittest discover -s tests

# Run the automated live terminal walkthrough
python scripts/demo_walkthrough.py
```

---

## 🎬 Terminal Walkthrough & Demo Recording

To view or record the terminal demo:

```bash
# Run interactive walkthrough script:
python scripts/demo_walkthrough.py

# Or generate a crisp 30-second terminal GIF using VHS:
vhs demo.tape
```

---

## 🧪 Verification & Test Suite Transparency

Apex maintains an absolute regression-free policy. Every commit is tested across **Linux, Windows, and macOS** on Python 3.10, 3.11, and 3.12:

```bash
python -m unittest discover -s tests
```
```text
Ran 246 tests in 36.421s
OK
```

* **189 Platform Baseline Tests:** MCTS search, CEGIS invariant synthesizer with differential oracle, Ochiai SBFL, Hoare logic, AST mutation fuzzing, DLP sanitization, RBAC, and Git plumbing.
* **20 Tool Integration Tests (`tests/test_e2e_tool_integrations.py`):** REA bytecode/binary inspection, Reviewdog unified diff filtering, Netdata wire protocol.
* **15 Transformer Model Tests (`tests/test_e2e_transformer_model.py`):** ByteTokenizer (0% OOV), RoPE, RMSNorm, GQA, causal masking, KV cache step decoding.
* **7 Training Pipeline Tests (`tests/test_e2e_transformer_pipeline.py`):** Multi-domain text chunking, CrossEntropy loss, AdamW optimizer, warmup-cosine schedule.
* **8 Deployment & Server Tests (`tests/test_e2e_transformer_deployment.py`):** Inference engine, REST server endpoints, TTFT/ITL latency tracking.
* **7 Production Packaging Tests (`tests/test_e2e_production_packaging.py`):** Dockerfile structure, non-root user security, Compose orchestration, self-healing supervisor.

---

## 📦 Pure-Python Transformer: Standalone Project

To keep Apex razor-focused on Multi-Agent Consensus and Bounded Verification, the pure-Python Transformer subsystem (`apex_council/transformer`) is also being packaged into its own dedicated open-source repository:

👉 **[apex-transformer](https://github.com/your-username/apex-transformer)**: *A complete decoder-only Transformer with RoPE, GQA, RMSNorm, SwiGLU, AdamW, and KV-cache written in 100% Pure Python Standard Library with zero pip dependencies.*

---

## 🐳 Production Deployment & Docker Packaging

Apex includes production containerization ready for cloud or edge deployment:

```bash
# Build multi-stage lightweight image (Python 3.11-slim, non-root user)
docker build -f packaging/Dockerfile -t apex .

# Or run with Docker Compose (API on 8000, Netdata telemetry on 19999)
docker compose -f packaging/docker-compose.yml up -d
```

---

## 🤝 Inspirations & Acknowledgments

Apex stands on the shoulders of the open-source community. We gratefully acknowledge the following projects and concepts that inspired our modular subsystems:

| Component | Inspiration / Upstream | Relationship & Notes |
| :--- | :--- | :--- |
| **Reverse Engineering** | [morluto/rea](https://github.com/morluto/rea) | Architecture pattern for evidence-first binary and bytecode inspection. |
| **Diff-Aware Review** | [reviewdog/reviewdog](https://github.com/reviewdog/reviewdog) | Concepts for parsing diagnostic outputs and filtering comments against git diffs. |
| **Streaming Telemetry** | [netdata/netdata](https://github.com/netdata/netdata) | High-frequency telemetry collector and streaming wire protocol structure. |
| **Startup Review Suite** | [garrytan/gstack](https://github.com/garrytan/gstack) | Inspiration for founder-level office hours review, CSO security checklist, and release ship automation. |
| **Git Worktrees** | [max-sixty/worktrunk](https://github.com/max-sixty/worktrunk) | Isolated branch and parallel agent worktree coordination workflows. |
| **Resilient Scraping** | [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | Pure-Python DOM tree construction and table extraction patterns. |
| **Local Cloud Testing** | [floci-io/floci](https://github.com/floci-io/floci) | Inspiration for hermetic local AWS cloud service emulation. |
| **Persistent Memory** | [garrytan/gbrain](https://github.com/garrytan/gbrain) | SQLite persistent memory vault and cross-session knowledge locking. |
| **Resilient Collections** | [google/guava](https://github.com/google/guava) | Ported token-bucket `RateLimiter`, LRU `GuavaCache`, `BiMap`, and `Preconditions`. |

---

## 📜 License

Apex is distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
