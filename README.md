# 🏛️ Apex-Council: The Multi-LLM Code Supreme Court

> **Stop choosing between models. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-examine their code, auto-verify security & runtime performance, and synthesize the ultimate flaw-free implementation.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Self-Healing](https://img.shields.io/badge/Self--Healing-Closed--Loop%20Repair-blue.svg)]()
[![MCP Server](https://img.shields.io/badge/MCP-Standard%20Protocol-purple.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)]()
[![Tests](https://img.shields.io/badge/tests-9%20passing-brightgreen.svg)]()

---

## ⚡ Why Apex-Council?

Frontier AI providers constantly debate who writes the best code:
* **Google Gemini** dominates in massive context reasoning, multimodal ingestion, and raw latency.
* **Anthropic Claude** is revered for defensive architectural design and boundary safety.
* **OpenAI (GPT-4o / o1)** excels at concise algorithmic logic and strict formatting.

Yet in production, **isolated models make critical mistakes**—leaving open command injections (CWE-78), path traversals (CWE-22), or race conditions.

**Apex-Council** eliminates single-model blindspots by convening an autonomous **Multi-Model Supreme Council**:
1. ⚔️ **Head-to-Head Arena:** Dispatches prompts simultaneously to Gemini, Claude, and OpenAI.
2. 🔍 **Cross-Critique Matrix:** Each model acts as an adversarial peer reviewer auditing rivals' code.
3. 🛡️ **Automated Verification Gate:** AST security analysis, sandboxed subprocess runtime execution, and hostile red-team fuzzing.
4. ✨ **Consensus Synthesizer:** Merges the winning architecture with peer-reviewed patches to produce flaw-free production code.
5. 🩺 **Autonomous Closed-Loop Self-Healing:** Catches runtime tracebacks and compiler errors, auto-repairs code on disk, and iterates until 100% green.
6. 🐙 **Live GitHub PR Reviews:** Pull and review any public/private Pull Request with one command (`apex-council pr owner/repo#123`).
7. 🔌 **Model Context Protocol (MCP) Server:** Plug Apex-Council directly into **Claude Code, Cursor, Windsurf, or Claude Desktop**.
8. 🌿 **Pre-Commit Git Diff Review:** Automatically audits your uncommitted working tree before you push.
9. 🏆 **SWE Benchmark Tournament:** Built-in 5-challenge leaderboard testing concurrency, cryptography, memory safety, and distributed locks.
10. 🌐 **Polyglot & Container-Ready:** Works across Python, TypeScript, Go, Rust, and ships with zero-config `Dockerfile` and `docker-compose.yml`.

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

Whenever environment keys are set, Apex-Council automatically connects to live official REST endpoints (via native zero-dependency HTTP):

```bash
export GEMINI_API_KEY="your-gemini-key"
export ANTHROPIC_API_KEY="your-claude-key"
export OPENAI_API_KEY="your-openai-key"

python -m apex_council "Write an authenticated FastAPI rate-limiter"
```

---

## 💻 Flagship CLI Command Suite

| Command | Description |
| :--- | :--- |
| `apex-council "prompt"` | Run head-to-head battle across Gemini, Claude, and OpenAI |
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

## 🩺 Autonomous Closed-Loop Self-Healing

Point Apex-Council at any broken code file:

```bash
python -m apex_council heal src/broken_service.py --tests "python -m unittest test_service.py"
```

The Supreme Council will:
1. Capture the exact traceback / compiler error.
2. Convene Gemini, Claude, and OpenAI with the error context.
3. Apply candidate fixes in an isolated sandbox.
4. Re-run tests iteratively until 100% test pass rate and clean security score are achieved.
5. Overwrite the healed file atomically with zero data loss!

---

## 🐙 Live GitHub Pull Request Reviewer

Review any open Pull Request directly from your terminal:

```bash
# Via GitHub URL
python -m apex_council pr https://github.com/pallets/flask/pull/5000

# Or via shorthand
python -m apex_council pr django/django#17000
```

---

## 🔌 Model Context Protocol (MCP) Integration

Apex-Council can be used directly inside **Claude Desktop**, **Cursor**, or **Claude Code** as an official tool!

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

Now inside Claude or Cursor, simply ask:
> *"Ask Apex Council to debate and write a thread-safe event bus."*

---

## 🐳 Docker Deployment

Run the complete Council studio with Docker in one command:

```bash
docker-compose up --build
# Open http://localhost:8080
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
