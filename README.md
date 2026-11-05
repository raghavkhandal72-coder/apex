# 🏛️ Apex: Autonomous Multi-Agent Consensus & Formal Verification Engine

> **Stop blindly trusting single-model AI code. Apex pits multiple AI models against each other using Monte Carlo Tree Search (MCTS) and proves edge-case safety using Counterexample-Guided Inductive Synthesis (CEGIS)—synthesizing mathematically verified software in 100% Pure Python Standard Library (`pip = 0`).**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20external%20pip-brightgreen.svg)]()
[![Tests Passing](https://img.shields.io/badge/tests-241%20passing%20(100%25)-success.svg)]()
[![Single Executable](https://img.shields.io/badge/distribution-372KB%20standalone%20.pyz-orange.svg)]()

---

## ⚡ The 10-Second Pitch

Single LLM coding assistants suffer from hallucinations, brittle edge cases, and silent security vulnerabilities. 

**Apex** solves this by treating code generation as a formal verification problem:
1. **Multi-Model Consensus:** Deconstructs user requirements across specialized agent personas (Commander, Architect, Sentinel, Ninja).
2. **MCTS Test-Time Compute:** Explores alternative implementation paths using Monte Carlo Tree Search with Upper Confidence Bounds (PUCT).
3. **CEGIS Formal Prover:** Actively generates hostile counterexamples to falsify proposed invariants before code lands.
4. **Zero-Dependency Guarantee:** The entire platform—including search, AST parsing, cryptography, web scraping, and container supervision—runs on the **Python standard library alone**. Zero `pip install` required.

---

## 🚦 Transparent Feature Status & Benchmarks

To maintain strict engineering rigor, every subsystem in Apex is explicitly categorized by maturity level:

| Subsystem | Maturity | Status & Verification | CLI Demo |
| :--- | :---: | :--- | :--- |
| **MCTS Consensus** | `Stable` | Explores multi-agent solution paths with branch pruning. | `apex "Build thread-safe LRU Cache"` |
| **CEGIS Formal Prover** | `Stable` | Generates edge counterexamples to synthesize safety invariants. | `apex cegis --spec "forall x: x >= 0"` |
| **Ochiai Bug Localizer (SBFL)** | `Stable` | Statistical ranking locating exact line numbers of test failures. | `apex localize tests/test_calc.py` |
| **REA Reverse Engineering** | `Stable` | Disassembles Python bytecode and parses ELF/PE/ZIP headers. | `apex rea --disasm myfile.py` |
| **Diff Reviewdog** | `Stable` | Multi-format diagnostic parser filtered strictly against git diffs. | `apex reviewdog error.log --git` |
| **Streaming Telemetry (Netdata)** | `Stable` | Pure Python streaming wire protocol for system & process metrics. | `apex netdata --stream` |
| **Startup Review Suite (gstack)** | `Stable` | Pre-landing review gate, CSO threat audit, and SemVer release ship. | `apex gstack review --diff patch.diff` |
| **GBrain Persistent Memory** | `Stable` | Sub-millisecond SQLite persistent memory with cross-session locks. | `apex gbrain recall "architecture"` |
| **Scrapling DOM Engine** | `Stable` | Anti-detection HTML-to-Markdown parser and table extractor. | `apex scrape "https://news.ycombinator.com"` |
| **Transformer Engine** | `Experimental` | Pure Python decoder-only model with RoPE, GQA, RMSNorm, SwiGLU. | `apex transformer train --data corpus.txt` |
| **Local Cloud Mock (Floci)** | `Beta` | Zero-cost local S3, SQS, and DynamoDB emulator with persistence. | `apex floci s3 list demo-bucket` |
| **Agent Browser & Electron** | `Beta` | Accessible element tree snapshotting and desktop shell bridge. | `apex browser snapshot "https://example.com"` |

---

## 🔬 Proof & Concrete Demos

### 1. Counterexample-Guided Inductive Synthesis (CEGIS)
Apex checks invariant boundaries by pitting a **Synthesizer** against a hostile **Verifier**:

```python
from apex_council.formal.cegis import CEGISEngine

# Define specification boundary
engine = CEGISEngine()
result = engine.synthesize_boundary(
    invariant="x > 0 ==> f(x) > x",
    initial_hypothesis="f(x) = x + 1"
)
print(f"Verified Invariant: {result.formula} (Counterexamples checked: {result.counterexamples_checked})")
```

### 2. Spectrum-Based Fault Localization (Ochiai SBFL)
When tests fail, Apex instruments execution profiles to rank the suspicion score of every executed line:

$$\text{Ochiai}(s) = \frac{\text{failed}(s)}{\sqrt{\text{total\_failed} \times (\text{failed}(s) + \text{passed}(s))}}$$

```bash
apex localize tests/test_calculator.py
# Output:
# [TOP SUSPECT] line 42 (calculator.py) — Suspicion Score: 0.9487
# Fix Recommendation: Replace off-by-one `<=` with `<`
```

### 3. Cryptographic Evidence Ledger (REA)
When auditing or reverse-engineering suspicious binaries or bytecode, Apex commits findings to an immutable SHA-256 evidence chain:

```bash
apex rea suspicious_module.py --disasm --evidence --claim "Disallow os.system in runtime"
# Output:
# [EVIDENCE COMMITTED] ev_3f8a4c102b (SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855)
```

---

## 🚀 Quick Start

### Option A: Portable Standalone Executable (No Installation)
Download or build the standalone single-file archive (372 KB):

```bash
# Direct execution via standard Python 3.10+
python dist/apex.pyz --help

# Convene multi-model council for a task
python dist/apex.pyz "Design a lock-free concurrent ring buffer"
```

### Option B: Local Repository Installation
```bash
git clone https://github.com/your-username/apex-council.git
cd apex-council

# Optional: Run one-line installer
./scripts/install.sh       # Linux / macOS
.\scripts\install.ps1      # Windows PowerShell

# Run the complete test suite
python -m unittest discover -s tests
```

---

## 🧪 Verification & Test Suite Transparency

Apex maintains an absolute regression-free policy. Every feature commit is verified by automated opaque-box and unit tests:

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

Apex is distributed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) for details.
