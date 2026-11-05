# 🏛️ Apex: Autonomous Multi-Agent Consensus & Bounded Verification

> **Stop blindly trusting single-model AI code. Apex coordinates multiple AI models using Monte Carlo Tree Search (MCTS) and hardens edge cases using Counterexample-Guided Inductive Synthesis (CEGIS)—synthesizing bug-resilient software in 100% Pure Python Standard Library (`pip = 0`).**

[![CI Matrix](https://github.com/your-username/apex-council/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external%20pip-brightgreen.svg)]()
[![Tests Passing](https://img.shields.io/badge/tests-241%20passing%20(100%25)-success.svg)]()
[![Single Executable](https://img.shields.io/badge/distribution-372KB%20standalone%20.pyz-orange.svg)]()

---

## ⚡ The 10-Second Pitch

Single LLM coding assistants suffer from hallucinations, brittle edge cases, and silent security vulnerabilities. 

**Apex** treats code generation as an adversarial consensus and bounded verification problem:
1. **Multi-Model Consensus:** Pits specialized agent personas (Commander, Architect, Sentinel, Ninja) against each other.
2. **MCTS Test-Time Compute:** Explores alternative implementation paths with Monte Carlo Tree Search and branch pruning.
3. **CEGIS Bounded Verification:** Actively searches for counterexamples across edge domains (`[-10, 0, 1, 100]`) to falsify and inductively repair proposed code before it lands.
4. **Zero-Dependency Guarantee:** The entire runtime—including HTTP API clients, AST parsing, cryptography, web scraping, and container supervision—runs on the **Python standard library alone**. Zero `pip install` required.

---

## 🔌 How Model Integration Works: Live vs. Offline Simulation

Apex supports both real live foundation models and an instant offline simulator:

* **Live Multi-Model Execution:** Set your API keys in your environment:
  ```bash
  export GEMINI_API_KEY="AIzaSy..."      # Google Gemini 2.5 Pro
  export ANTHROPIC_API_KEY="sk-ant-..."  # Anthropic Claude 3.5 Sonnet
  export OPENAI_API_KEY="sk-proj-..."    # OpenAI GPT-4o
  ```
  Apex dispatches to all three foundational models simultaneously. Gemini drafts the architecture, Claude generates defensive implementations, and GPT-4o synthesizes adversarial unit tests.
* **Zero External Dependencies (`pip = 0`):** Apex implements custom HTTP/JSON streaming adapters over standard library `urllib.request`. You do **not** need to install `openai`, `anthropic`, or `google-generativeai`.
* **Instant Offline Simulator:** If no API keys are provided (or if `--offline` is passed), Apex automatically falls back to an offline simulated engine. You can clone the repo and run full council debates and verification workflows immediately with zero tokens or internet access.

---

## 🔬 Claims vs. Reality: Engineering Transparency

To ensure absolute credibility with engineers, here is what Apex does and does not do:

* **What CEGIS is:** Counterexample-Guided Inductive Synthesis (Solar-Lezama 2008 & Gulwani 2011). Apex mutates AST candidate operations and systematically evaluates them against hostile test oracles and boundary inputs. It is **bounded inductive program repair**, not an SMT/Z3 theorem prover or Coq proof assistant.
* **What Ochiai SBFL is:** Spectrum-Based Fault Localization. It instruments code execution using Python's tracing subsystem (`sys.settrace`), computes passing vs. failing test coverage, and mathematically ranks suspicious lines using the Ochiai formula.
* **What the Consensus Engine does:** Models critique and score each other's ASTs against CWE security rules, typing invariants, and runtime execution latency. A composite score determines the winning candidate or synthesizes an agreed hybrid patch.

---

## 🚦 Transparent Feature Status & Tested CLI Commands

All commands below are verified and runnable out-of-the-box with the standalone single executable [`dist/apex.pyz`](dist/apex.pyz):

| Subsystem | Maturity | Status & Verification | Runnable CLI Command |
| :--- | :---: | :--- | :--- |
| **MCTS Consensus** | `Stable` | Multi-agent solution search with branch pruning. | `python dist/apex.pyz "Build thread-safe LRU Cache" --offline` |
| **CEGIS Program Repair** | `Stable` | Bounded counterexample search repairing AST operators. | `python dist/apex.pyz cegis examples/calculator.py --tests "assert add(2, 3) == 5"` |
| **Ochiai Bug Localizer** | `Stable` | Statistical coverage ranking locating line numbers of failures. | `python dist/apex.pyz localize examples/calculator.py --tests "assert add(2, 3) == 5"` |
| **Unified SBFL Triad** | `Stable` | Ensemble localization combining Ochiai, Tarantula, and D*. | `python dist/apex.pyz sbfl examples/calculator.py --tests "assert add(2, 3) == 5"` |
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

# Run the complete test suite (241 tests, ~36s)
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
Ran 241 tests in 36.527s
OK
```

* **184 Platform Baseline Tests:** MCTS search, CEGIS invariant synthesizer, Ochiai SBFL, Hoare logic, AST mutation fuzzing, DLP sanitization, RBAC, and Git plumbing.
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
docker build -f packaging/Dockerfile -t apex-sovereign .

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
