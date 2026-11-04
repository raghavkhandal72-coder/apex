# 🏛️ Apex-Council: The Multi-LLM Autonomous Software Engineer & Supreme Court

> **Stop choosing between models. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-examine their code, auto-verify security & runtime performance, synthesize flaw-free implementations, or let the Council autonomously engineer entire repositories from scratch.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Autonomous Engineer](https://img.shields.io/badge/AI--Engineer-Devin%20Level-orange.svg)]()
[![Self-Healing](https://img.shields.io/badge/Self--Healing-Closed--Loop%20Repair-blue.svg)]()
[![MCP Server](https://img.shields.io/badge/MCP-Standard%20Protocol-purple.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)]()
[![Tests](https://img.shields.io/badge/tests-10%20passing-brightgreen.svg)]()

---

## ⚡ Why Apex-Council?

Frontier AI providers constantly debate who writes the best code:
* **Google Gemini** dominates in massive context reasoning, multimodal ingestion, and raw latency.
* **Anthropic Claude** is revered for defensive architectural design and boundary safety.
* **OpenAI (GPT-4o / o1)** excels at concise algorithmic logic and strict formatting.

Yet in production, **isolated models make critical mistakes**—leaving open command injections (CWE-78), path traversals (CWE-22), or race conditions.

**Apex-Council** eliminates single-model blindspots by convening an autonomous **Multi-Model Supreme Council & Autonomous Engineering System**:
1. 🤖 **Autonomous AI Software Engineer (`apex-council engineer`):** Give it a natural language spec, and it deconstructs architecture, generates multi-file codebases, writes test suites, executes verification in a sandbox, self-heals bugs, and initializes Git commits autonomously.
2. 🔍 **Autonomous Issue Resolver (`apex-council solve`):** Localizes bugs across an existing repository, generates patches, and tests fixes automatically.
3. ⚔️ **Head-to-Head Arena:** Dispatches prompts simultaneously to Gemini, Claude, and OpenAI.
4. 🔍 **Cross-Critique Matrix:** Each model acts as an adversarial peer reviewer auditing rivals' code.
5. 🛡️ **Automated Verification Gate:** AST security analysis, sandboxed subprocess runtime execution, and hostile red-team fuzzing.
6. ✨ **Consensus Synthesizer:** Merges the winning architecture with peer-reviewed patches to produce flaw-free production code.
7. 🩺 **Autonomous Closed-Loop Self-Healing:** Catches runtime tracebacks and compiler errors, auto-repairs code on disk, and iterates until 100% green.
8. 🐙 **Live GitHub PR Reviews:** Pull and review any public/private Pull Request with one command (`apex-council pr owner/repo#123`).
9. 🔌 **Model Context Protocol (MCP) Server:** Plug Apex-Council directly into **Claude Code, Cursor, Windsurf, or Claude Desktop**.
10. 🌿 **Pre-Commit Git Diff Review:** Automatically audits your uncommitted working tree before you push.
11. 🏆 **SWE Benchmark Tournament:** Built-in 5-challenge leaderboard testing concurrency, cryptography, memory safety, and distributed locks.

---

## 🚀 Quick Start

### 1. Instant Run (Zero Dependencies)

```bash
git clone https://github.com/your-username/apex-council.git
cd apex-council

# Run head-to-head battle
python -m apex_council "Build a thread-safe LRU Cache with TTL"
```

### 2. Autonomous Full-Repository Engineering

```bash
# Build an entire multi-file project autonomously with tests and git commit:
python -m apex_council engineer "Build a concurrent distributed lock manager with TTL heartbeat" -o ./dist_lock
```

---

## 💻 Flagship CLI Command Suite

| Command | Description |
| :--- | :--- |
| `apex-council engineer <spec> -o <dir>` | **Autonomous AI Engineer:** Scaffold complete multi-file repo, write tests, & git commit |
| `apex-council solve <issue> [--repo <dir>]` | **Autonomous Bug Hunter:** Localize bug across files & apply verified patch |
| `apex-council heal <file>` | **Autonomous Self-Healing Loop:** Auto-fix compiler & runtime errors on disk |
| `apex-council pr <url|repo#pr>` | **Live GitHub PR Review:** Fetch diff & generate comprehensive review |
| `apex-council diff` | Pre-commit audit of uncommitted local Git diff |
| `apex-council redteam <file>` | Fuzz and stress-test code with hostile injection payloads |
| `apex-council benchmark` | Run the 5-Challenge SWE Tournament and show the Leaderboard |
| `apex-council audit <file>` | Audit, benchmark, and auto-refactor an existing codebase file |
| `apex-council relay "task"` | Run Collaborative Pipeline: Gemini (Arch) ➔ Claude (Code) ➔ OpenAI (Tests) |
| `apex-council serve` | Launch the local Cyberpunk dark-mode Web Dashboard |
| `apex-council mcp` | Start standard Model Context Protocol (stdio) server |
| `apex-council init-ci` | Generate GitHub Actions PR review workflow |

---

## 🤖 Autonomous Full-Repository Engineer

Watch Apex-Council act as a Staff Software Engineer:

```bash
python -m apex_council engineer "Build an asynchronous rate-limited webhook dispatcher with HMAC signatures" -o ./webhook_engine
```

**What happens behind the scenes:**
1. **Google Gemini** designs the system architecture and data models (`core.py`).
2. **Anthropic Claude** implements defensive error handling, type safety, and boundary checks.
3. **OpenAI** writes a self-contained unit and property test suite (`test_core.py`).
4. **The Sandbox Verifier** runs the test suite; if any error occurs, the **Self-Healing Loop** patches it.
5. Generates `README.md`, `.gitignore`, initializes Git repository, and executes the initial commit!

---

## 🩺 Autonomous Closed-Loop Self-Healing

Point Apex-Council at any broken code file:

```bash
python -m apex_council heal src/broken_service.py --tests "python -m unittest test_service.py"
```

---

## 🐙 Live GitHub Pull Request Reviewer

```bash
python -m apex_council pr https://github.com/pallets/flask/pull/5000
```

---

## 🔌 Model Context Protocol (MCP) Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "apex-council": {
      "command": "python",
      "args": ["-m", "apex_council", "mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key",
        "ANTHROPIC_API_KEY": "your-key",
        "OPENAI_API_KEY": "your-key"
      }
    }
  }
}
```

---

## 🐳 Docker Deployment

```bash
docker-compose up --build
# Open http://localhost:8080
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
