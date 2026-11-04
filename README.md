# 🏛️ Apex-Council: The Multi-LLM Code Supreme Court

> **Stop choosing between models. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-examine their code, auto-verify security & runtime performance, and synthesize the ultimate flaw-free implementation.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Council Members](https://img.shields.io/badge/Council-Gemini%20%7C%20Claude%20%7C%20OpenAI-purple.svg)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

---

## ⚡ The Big Idea

Every frontier AI provider claims to be the "best coding model":
* **Anthropic Claude** is praised for architectural elegance and defensive style.
* **Google Gemini** dominates with massive context reasoning, multimodal ingestion, and blazing speed.
* **OpenAI (GPT-4o / o1)** provides battle-tested algorithmic logic and strict formatting.

Yet in reality, **individual models still make mistakes**—leaving open command injection, subtle race conditions, or unhandled edge cases.

**Apex-Council** eliminates this by convening an autonomous **Multi-Model Supreme Council**:
1. **Parallel Dispatch:** Dispatches your coding challenge simultaneously to Google Gemini, Anthropic Claude, and OpenAI.
2. **The Cross-Critique Matrix (Peer Review):** Each model audits the others' code to expose security flaws, hallucinated libraries, and performance bottlenecks.
3. **Automated Verification Gate:** Runs AST security scanning (CWE-78, CWE-22, CWE-798) and sandbox execution tests with millisecond timing.
4. **The Synthesizer:** Merges the winning architecture with peer-reviewed patches to produce the **Consensus Code**—verifiably superior to any single model's isolated output.

---

## 🔄 How It Works

```
                                [Your Coding Prompt]
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 ▼                       ▼                       ▼
         [Google Gemini]         [Anthropic Claude]      [OpenAI / Microsoft]
                 │                       │                       │
                 └───────────────┬───────┴───────┬───────────────┘
                                 │               │
                                 ▼               ▼
                     [Peer Review Cross-Critique Matrix]
                      (Each model audits rivals' code)
                                         │
                                         ▼
                     [AST Security & Isolated Sandbox Tests]
                     (CWE Checks, Runtime Latency, Unit Tests)
                                         │
                                         ▼
                     [Supreme Verdict & Flaw-Free Consensus]
```

---

## 🚀 Quick Start

### 1. Clone & Run Instantly

Zero external dependencies required out-of-the-box:

```bash
git clone https://github.com/your-username/apex-council.git
cd apex-council
python -m apex_council "Build a thread-safe LRU Cache with TTL"
```

### 2. Optional: Plug in Live API Keys

Whenever environment keys are set, Apex-Council automatically upgrades from simulation to live cloud model execution:

```bash
export GEMINI_API_KEY="your-gemini-key"
export ANTHROPIC_API_KEY="your-claude-key"
export OPENAI_API_KEY="your-openai-key"

python -m apex_council "Write an authenticated FastAPI rate-limiter"
```

---

## 💻 CLI Usage

### Live Interactive Arena

```bash
python -m apex_council "Design a concurrent distributed lock using Redis"
```

### Output Formats

```bash
# Pretty terminal output with ANSI colors (default)
python -m apex_council "Write a secure file upload handler"

# Export Markdown summary for GitHub pull requests
python -m apex_council "Refactor auth middleware" --format markdown -o council_verdict.md

# Output JSON for CI/CD automation pipelines
python -m apex_council "Generate SQL migration" --format json
```

---

## 📊 Sample Head-to-Head Scoreboard

```text
========================================================================
   APEX-COUNCIL: THE MULTI-LLM CODE SUPREME COURT   
   Google Gemini  ×  Anthropic Claude  ×  OpenAI / Microsoft
========================================================================

🎯 Task Prompt: "Build a secure thread-safe cache with TTL"

📊 HEAD-TO-HEAD SCOREBOARD
---------------------------------------------------------------------------
Model Provider         | Security   | Peer Review  | Runtime    | Overall Score
---------------------------------------------------------------------------
Google Gemini          | 100%       | 9.2 / 10     | 42.1 ms    | 97.2 / 100
Anthropic Claude       | 100%       | 9.2 / 10     | 48.3 ms    | 97.2 / 100
OpenAI / Microsoft     | 100%       | 9.0 / 10     | 51.0 ms    | 96.5 / 100
---------------------------------------------------------------------------

🏆 COUNCIL VERDICT & WINNER: Google Gemini
  Google Gemini earned the highest composite score based on automated security
  auditing (100%), runtime verification (42.1ms), and cross-model consensus.
```

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
