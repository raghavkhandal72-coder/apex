# Contributing to Apex-Council

Thank you for your interest in contributing to **Apex-Council**! We are building the sovereign multi-model consensus and autonomous engineering platform for the next decade of software development.

---

## 🛠️ Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/apex-council.git
   cd apex-council
   ```

2. **Verify Python Environment (>= 3.9):**
   ```bash
   python --version
   ```

3. **Install Editable Package:**
   ```bash
   pip install -e .
   ```

4. **Run the Full Test Suite:**
   ```bash
   python -m unittest discover -s tests
   ```

---

## 🏗️ Architecture Guide

* `apex_council/engine.py`: Core council orchestrator handling parallel dispatch, cross-examination, and synthesis.
* `apex_council/providers/`: Model provider adapters (Gemini, Claude, OpenAI, and local simulation).
* `apex_council/engineer/`: Full-repo autonomous scaffolding and bug hunting engine.
* `apex_council/enterprise/`: DLP PII sanitizer, SOC2 cryptographic audit trail, and RBAC policies.
* `apex_council/evaluator/`: AST security analyzer, sandbox runtime executor, red-team fuzzer, and SWE benchmarks.
* `apex_council/mcp_server.py`: Model Context Protocol JSON-RPC 2.0 stdio engine for Claude Desktop & Cursor.
* `apex_council/web/`: Lightweight zero-dependency Cyberpunk Web Studio.

---

## 🔌 Adding a New Model Provider

To add a new LLM provider (e.g., DeepSeek, Mistral, Llama 3):
1. Subclass `BaseLLMProvider` in `apex_council/providers/base.py`.
2. Implement `generate(prompt: str) -> CodeSubmission`.
3. Implement `critique(target_provider: ModelProvider, target_code: str, prompt: str) -> Critique`.
4. Register the new provider enum in `apex_council/models.py` and factory in `factory.py`.
5. Add unit tests in `tests/`.

---

## 📋 Pull Request Checklist

Before opening a PR, ensure:
- [ ] All unit tests pass: `python -m unittest discover -s tests`
- [ ] No hardcoded secrets or PII are committed.
- [ ] Pre-commit git diff audit passes: `python -m apex_council diff`
- [ ] Documentation and README are updated for new flags or commands.
