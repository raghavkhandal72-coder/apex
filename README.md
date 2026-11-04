# 🏛️ Apex-Council: The Multi-LLM Code Supreme Court

> **Stop choosing between models. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-examine their code, auto-verify security & runtime performance, and synthesize the ultimate flaw-free implementation.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Server](https://img.shields.io/badge/MCP-Standard%20Protocol-purple.svg)]()
[![Web Dashboard](https://img.shields.io/badge/Web%20Studio-Included-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-7%20passing-brightgreen.svg)]()

---

## ⚡ Why Apex-Council?

Frontier AI providers constantly debate who writes the best code:
* **Google Gemini** dominates in massive context reasoning, multimodal ingestion, and raw latency.
* **Anthropic Claude** is praised for defensive architectural design and boundary safety.
* **OpenAI (GPT-4o / o1)** excels at concise algorithmic logic and strict formatting.

Yet in production, **isolated models make critical mistakes**—leaving open command injections (CWE-78), path traversals (CWE-22), or race conditions.

**Apex-Council** eliminates single-model blindspots by convening an autonomous **Multi-Model Supreme Council**:
1. ⚔️ **Head-to-Head Arena:** Dispatches prompts simultaneously to Gemini, Claude, and OpenAI.
2. 🔍 **Cross-Critique Matrix:** Each model acts as an adversarial peer reviewer auditing rivals' code.
3. 🛡️ **Automated Verification Gate:** AST security analysis, sandboxed subprocess runtime execution, and hostile red-team fuzzing.
4. ✨ **Consensus Synthesizer:** Merges the winning architecture with peer-reviewed patches to produce flaw-free production code.
5. 🔌 **Model Context Protocol (MCP) Server:** Plug Apex-Council directly into **Claude Code, Cursor, Windsurf, or Claude Desktop**.
6. 🌿 **Pre-Commit Git Diff Review:** Automatically audits your uncommitted working tree before you push.
7. 🏆 **SWE Benchmark Tournament:** Built-in 5-challenge leaderboard testing concurrency, cryptography, memory safety, and distributed locks.

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

## 💻 CLI Command Suite

| Command | Description |
| :--- | :--- |
| `apex-council "prompt"` | Run head-to-head battle across Gemini, Claude, and OpenAI |
| `apex-council diff` | Audit uncommitted local Git diff for security regressions |
| `apex-council redteam <file>` | Fuzz and stress-test code with hostile injection payloads |
| `apex-council benchmark` | Run the 5-Challenge SWE Tournament and show the Leaderboard |
| `apex-council audit <file>` | Audit, benchmark, and auto-refactor an existing codebase file |
| `apex-council relay "task"` | Run Collaborative Pipeline: Gemini (Arch) ➔ Claude (Code) ➔ OpenAI (Tests) |
| `apex-council serve` | Launch the local Cyberpunk dark-mode Web Dashboard |
| `apex-council mcp` | Start standard Model Context Protocol (stdio) server |
| `apex-council init-ci` | Generate GitHub Actions PR review workflow |

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

## 🏆 SWE Benchmark Leaderboard

Run the tournament on your own machine:

```bash
python -m apex_council benchmark
```

```text
==========================================================================
   🏆 APEX-COUNCIL SWE BENCHMARK LEADERBOARD (5 Production Challenges)   
==========================================================================
Rank  | Model Provider         | Wins   | Avg Score    | Security   | Latency
--------------------------------------------------------------------------
🥇 1st | Google Gemini          | 5      | 97.2         | 100.0%     | 170.1 ms
🥈 2nd | Anthropic Claude       | 0      | 97.2         | 100.0%     | 182.1 ms
🥉 3rd | OpenAI / Microsoft     | 0      | 97.2         | 100.0%     | 111.3 ms
--------------------------------------------------------------------------
```

---

## 🌿 Pre-Commit Git Diff Review

Prevent bad code and security holes from ever reaching GitHub:

```bash
# Audit working changes before commit
python -m apex_council diff

# Audit only staged changes
python -m apex_council diff --staged
```

---

## ⚔️ Adversarial Red-Team Fuzzing

Subject your code to hostile adversarial attack vectors (Null bytes, command chaining, path traversal, memory bloat):

```bash
python -m apex_council redteam src/auth_service.py
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
