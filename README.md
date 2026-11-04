# 🏛️ Apex-Council: Enterprise Autonomous Multi-LLM Software Engineering & Consensus Platform

> **The Sovereign Multi-Model Platform for Enterprise AI Engineering. Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, enforce SOC2 cryptographic audit trails, run zero-leakage DLP sanitization, and autonomously engineer production-grade software.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Security Hardening](https://img.shields.io/badge/Sandbox-Hermetic%20Isolated-red.svg)]()
[![Code Integrity](https://img.shields.io/badge/Signatures-HMAC--SHA512%20Attested-purple.svg)]()
[![SOC2 Audit](https://img.shields.io/badge/SOC2-Cryptographically%20Chained-success.svg)]()
[![Enterprise DLP](https://img.shields.io/badge/DLP-Zero--Leakage%20Sanitizer-blue.svg)]()
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Production%20Manifests-326CE5.svg)]()
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics%20Ready-E6522C.svg)]()
[![Tests](https://img.shields.io/badge/tests-19%20passing-brightgreen.svg)]()

---

## 🏢 Why Big Tech & Fortune 500 Enterprises Adopt Apex-Council

Enterprises like **Google, Microsoft, Netflix, Stripe, and Meta** cannot deploy single-model AI assistants blindly into production due to three critical enterprise liabilities:
1. **Model Bias & Single-Point-of-Failure:** Relying on one vendor creates vendor lock-in and leaves severe hallucination & security blindspots.
2. **Data Leakage & PII Exposure (GDPR / HIPAA):** Employees accidentally paste internal customer emails, credit cards, or private API keys into LLM prompts.
3. **Auditability & Legal Governance (SOC2 / ISO 27001):** Regulators require an immutable, tamper-evident cryptographic log of every AI action, model contribution, and code deployment.

**Apex-Council** resolves all three enterprise barriers with an all-in-one architecture:
* 🛡️ **Enterprise Data Loss Prevention (DLP):** Automatically redacts emails, SSNs, credit cards, JWTs, and private keys *before* prompts reach any model.
* 🔒 **Hermetic Subprocess Sandbox:** All code execution runs in an isolated, scrubbed environment with zero parent credentials or SSH keys exposed.
* 🔏 **HMAC-SHA512 Code Integrity Signing:** All synthesized consensus code is cryptographically signed with constant-time verification against tampering.
* 🏰 **Zero-Trust Filesystem Chroot Jail:** Defeats path traversal, symlink escapes, null bytes, and NTFS Alternate Data Streams (ADS).
* 🛡️ **AST Bomb & Recursion Shield:** Prevents parser overflows, DoS attacks, and deeply nested syntax explosion exploits.
* 📜 **Cryptographically Chained Audit Trail (SHA-256):** Every single generation and code fix is chained like a blockchain block, guaranteeing non-repudiation.
* 🔐 **Multi-Tenant Role-Based Access Control (RBAC):** Scoped permissions for `ADMIN`, `SECURITY_LEAD`, `DEVELOPER`, and `AUDITOR`.
* ⚖️ **Enterprise Governance Policy Engine:** Blocks viral licenses (AGPL/GPL) and prohibited insecure modules (pickle, telnetlib, pycrypto).
* 📈 **OpenMetrics & Prometheus Observability:** Live `/metrics` endpoint exporting request rates, model win ratios, and security mitigations.
* ☸️ **Kubernetes (K8s) Production Deployment:** Includes battle-tested `k8s/deployment.yaml`, `k8s/service.yaml`, and `k8s/configmap.yaml`.

---

## 🔄 Enterprise Architecture

```
                                [Enterprise Developer / CI Pipeline]
                                                  │
                                                  ▼
                                     [Enterprise RBAC Gateway]
                                                  │
                                                  ▼
                                 [Enterprise DLP Sanitizer]
                           (Redacts SSNs, Cards, JWTs, Keys)
                                                  │
                         ┌────────────────────────┼────────────────────────┐
                         ▼                        ▼                        ▼
                 [Google Gemini]          [Anthropic Claude]       [OpenAI / Microsoft]
                         │                        │                        │
                         └────────────────┬───────┴────────┬───────────────┘
                                          │                │
                                          ▼                ▼
                             [Peer-Review Cross-Critique Matrix]
                                          │
                                          ▼
                             [AST Security & Red-Team Fuzzing]
                                          │
                                          ▼
                             [Enterprise Policy Enforcement]
                             (Licenses, Banned Libs, Typing)
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
           [Flaw-Free Consensus Code]       [SOC2 SHA-256 Audit Chain]
                                             (Immutable /metrics Stream)
```

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
python -m apex_council engineer "Build a concurrent distributed lock manager with TTL heartbeat" -o ./dist_lock
```

---

## 💻 Enterprise CLI Command Suite

| Command | Category | Description |
| :--- | :--- | :--- |
| `apex-council engineer <spec> -o <dir>` | **AI Engineer** | Deconstruct spec, build multi-file codebase, write tests, & git commit |
| `apex-council solve <issue> [--repo <dir>]` | **AI Engineer** | Localize bug across files & apply verified patch |
| `apex-council heal <file>` | **Self-Healing** | Autonomous Closed-Loop Code Repair (Tests ➔ Traceback ➔ Fix ➔ Re-test) |
| `apex-council pr <url|repo#pr>` | **GitHub Bot** | Live GitHub PR Review with line-by-line comments & patch |
| `apex-council dlp-test "<text>"` | **Enterprise** | Test DLP sanitization of customer PII, credit cards, and tokens |
| `apex-council audit-verify` | **Compliance** | Verify cryptographic SHA-256 integrity of SOC2 / ISO 27001 audit trail |
| `apex-council policy-check <file>` | **Compliance** | Audit code against Enterprise Licensing and Prohibited Library policies |
| `apex-council diff` | **Security** | Pre-commit audit of uncommitted local Git diff |
| `apex-council redteam <file>` | **Security** | Fuzz and stress-test code with hostile injection attack vectors |
| `apex-council benchmark` | **Evaluation** | Run 5-Challenge SWE Tournament and output the Olympic Leaderboard |
| `apex-council serve` | **Web Studio** | Launch local Cyberpunk Dark-Mode Web Studio & Prometheus `/metrics` |
| `apex-council mcp` | **Protocol** | Start standard Model Context Protocol (stdio) server |

---

## 🛡️ Enterprise DLP & PII Sanitizer

Never leak customer data or corporate keys to cloud models:

```bash
python -m apex_council dlp-test "Process payment for user john.doe@enterprise.com with card 4111111111111111 and token api_key='secret-corp-key-999'"
```

**Output:**
```text
Redactions Made: 3
Categories Found: ['EMAIL', 'CREDIT_CARD', 'API_KEY_GENERIC']
Sanitized Text:   Process payment for user [REDACTED_EMAIL] with card [REDACTED_CREDIT_CARD] and token api_key='[REDACTED_SECRET]'
```

---

## 📜 SOC2 / ISO 27001 Cryptographic Audit Trail

Every code generation and review event is cryptographically linked via SHA-256 Merkle chaining:

```bash
# Verify log integrity (detects any tampering or unauthorized edits)
python -m apex_council audit-verify --log audit_trail.jsonl
```

```text
✓ AUDIT TRAIL VERIFIED: All 128 cryptographic hash chains are intact and tamper-free.
```

---

## 📈 Prometheus & OpenMetrics Telemetry

Apex-Council natively exposes `/metrics` for enterprise Datadog, Prometheus, Grafana, and New Relic dashboards:

```text
# HELP apex_council_requests_total Total number of Council operations processed
# TYPE apex_council_requests_total counter
apex_council_requests_total{action="deliberate"} 1420
apex_council_requests_total{action="engineer"} 380

# HELP apex_council_model_wins_total Total Council consensus wins by model provider
# TYPE apex_council_model_wins_total counter
apex_council_model_wins_total{model="Google Gemini"} 890
apex_council_model_wins_total{model="Anthropic Claude"} 520
apex_council_model_wins_total{model="OpenAI / Microsoft"} 390
```

---

## 🔒 Military-Grade Defense Hardening

Apex-Council enforces defense-in-depth security to ensure that no untrusted code, malicious prompt injection, or parser exploit can breach the runtime environment:

* **Hermetic Sandbox Execution:** Isolates child processes with stripped environments. Denies child processes any access to parent AWS/GCP/Azure tokens, SSH keys, or shell secrets.
* **HMAC-SHA512 Sovereign Code Attestation:** Emits `# APEX-SIG-SHA512:` cryptographic signatures on generated files. The system rejects execution if even a single byte has been modified out-of-band.
* **Zero-Trust Filesystem Chroot Jail:** Restricts all file reads and writes within strict root bounds. Automatically rejects path traversals (`../../`), symlink escapes, null-byte poisoning (`\x00`), and Windows NTFS Alternate Data Streams (`::$DATA`).
* **AST Bomb & Recursion Shield:** Inspects incoming code before parsing. Flags parser-exploding depth attacks, excessive AST node floods (>50,000 nodes), and nested bracket exhaustion before execution occurs.

---

## ☸️ Enterprise Kubernetes (K8s) Deployment

Deploy to your corporate Kubernetes cluster in seconds:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
