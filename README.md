# 🏛️ Apex-Council: The Multi-LLM Code Supreme Court

> **Stop choosing between models. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-examine their code, auto-verify security & runtime performance, and synthesize the ultimate flaw-free implementation.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Council Members](https://img.shields.io/badge/Council-Gemini%20%7C%20Claude%20%7C%20OpenAI-purple.svg)]()
[![Web Dashboard](https://img.shields.io/badge/Web%20UI-Included-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-7%20passing-brightgreen.svg)]()

---

## ⚡ The Big Idea

Frontier AI providers constantly debate who has the best coding model:
* **Google Gemini** dominates in massive context windows, multimodal reasoning, and speed.
* **Anthropic Claude** is revered for defensive architectural design and boundary rigor.
* **OpenAI (GPT-4o / o1)** provides concise algorithmic logic and strict formatting.

Yet in reality, **no single model is immune to flaws**: isolated models leave open subtle command injections, path traversals, or unhandled edge cases.

**Apex-Council** solves this by convening an autonomous **Multi-Model Supreme Council**:
1. ⚔️ **Competitive Battle Mode:** Dispatches prompts simultaneously to Gemini, Claude, and OpenAI.
2. 🔍 **Cross-Critique Matrix (Peer Review):** Each model audits its rivals' code, exposing hallucinations, security bugs, and performance bottlenecks.
3. 🛡️ **Automated Verification Gate:** Runs AST security scanning (CWE-78, CWE-22, CWE-798) and sandbox execution tests with millisecond timing.
4. ✨ **Consensus Synthesizer:** Merges the winning architecture with peer-reviewed patches to produce the **Consensus Code**—verifiably superior to any single model's isolated output.
5. 🤝 **Collaborative Relay Pipeline:** Gemini (Architect) ➔ Claude (Defensive Code) ➔ OpenAI (Unit Tests).
6. 🌐 **Built-in Web Dashboard:** Futuristic dark-mode UI with live model scorecards and real-time deliberation.

---

## 🚀 Quick Start

### 1. Instant Run (Zero Dependencies)

```bash
git clone https://github.com/your-username/apex-council.git
cd apex-council

# Run head-to-head battle
python -m apex_council "Build a thread-safe LRU Cache with TTL"
```

### 2. Optional: Connect Live Cloud Models

Whenever environment keys are set, Apex-Council automatically queries live endpoints via native zero-dependency HTTP:

```bash
export GEMINI_API_KEY="your-gemini-key"
export ANTHROPIC_API_KEY="your-claude-key"
export OPENAI_API_KEY="your-openai-key"

python -m apex_council "Write an authenticated FastAPI rate-limiter"
```

---

## 💻 CLI Commands

### 1. Head-to-Head Battle Arena
```bash
python -m apex_council battle "Design a concurrent distributed lock using Redis"
```

### 2. File Audit Mode
Have the Supreme Council audit, benchmark, and refactor any existing file:
```bash
python -m apex_council audit ./src/auth.py
```

### 3. Collaborative Relay Pipeline
Let Gemini design the architecture, Claude write the defensive code, and OpenAI generate unit tests:
```bash
python -m apex_council relay "Build an event bus in Python" -o event_bus.py
```

### 4. Interactive Web Dashboard
Launch the local dark-mode developer studio:
```bash
python -m apex_council serve --port 8080
# Visit http://127.0.0.1:8080
```

### 5. Automated CI/CD Generator
Generate automated GitHub Actions PR review gating:
```bash
python -m apex_council init-ci
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
