from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .engine import CouncilEngine
from .engineer.autonomous_engineer import AutonomousEngineer
from .enterprise.audit import CryptographicAuditLogger
from .enterprise.dlp import EnterpriseDLP
from .enterprise.policy import EnterprisePolicyEngine
from .evaluator.benchmark import format_benchmark_table, run_benchmark_tournament
from .evaluator.git_review import review_git_diff
from .evaluator.github_pr import review_github_pr
from .evaluator.redteam import run_redteam_analysis
from .evaluator.self_healing import SelfHealingLoop
from .autopsy.ochiai import OchiaiFaultLocalizer
from .graph.repo_map import RepoMap
from .mcp_server import ApexCouncilMCPServer
from .memory.matcher import MemoryMatcher
from .memory.vault import MemoryVault
from .polyglot import detect_language, get_language_prompt_guidelines
from .reporter import CouncilReporter
from .security.ledger import CryptographicLedger
from .swarm.coordinator import SwarmCoordinator
from .swarm.solver import AutonomousIssueSolver
from .ui.replay import FlightRecorderReplay, HTMLReportGenerator
from .ui.terminal import CyberpunkTUI
from .web.server import run_server


KNOWN_COMMANDS = {
    "battle", "engineer", "solve", "heal", "pr", "audit", "relay",
    "serve", "mcp", "diff", "redteam", "benchmark", "audit-verify",
    "dlp-test", "policy-check", "init-ci", "repomap", "swarm", "memory",
    "demo", "verify-ledger", "localize", "build-pyz", "swe-bench",
    "autopsy", "synthesize", "verify-proof", "edge",
    "perf", "chaos", "appsec", "db-tune", "modernize", "release", "sbfl", "hoare",
    "cfg", "abstract-interp", "cegis", "solomonoff",
    "oracle", "ast-nav", "memo-sync", "mini-swe",
    "ontology", "sdd", "worktrunk", "executive",
    "wt", "console", "mlflow-trace", "mlflow-eval",
    "omo", "dag", "gstack",
    "gbrain", "scrape", "floci", "voice", "skills", "browser", "electron",
    "rea", "reviewdog", "netdata", "lint", "fix", "hook", "challenge", "null-guard",
    "watch", "slice", "modern", "lsp", "loop",
    "patch-export", "crash-fingerprint", "flamegraph", "pr-summary", "secret-mask", "completion", "zero-div",
    "instruments", "swift-guard", "studio", "test-all", "demo-live", "bench-live", "review", "ollama", "llamafile", "runner", "audit-sec", "security-audit", "scala", "scala-guard", "spark", "spark-guard", "dify", "dify-guard",
    "-h", "--help"
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_args = list(sys.argv[1:] if argv is None else argv)

    # Seamless UX Polish: If first argument is not a known command or flag, treat as direct battle prompt
    if raw_args and not raw_args[0].startswith("-") and raw_args[0] not in KNOWN_COMMANDS:
        raw_args = ["battle"] + raw_args

    parser = argparse.ArgumentParser(
        prog="apex",
        description="🏛️ The Multi-LLM Code Supreme Court: Enterprise AI Engineering & Consensus Platform.",
    )
    parser.add_argument("--version", action="version", version="Apex Sovereign v0.9.0")

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command 1: Battle / Deliberate
    battle_parser = subparsers.add_parser("battle", help="Run head-to-head competition between Gemini, Claude, and OpenAI")
    battle_parser.add_argument("prompt", nargs="?", default="Build an LRU cache with TTL support", help="Coding task prompt")
    battle_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    battle_parser.add_argument("-o", "--output", type=Path, help="Save report to file")
    battle_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")
    battle_parser.add_argument("--strict", action="store_true", help="Fail immediately with non-zero exit code if any live API call fails")
    battle_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose diagnostics (provider endpoints, token telemetry, latency)")

    # Command 2: Autonomous AI Software Engineer
    eng_parser = subparsers.add_parser("engineer", help="Autonomous AI Engineer: Deconstruct spec, build multi-file codebase, write tests, & git commit")
    eng_parser.add_argument("spec", help="Natural language application or feature specification")
    eng_parser.add_argument("-o", "--output", type=Path, required=True, help="Directory to create the engineered project in")
    eng_parser.add_argument("--offline", action="store_true")

    # Command 3: Autonomous Issue Solver / Bug Hunter
    solve_parser = subparsers.add_parser("solve", help="Autonomous Issue Resolver: Localize bug, patch files, and verify fix")
    solve_parser.add_argument("issue", help="Bug report or issue description to resolve")
    solve_parser.add_argument("--repo", type=Path, default=Path("."), help="Target repository directory (default: current directory)")
    solve_parser.add_argument("--file", help="Specific target file relative to repository root")
    solve_parser.add_argument("--tests", default="", help="Optional test harness code or script")
    solve_parser.add_argument("--html", type=Path, help="Save standalone HTML verification report to file")
    solve_parser.add_argument("--offline", action="store_true")

    # Command 4: Autonomous Closed-Loop Self-Healing
    heal_parser = subparsers.add_parser("heal", help="Autonomous Closed-Loop Code Repair (Tests -> Traceback -> Fix -> Re-test)")
    heal_parser.add_argument("file", type=Path, help="Path to code file to auto-heal")
    heal_parser.add_argument("--tests", default="", help="Optional test harness script to verify fixes against")
    heal_parser.add_argument("--max-attempts", type=int, default=3, help="Max self-healing iterations (default: 3)")
    heal_parser.add_argument("--no-write", action="store_true", help="Do not overwrite file on disk (dry run)")
    heal_parser.add_argument("--offline", action="store_true")

    # Command 5: GitHub PR Review
    pr_parser = subparsers.add_parser("pr", help="Review a live GitHub Pull Request (URL or owner/repo#123)")
    pr_parser.add_argument("target", help="GitHub PR URL or 'owner/repo#number'")
    pr_parser.add_argument("--token", help="GitHub Personal Access Token (or GITHUB_TOKEN env var)")
    pr_parser.add_argument("--offline", action="store_true")

    # Command 6: Audit File
    audit_parser = subparsers.add_parser("audit", help="Audit an existing file using the Supreme Council")
    audit_parser.add_argument("file", type=Path, help="Path to code file to audit")
    audit_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    audit_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 7: Collaborative Relay
    relay_parser = subparsers.add_parser("relay", help="Run Collaborative Relay: Gemini (Architecture) -> Claude (Defensive Code) -> OpenAI (Tests)")
    relay_parser.add_argument("prompt", help="Task prompt for the relay pipeline")
    relay_parser.add_argument("-o", "--output", type=Path, help="Save generated code and tests to file")
    relay_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 8: Web UI Server
    serve_parser = subparsers.add_parser("serve", help="Launch the local interactive Web Dashboard")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind server (default: 8080)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")

    # Command 9: MCP Server
    mcp_parser = subparsers.add_parser("mcp", help="Run Apex-Council as a Model Context Protocol (MCP) server for Claude Desktop / Cursor")
    mcp_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 10: Git Diff Pre-Commit Review
    diff_parser = subparsers.add_parser("diff", help="Audit uncommitted Git diff changes before commit/push")
    diff_parser.add_argument("--staged", action="store_true", help="Review staged changes only")
    diff_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    diff_parser.add_argument("--offline", action="store_true")

    # Command 11: Red-Team Adversarial Fuzzer
    redteam_parser = subparsers.add_parser("redteam", help="Fuzz code file against adversarial injections and stress vectors")
    redteam_parser.add_argument("file", type=Path, help="Path to file to fuzz")

    # Command 12: SWE Benchmark Tournament
    bench_parser = subparsers.add_parser("benchmark", help="Run 5-Challenge SWE Tournament across Gemini, Claude, and OpenAI")
    bench_parser.add_argument("--format", choices=["table", "json"], default="table")
    bench_parser.add_argument("--offline", action="store_true")
    bench_parser.add_argument("--runtime", action="store_true", help="Execute high-precision runtime micro-benchmarks")

    # Command 13: Enterprise SOC2 Cryptographic Audit Verifier
    audit_ver_parser = subparsers.add_parser("audit-verify", help="Verify cryptographic SHA-256 integrity of SOC2 / ISO 27001 audit logs")
    audit_ver_parser.add_argument("--log", type=Path, default=Path("audit_trail.jsonl"), help="Path to audit trail log file")

    # Command 14: Enterprise Data Loss Prevention (DLP) Tester
    dlp_parser = subparsers.add_parser("dlp-test", help="Test Enterprise DLP sanitization of PII, credit cards, and corporate secrets")
    dlp_parser.add_argument("text", help="Text containing potential secrets or customer PII to sanitize")

    # Command 15: Enterprise Policy & Compliance Guardrail Checker
    policy_parser = subparsers.add_parser("policy-check", help="Audit code against Enterprise Compliance policies (licenses, banned libs, type hints)")
    policy_parser.add_argument("file", type=Path, help="Code file to audit for enterprise compliance")

    # Command 16: Init CI Workflow
    ci_parser = subparsers.add_parser("init-ci", help="Generate GitHub Actions PR workflow file")

    # Command 17: Personalized PageRank Repo-Map Engine
    repomap_parser = subparsers.add_parser("repomap", help="Generate Personalized PageRank repository structural map")
    repomap_parser.add_argument("repo", nargs="?", default=".", type=Path, help="Target repository directory (default: current directory)")
    repomap_parser.add_argument("--tokens", type=int, default=1024, help="Token budget for structural skeleton (default: 1024)")
    repomap_parser.add_argument("--focus", help="Comma-separated files to prioritize in PageRank")

    # Command 18: Autonomous 5-Role SWE Swarm
    swarm_parser = subparsers.add_parser("swarm", help="Autonomous 5-Role SWE Swarm: Architect -> Speculator (TDD) -> MCTS Search -> Gatekeeper")
    swarm_parser.add_argument("task", help="Software engineering task specification or bug description")
    swarm_parser.add_argument("--repo", type=Path, default=Path("."), help="Target repository directory (default: current directory)")
    swarm_parser.add_argument("--iters", type=int, default=4, help="MCTS tree search iterations (default: 4)")
    swarm_parser.add_argument("-o", "--output", type=Path, help="Save verified code to file")

    # Command 19: Persistent Episodic Memory Vault
    mem_parser = subparsers.add_parser("memory", help="Query or list institutional episodic engineering memory")
    mem_parser.add_argument("--query", help="Query memory for relevant heuristics and lessons")
    mem_parser.add_argument("--list", action="store_true", help="List all stored episodes")

    # Command 20: Zero-API-Key Offline Flight Recorder Replay
    demo_parser = subparsers.add_parser("demo", help="Zero-API-key offline flight recorder replay")
    demo_parser.add_argument("--replay", action="store_true", help="Stream realistic autonomous session")
    demo_parser.add_argument("--fast", action="store_true", help="Skip animation delay for speed")
    demo_parser.add_argument("--live", "--interactive", dest="live", action="store_true", help="5-stage live inductive program repair walkthrough")

    # Command 21: Cryptographic Hash-Chained Audit Ledger Verifier
    ledger_parser = subparsers.add_parser("verify-ledger", help="Verify HMAC-SHA512 cryptographic audit chain")
    ledger_parser.add_argument("--ledger", type=Path, default=Path(".apex/audit_chain.jsonl"), help="Path to audit ledger")

    # Command 22: Spectrum-Based Fault Localization (Ochiai)
    local_parser = subparsers.add_parser("localize", help="Spectrum-based fault localization using Ochiai algorithm")
    local_parser.add_argument("file", type=Path, help="Target Python source file to trace")
    local_parser.add_argument("--tests", default=None, help="Test code to run against the source file")
    local_parser.add_argument("--tests-file", type=Path, default=None, help="Path to tests file")

    # Command 23: Standalone Executable Compiler (zipapp)
    pyz_parser = subparsers.add_parser("build-pyz", help="Compile standalone zero-dependency apex.pyz executable")
    pyz_parser.add_argument("-o", "--output", default="dist/apex.pyz", help="Output path for .pyz archive")

    # Command 24: Micro-SWE-Bench Harness
    swe_parser = subparsers.add_parser("swe-bench", help="Run 5-Bug Real-World Micro-SWE-Bench harness")

    # Command 25: CPython Bytecode Autopsy Inspector
    autopsy_parser = subparsers.add_parser("autopsy", help="Disassemble crash site and capture opcode telemetry & frame locals")
    autopsy_parser.add_argument("file", type=Path, help="Python source file")
    autopsy_parser.add_argument("--tests", default="", help="Test harness code")

    # Command 26: Deterministic AST Program Synthesizer
    synth_parser = subparsers.add_parser("synthesize", help="Synthesize verified bug repairs using AST mutations with zero LLM calls")
    synth_parser.add_argument("file", type=Path, help="Target Python source file")
    synth_parser.add_argument("--line", type=int, help="Target line number (optional)")

    # Command 27: Verify Git Proof Note
    proof_parser = subparsers.add_parser("verify-proof", help="Verify HMAC-SHA512 cryptographic proof note on refs/notes/apex-proof")
    proof_parser.add_argument("commit", nargs="?", default="HEAD", help="Commit SHA or reference (default: HEAD)")
    proof_parser.add_argument("--repo", type=Path, default=Path("."), help="Repository path")

    # Command 28: Raspberry Pi & ESP32 Edge Runner
    edge_parser = subparsers.add_parser("edge", help="Raspberry Pi & ESP32 lightweight edge runner with thermal/RAM guards")
    edge_parser.add_argument("file", nargs="?", type=Path, help="Target Python source file to repair on edge")
    edge_parser.add_argument("--tests", default="", help="Test harness code")
    edge_parser.add_argument("--verify", action="store_true", help="Run 3-case built-in edge verification suite")

    # Command 29: Staff Performance & Latency Optimizer
    perf_parser = subparsers.add_parser("perf", help="Staff Performance Engineer: profile latency, detect O(N^2) loops & optimize AST")
    perf_parser.add_argument("file", type=Path, help="Target Python source file to profile")
    perf_parser.add_argument("--tests", default="", help="Optional test harness")

    # Command 30: Autonomous Chaos & Resilience SRE
    chaos_parser = subparsers.add_parser("chaos", help="Chaos SRE Engineer: inject socket timeouts, disk full, & transient RPC faults")
    chaos_parser.add_argument("file", type=Path, help="Target Python source file to test")
    chaos_parser.add_argument("--tests", default="", help="Optional test harness")

    # Command 31: Principal AppSec & Penetration Tester
    appsec_parser = subparsers.add_parser("appsec", help="Principal AppSec Engineer: AST taint flow analysis & automated secure remediation")
    appsec_parser.add_argument("file", type=Path, help="Target Python source file to audit")
    appsec_parser.add_argument("--remediate", action="store_true", help="Auto-remediate vulnerabilities")

    # Command 32: Principal Database & Storage Architect
    db_parser = subparsers.add_parser("db-tune", help="Database Architect: detect N+1 queries, synthesize B-Tree indexes, & tune SQLite WAL")
    db_parser.add_argument("file", type=Path, help="Target Python source file to analyze")

    # Command 33: Legacy Modernizer & Refactoring Engineer
    mod_parser = subparsers.add_parser("modernize", help="Legacy Modernizer: apply modern Python 3.10+ AST codemods (pathlib, PEP 604 unions)")
    mod_parser.add_argument("file", type=Path, help="Target Python source file to modernize")
    mod_parser.add_argument("--write", action="store_true", help="Overwrite file on disk with modernized code")

    # Command 34: Autonomous Release Captain & SemVer Auditor
    rel_parser = subparsers.add_parser("release", help="Release Captain: diff public API surfaces, calculate SemVer bump & generate changelog")
    rel_parser.add_argument("base_file", type=Path, help="Base / current version file")
    rel_parser.add_argument("candidate_file", type=Path, help="Candidate / new version file")
    rel_parser.add_argument("--version", default="1.0.0", help="Current version (default: 1.0.0)")

    # Command 35: Unified Spectrum-Based Fault Localization Triad
    sbfl_parser = subparsers.add_parser("sbfl", help="Unified SBFL Triad: localize faults via Ochiai, Tarantula, & DStar (D*) formulas")
    sbfl_parser.add_argument("file", type=Path, help="Target Python source file")
    sbfl_parser.add_argument("--tests", default=None, help="Test harness code or file path")
    sbfl_parser.add_argument("--tests-file", type=Path, default=None, help="Path to tests file")
    sbfl_parser.add_argument("--star", type=float, default=2.0, help="DStar tuning exponent (default: 2.0)")

    # Command 36: Formal Hoare Logic & Invariant Verifier
    hoare_parser = subparsers.add_parser("hoare", help="Formal Verifier: verify zero-division, loop termination, & None dereferences via Dijkstra WP")
    hoare_parser.add_argument("file", type=Path, help="Target Python source file to verify")

    # Command 37: Control Flow Graph & Lengauer-Tarjan Dominator Trees
    cfg_parser = subparsers.add_parser("cfg", help="Control Flow Graph & Lengauer-Tarjan Dominator Tree analysis")
    cfg_parser.add_argument("file", type=Path, help="Target Python source file to analyze")

    # Command 38: Abstract Interpretation & Interval Polyhedra Prover
    ai_parser = subparsers.add_parser("abstract-interp", help="Abstract Interpretation & Interval Polyhedra static safety prover")
    ai_parser.add_argument("file", type=Path, help="Target Python source file to prove")

    # Command 39: Counterexample-Guided Inductive Synthesis (CEGIS)
    cegis_parser = subparsers.add_parser("cegis", help="Counterexample-Guided Inductive Synthesizer (CEGIS)")
    cegis_parser.add_argument("file", type=Path, help="Target Python source file to repair")
    cegis_parser.add_argument("--tests", default=None, help="Test harness code")
    cegis_parser.add_argument("--tests-file", type=Path, default=None, help="Path to tests file")

    # Command 40: Solomonoff Algorithmic Prior & Kolmogorov Upper Bound
    sol_parser = subparsers.add_parser("solomonoff", help="Solomonoff Algorithmic Prior, Kolmogorov Bound, & Shannon AST Entropy")
    sol_parser.add_argument("file", type=Path, help="Target Python source file to evaluate")

    # Command 41: Bug Reproduction Oracle (Agentless-style)
    oracle_parser = subparsers.add_parser("oracle", help="Autonomous Bug Reproduction Oracle Synthesizer (Agentless style)")
    oracle_parser.add_argument("issue", help="Path to issue file or raw text description")
    oracle_parser.add_argument("--verify", action="store_true", help="Execute the generated oracle against local directory")

    # Command 42: Surgical AST Symbol Navigator (AutoCodeRover-style)
    ast_parser = subparsers.add_parser("ast-nav", help="Surgical AST Symbol Navigator & Call Hierarchy (AutoCodeRover style)")
    ast_parser.add_argument("query", help="Symbol or function or class name to search")
    ast_parser.add_argument("--dir", type=Path, default=Path("."), help="Root directory to search (default: current dir)")

    # Command 43: Cognitive Memory Stream & Context Guide (claude-mem style)
    memo_parser = subparsers.add_parser("memo-sync", help="Cognitive Memory Stream & CLAUDE.md Generator (claude-mem style)")
    memo_parser.add_argument("--export-claude-md", type=Path, help="Export high-density cache-optimized CLAUDE.md")
    memo_parser.add_argument("--search", help="Search institutional memory for past solutions")

    # Command 44: Mini-SWE Agent-Computer Interface (mini-swe-agent style)
    mini_parser = subparsers.add_parser("mini-swe", help="Mini-SWE-Agent ACI with Linter-in-the-Loop (mini-swe-agent style)")
    mini_parser.add_argument("issue", help="Path to issue text or bug description")
    mini_parser.add_argument("--workspace", type=Path, default=Path("."), help="Target workspace directory")

    # Command 45: Semantic Code Ontology (NVIDIA auto-ontology style)
    ont_parser = subparsers.add_parser("ontology", help="Semantic Code Ontology & Layer Boundary Checker (NVIDIA auto-ontology style)")
    ont_parser.add_argument("path", type=Path, help="Target file or directory to construct semantic ontology for")
    ont_parser.add_argument("--check-invariants", action="store_true", help="Validate architectural layer boundary invariants")
    ont_parser.add_argument("--impact", help="Explain blast radius and transitive callers of a symbol")
    ont_parser.add_argument("--hr-audit", action="store_true", help="Run Enterprise HR & Workforce Analytics diagnostic audit")
    ont_parser.add_argument("--query", help="Ask a natural language question over the semantic catalog")

    # Command 46: Spec-Driven Development Engine (github/spec-kit style)
    sdd_parser = subparsers.add_parser("sdd", help="Spec-Driven Development (SDD) Contract Compiler (github/spec-kit style)")
    sdd_parser.add_argument("spec", type=Path, help="Path to specification Markdown or JSON file")
    sdd_parser.add_argument("--validate", type=Path, help="Validate implementation module against spec contracts")
    sdd_parser.add_argument("--gen-tests", help="Generate standalone unittest suite for target module name")

    # Command 47: Git Worktree Trunk (max-sixty/worktrunk style)
    trunk_parser = subparsers.add_parser("worktrunk", help="Parallel Agent Git Worktree Manager (max-sixty/worktrunk style)")
    trunk_parser.add_argument("--allocate", help="Allocate an isolated worktree for an agent")
    trunk_parser.add_argument("--list", action="store_true", help="List active agent worktrees")
    trunk_parser.add_argument("--prune", help="Prune and delete worktree for agent")
    trunk_parser.add_argument("--cleanup-all", action="store_true", help="Clean up all active worktrees")

    # Command 48: Startup Executive Review (inspired by gstack)
    exec_parser = subparsers.add_parser("executive", help="Startup Executive Leadership Review (inspired by gstack)")
    exec_parser.add_argument("--title", required=True, help="Proposal or PR title")
    exec_parser.add_argument("--desc", required=True, help="Proposal description")
    exec_parser.add_argument("--diff", help="Path to diff or code file")

    # Command 49: Worktrunk Interactive Git Worktree Matrix (inspired by max-sixty/worktrunk)
    wt_p = subparsers.add_parser("wt", help="Worktrunk interactive worktree matrix & branch manager (Image 1 style)")
    wt_p.add_argument("subaction", nargs="?", default="list", choices=["list", "switch", "add", "remove"], help="Action: list, switch, add, remove")
    wt_p.add_argument("branch", nargs="?", help="Target branch for switch/add/remove")
    wt_p.add_argument("--full", action="store_true", help="Display full table with triple-dot diff and commit summary")

    # Command 50: Interactive Claude Code Style Terminal Console (Image 3)
    console_p = subparsers.add_parser("console", help="Claude Code style interactive terminal console with pixel mascot (Image 3)")
    console_p.add_argument("--mascot", choices=["falcon", "guardian", "aegis", "retro"], default="falcon", help="Apex mascot style")
    console_p.add_argument("--theme", choices=["gold", "amber", "cyan", "emerald", "violet"], default="gold", help="Aesthetic color palette")

    # Command 51: MLflow Agent Tracing & OpenTelemetry
    mlflow_p = subparsers.add_parser("mlflow-trace", help="MLflow-compatible Agent Tracing & OpenTelemetry exporter")
    mlflow_p.add_argument("--session", default="apex_council_session", help="Trace session name")
    mlflow_p.add_argument("--export-json", help="Export OpenTelemetry trace JSON file")

    # Command 52: MLflow LLM Judge Evaluation
    ml_eval_p = subparsers.add_parser("mlflow-eval", help="MLflow LLM Judge automated evaluation on code")
    ml_eval_p.add_argument("file", type=Path, help="Target Python source code to evaluate")
    ml_eval_p.add_argument("--prompt", default="Audit code quality and safety", help="Evaluation prompt")

    # Command 53: OmO Dual-Pane Live DAG & Task Visualizer (Image 1)
    omo_p = subparsers.add_parser("omo", help="OmO dual-pane live DAG & Task visualizer (Image 1)")
    omo_p.add_argument("--task", default="Linear gates integration evidence 1/1", help="Task title")
    omo_p.add_argument("--run-id", default="01a97526", help="DAG Run ID")

    # Command 54: Task DAG Compilation & Scheduling Analysis
    dag_p = subparsers.add_parser("dag", help="Compile and display Task DAG graph with wave scheduling")
    dag_p.add_argument("spec", nargs="?", help="Task specification or flow")

    # Command 55: Startup Engineering Suite (inspired by gstack)
    gstack_p = subparsers.add_parser("gstack", help="Startup engineering & review suite (inspired by gstack: office-hours, review, cso, ship)")
    gstack_p.add_argument("action", choices=["office-hours", "review", "cso", "ship", "autoplan"], help="Gstack command action")
    gstack_p.add_argument("target", nargs="?", default="", help="Target prompt, idea, or file path")
    gstack_p.add_argument("--diff", help="Path to diff or code file for review")
    gstack_p.add_argument("--bump", choices=["auto", "major", "minor", "patch"], default="auto", help="SemVer release bump")

    # Command 56: GBrain Multi-Session Context Engine (garrytan/gbrain)
    gbrain_p = subparsers.add_parser("gbrain", help="GBrain persistent memory & knowledge engine (garrytan/gbrain)")
    gbrain_p.add_argument("action", choices=["store", "recall", "correct", "withdraw", "lock"], help="GBrain action")
    gbrain_p.add_argument("params", nargs="*", help="Action parameters")
    gbrain_p.add_argument("--source", default="user_session", help="Fact source")
    gbrain_p.add_argument("--tags", default="general", help="Comma-separated tags")

    # Command 57: Scrapling Resilient Web Scraping Engine (D4Vinci/Scrapling)
    scrape_p = subparsers.add_parser("scrape", help="Scrapling resilient web scraping and DOM extraction engine (D4Vinci/Scrapling)")
    scrape_p.add_argument("target", help="URL or local HTML file path to scrape")
    scrape_p.add_argument("--tables", action="store_true", help="Extract tabular structures")

    # Command 58: Floci AWS Local Cloud Emulator (floci-io/floci)
    floci_p = subparsers.add_parser("floci", help="Floci local zero-cost AWS cloud emulator (floci-io/floci)")
    floci_p.add_argument("service", choices=["s3", "sqs", "dynamo", "stats"], help="Cloud service to interact with")
    floci_p.add_argument("action", nargs="?", default="list", help="Operation")
    floci_p.add_argument("params", nargs="*", help="Parameters for operation")

    # Command 59: VibeVoice Frontier Acoustic Synthesizer (microsoft/VibeVoice)
    voice_p = subparsers.add_parser("voice", help="VibeVoice frontier acoustic voice synthesizer (microsoft/VibeVoice)")
    voice_p.add_argument("persona", choices=["falcon", "guardian", "aegis", "ninja"], help="Council agent voice persona")
    voice_p.add_argument("text", help="Text to synthesize into speech")
    voice_p.add_argument("-o", "--output", help="Output .wav path")

    # Command 60: Garden Skills Registry & Execution (google/skills & ConardLi/garden-skills)
    skills_p = subparsers.add_parser("skills", help="Garden Skills agent skills registry & executor (ConardLi/garden-skills)")
    skills_p.add_argument("action", choices=["list", "run"], help="Skills action")
    skills_p.add_argument("name", nargs="?", help="Skill name to run")
    skills_p.add_argument("--tag", help="Filter skills by tag")

    # Command 61: Agent Browser Automation Engine (vercel-labs/agent-browser)
    browser_p = subparsers.add_parser("browser", help="Autonomous Agent Browser CLI & DOM snapshot engine (vercel-labs/agent-browser)")
    browser_p.add_argument("action", choices=["goto", "snapshot", "extract", "viewport"], help="Browser action")
    browser_p.add_argument("url", help="Target URL or HTML content")

    # Command 62: Electron Desktop Shell Bridge (electron/electron)
    electron_p = subparsers.add_parser("electron", help="Electron native desktop shell IPC bridge & scaffold (electron/electron)")
    electron_p.add_argument("action", choices=["scaffold", "bridge"], help="Scaffold desktop app or start bridge")
    electron_p.add_argument("--dir", default="electron", help="Target scaffold directory")
    electron_p.add_argument("--port", type=int, default=4242, help="Bridge port")

    # Command 63: REA (Reverse Engineering Anything)
    rea_p = subparsers.add_parser("rea", help="Reverse Engineering Anything: binary inspection, bytecode disasm, & evidence ledger")
    rea_p.add_argument("target", nargs="?", help="Target binary, archive, or code file to inspect")
    rea_p.add_argument("--file", dest="target_file", type=Path, help="Alternative flag for target file")
    rea_p.add_argument("--disasm", action="store_true", help="Disassemble bytecode or extract instruction heuristics")
    rea_p.add_argument("--evidence", action="store_true", help="Record finding into cryptographic Evidence Ledger")
    rea_p.add_argument("--claim", default="Automated REA artifact inspection", help="Assertion claim for evidence recording")
    rea_p.add_argument("--verify-ledger", action="store_true", help="Verify integrity of existing Evidence Ledger")
    rea_p.add_argument("--ledger-file", type=Path, default=Path(".apex/evidence_ledger.jsonl"), help="Path to ledger JSONL file")
    rea_p.add_argument("--format", choices=["table", "json", "markdown", "text"], default="table", help="Output report format")
    rea_p.add_argument("-o", "--output", type=Path, help="Save report to file")
    rea_p.add_argument("--export", type=Path, help="Export evidence or analysis to file")

    # Command 64: reviewdog (Automated Code Review Reporting)
    rd_p = subparsers.add_parser("reviewdog", help="Automated code review reporting & git diff-filtered diagnostics")
    rd_p.add_argument("input", nargs="?", default="-", help="Diagnostic input file or '-' for stdin")
    rd_p.add_argument("--file", dest="input_file", type=Path, help="Diagnostic input file (rdjson, checkstyle XML, or line format)")
    rd_p.add_argument("--format", choices=["auto", "rdjson", "rdjsonl", "checkstyle", "line"], default="auto", help="Diagnostic format")
    rd_p.add_argument("--diff", help="Git diff string or path to diff file")
    rd_p.add_argument("--git", action="store_true", help="Auto-capture git diff HEAD from repository")
    rd_p.add_argument("--filter", dest="filter_mode", choices=["added", "diff-context", "file", "nofilter"], default="added", help="Diff filter mode")
    rd_p.add_argument("--filter-mode", dest="filter_mode", choices=["added", "diff-context", "file", "nofilter"], default="added", help="Diff filter mode")
    rd_p.add_argument("--reporter", choices=["text", "terminal", "markdown", "github-pr", "github-annotations", "rdjson", "checkstyle"], default="text", help="Output reporter")
    rd_p.add_argument("--pattern", help="Custom regex pattern for line format parsing")
    rd_p.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    rd_p.add_argument("--fail-on-error", action="store_true", help="Exit code 1 if ERROR findings exist")
    rd_p.add_argument("-o", "--output", type=Path, help="Save report to file")
    rd_p.add_argument("--export", type=Path, help="Save report to file")

    # Command 65: Netdata (Real-Time Telemetry & Monitoring)
    nd_p = subparsers.add_parser("netdata", help="Real-time system telemetry collector, wire streaming, & REST client")
    nd_p.add_argument("--stream", action="store_true", help="Stream Netdata wire protocol to stdout")
    nd_p.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds (default: 1.0)")
    nd_p.add_argument("--export", choices=["json", "wire", "allmetrics"], default="json", help="Export format for telemetry snapshot")
    nd_p.add_argument("--serve", action="store_true", help="Run local Netdata REST API emulator daemon")
    nd_p.add_argument("--port", type=int, default=19999, help="Port for REST emulator server (default: 19999)")
    nd_p.add_argument("--info", action="store_true", help="Query /api/v1/info from local daemon or emulator")
    nd_p.add_argument("--url", default="http://127.0.0.1:19999", help="Target Netdata daemon URL")
    nd_p.add_argument("--once", action="store_true", help="Capture a single telemetry snapshot and exit")
    nd_p.add_argument("-o", "--output", type=Path, help="Save output to file")

    # Command 66: Lint (Built-in Zero-Dependency Linter)
    lint_p = subparsers.add_parser("lint", help="Zero-dependency AST linter emitting reviewdog rdjson or text")
    lint_p.add_argument("paths", nargs="+", help="Paths to files or directories to lint")
    lint_p.add_argument("--format", choices=["rdjson", "text"], default="text", help="Output format")
    lint_p.add_argument("--fail-on-error", action="store_true", help="Exit code 1 if ERROR findings exist")

    # Command 67: Pipe Fix (pytest | apex fix)
    fix_p = subparsers.add_parser("fix", help="Pipe auto-repair: parse traceback from stdin/log & synthesize 1-token fix")
    fix_p.add_argument("log", nargs="?", default="-", help="Path to traceback log file or '-' for stdin")
    fix_p.add_argument("--apply", action="store_true", help="Apply synthesized fix in-place to target file (creates .bak)")
    fix_p.add_argument("--tests", help="Optional test suite code")

    # Command 68: Self-Healing Git Hook (apex hook)
    hook_p = subparsers.add_parser("hook", help="Self-healing git pre-commit hook")
    hook_p.add_argument("action", choices=["install", "uninstall", "run"], default="run", nargs="?", help="Hook action")

    # Command 69: Mutation Challenge (apex challenge)
    chal_p = subparsers.add_parser("challenge", help="Mutation testing resilience score vs fake code coverage")
    chal_p.add_argument("file", type=Path, help="Target Python source file")
    chal_p.add_argument("--tests", help="Test code")
    chal_p.add_argument("--tests-file", type=Path, help="Path to tests file")
    chal_p.add_argument("--mutants", type=int, default=30, help="Max mutants to evaluate (default: 30)")

    # Command 70: Kotlin-Style Null Safety (apex null-guard)
    null_p = subparsers.add_parser("null-guard", help="Kotlin-style static null/none safety prover for Python")
    null_p.add_argument("paths", nargs="+", help="Files or directories to audit for unguarded None dereferences")
    null_p.add_argument("--fix", action="store_true", help="Auto-apply Kotlin-style safe navigation codemods")

    # Command 71: Continuous Watcher (apex watch)
    watch_p = subparsers.add_parser("watch", help="Continuous file watcher and automated test/repair trigger")
    watch_p.add_argument("path", nargs="?", default=".", help="Target directory or file to watch (default: .)")
    watch_p.add_argument("--cmd", dest="command", help="Custom test command to execute on change")
    watch_p.add_argument("--interval", type=float, default=0.5, help="Polling interval in seconds (default: 0.5)")
    watch_p.add_argument("--fix", action="store_true", help="Auto-repair regressions with CEGIS on test failure")
    watch_p.add_argument("--once", action="store_true", help="Execute single pass without looping")

    # Command 72: Program Slicing (apex slice)
    slice_p = subparsers.add_parser("slice", help="Backward/Forward AST data & control dependency program slicing (Weiser 1981)")
    slice_p.add_argument("target", help="Target source file (e.g. file.py:42) or file path")
    slice_p.add_argument("--line", type=int, help="Target line number (if not in target arg)")
    slice_p.add_argument("--var", help="Comma-separated variable names to slice for")

    # Command 73: Python 3.10+ / 3.12+ Modernizer (apex modern)
    modern_p = subparsers.add_parser("modern", help="Upgrade legacy typing (Union, Optional, List, Dict) to native PEP 604 & 585 syntax")
    modern_p.add_argument("files", nargs="+", help="Files to modernize")
    modern_p.add_argument("--write", action="store_true", help="Apply modernization changes in-place (creates .bak)")

    # Command 74: Language Server Protocol (apex lsp)
    subparsers.add_parser("lsp", help="Run standard-library Language Server Protocol (LSP) server over stdio")

    # Command 75: Autonomous Closed-Loop Repair (apex loop)
    loop_p = subparsers.add_parser("loop", help="Autonomous closed-loop test-driven repair (Feature #100)")
    loop_p.add_argument("--test-cmd", dest="test_command", help="Test command to run (default: python -m unittest)")
    loop_p.add_argument("--max-iter", dest="max_iterations", type=int, default=5, help="Max repair iterations (default: 5)")
    loop_p.add_argument("--commit", dest="auto_commit", action="store_true", help="Auto-commit verified repairs to Git")

    # Command 76: Patch Export (apex patch-export)
    patch_p = subparsers.add_parser("patch-export", help="Export unified .patch comparing file with .bak or git version")
    patch_p.add_argument("file", help="Target source file")
    patch_p.add_argument("-o", "--output", help="Output patch file (default: stdout)")
    patch_p.add_argument("--backup", help="Path to original/backup file")

    # Command 77: Crash Fingerprint (apex crash-fingerprint)
    fp_p = subparsers.add_parser("crash-fingerprint", help="Normalized deterministic SHA-256 crash fingerprint from traceback")
    fp_p.add_argument("log", nargs="?", default="-", help="Path to traceback log file or '-' for stdin")

    # Command 78: Terminal Flamegraph (apex flamegraph)
    flame_p = subparsers.add_parser("flamegraph", help="ASCII hierarchical execution flamegraph profiler")
    flame_p.add_argument("target", help="Target Python script to profile")
    flame_p.add_argument("--top", type=int, default=8, help="Top functions to show (default: 8)")

    # Command 79: PR Summary (apex pr-summary)
    pr_sum_p = subparsers.add_parser("pr-summary", help="Generate GitHub PR description from git diff")
    pr_sum_p.add_argument("--base", help="Base git ref to diff against (e.g. main, HEAD~1)")
    pr_sum_p.add_argument("--title", help="PR title header")

    # Command 80: Secret Mask (apex secret-mask)
    mask_p = subparsers.add_parser("secret-mask", help="Redact API keys, tokens, and credentials from text/logs")
    mask_p.add_argument("input", nargs="?", default="-", help="Input file or '-' for stdin")

    # Command 81: Shell Completion (apex completion)
    comp_p = subparsers.add_parser("completion", help="Generate shell auto-completion script (bash, zsh, powershell)")
    comp_p.add_argument("shell", choices=["bash", "zsh", "powershell", "pwsh"], help="Target shell")

    # Command 82: Zero-Division Guard (apex zero-div)
    zdiv_p = subparsers.add_parser("zero-div", help="Static AST analyzer and safe guard prover for division operators")
    zdiv_p.add_argument("paths", nargs="+", help="Files or directories to scan")

    # Command 83: Apple Instruments Memory Profiler (apex instruments)
    inst_p = subparsers.add_parser("instruments", help="Apple Instruments-grade line-by-line heap allocations & leak profiler")
    inst_p.add_argument("target", help="Target Python script to profile")
    inst_p.add_argument("--top", type=int, default=6, help="Top allocation hotspots to show (default: 6)")

    # Command 84: Apple Swift-Guard Prover (apex swift-guard)
    swift_p = subparsers.add_parser("swift-guard", help="Swift-grade pattern match exhaustiveness & let-immutability prover")
    swift_p.add_argument("paths", nargs="+", help="Files or directories to audit")

    # Command 85: Apple Pro Studio Console (apex studio)
    studio_p = subparsers.add_parser("studio", help="Launch Apple Pro Studio interactive web & terminal telemetry dashboard")
    studio_p.add_argument("--web", action="store_true", help="Launch interactive browser dashboard")
    studio_p.add_argument("--port", type=int, default=8765, help="Port for web studio (default: 8765)")
    studio_p.add_argument("--host", default="127.0.0.1", help="Host for web studio (default: 127.0.0.1)")
    studio_p.add_argument("--terminal", action="store_true", help="Render terminal dashboard only without web server")
    studio_p.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")

    # Command 86: Master Verification Runner (apex test-all)
    subparsers.add_parser("test-all", help="Execute unified master verification scorecard across all Apex systems")

    # Command 87: 5-Stage Live Inductive Program Repair Walkthrough (apex demo-live)
    subparsers.add_parser("demo-live", help="5-stage live inductive program repair walkthrough")

    # Command 88: High-Precision Runtime Micro-Benchmarks (apex bench-live)
    subparsers.add_parser("bench-live", help="Execute high-precision runtime micro-benchmarks")

    # Command 89: Autonomous Code Review & Defect Auditor (apex review)
    review_p = subparsers.add_parser("review", help="Autonomous code review and safety auditor")
    review_p.add_argument("target", nargs="?", default=".", help="Target file or directory to audit")

    # Command 90: Local Ollama Model Manager (apex ollama)
    ollama_p = subparsers.add_parser("ollama", help="Manage and run local Ollama GPU/CPU models")
    ollama_p.add_argument("ollama_args", nargs="*", help="Ollama subcommands (status, list, use <model>, run <prompt>)")

    # Command 91: Apex Sovereign Portable Binary Runner (apex runner / apex llamafile)
    runner_p = subparsers.add_parser("runner", help="Manage and run Apex Sovereign Portable Binary Runtimes")
    runner_p.add_argument("runner_args", nargs="*", help="Runner subcommands (status, run <prompt>, info)")

    llamafile_p = subparsers.add_parser("llamafile", help="Manage and run Apex Sovereign Portable Binary Runtimes (alias)")
    llamafile_p.add_argument("runner_args", nargs="*", help="Runner subcommands (status, run <prompt>, info)")

    # Command 92: Cloudflare Defensive Security Audit Engine (apex audit-sec / apex security-audit)
    audit_sec_p = subparsers.add_parser("audit-sec", help="Cloudflare-grade sovereign defensive security audit engine (Zero-Pip)")
    audit_sec_p.add_argument("audit_args", nargs="*", help="Target path and audit flags (--output-dir, --format, --strict)")

    security_audit_p = subparsers.add_parser("security-audit", help="Cloudflare-grade sovereign defensive security audit engine (alias)")
    security_audit_p.add_argument("audit_args", nargs="*", help="Target path and audit flags (--output-dir, --format, --strict)")

    # Command 93: Scala 3 Functional & Actor Concurrency Engine (apex scala / apex scala-guard)
    scala_p = subparsers.add_parser("scala", help="Scala 3 pure functional monadic & actor concurrency engine with static defect auditor")
    scala_p.add_argument("scala_args", nargs="*", help="Scala subcommands (demo, audit <path>, guard)")

    scala_guard_p = subparsers.add_parser("scala-guard", help="Scala 3 static defect & MatchError auditor (alias)")
    scala_guard_p.add_argument("scala_args", nargs="*", help="Target path to audit (.scala files)")

    # Command 94: Apache Spark Unified Analytics Engine (apex spark / apex spark-guard)
    spark_p = subparsers.add_parser("spark", help="Apache Spark unified analytics engine (RDD lineage DAG, Catalyst SQL optimizer, SparkGuard)")
    spark_p.add_argument("spark_args", nargs="*", help="Spark subcommands (demo, rdd, sql, audit <path>, guard)")

    spark_guard_p = subparsers.add_parser("spark-guard", help="SparkGuard static AppSec & OOM auditor for PySpark/Scala pipelines (alias)")
    spark_guard_p.add_argument("spark_args", nargs="*", help="Target path to audit (.py or .scala Spark files)")

    # Command 95: LangGenius Dify Agentic Workflow & RAG Engine (apex dify / apex dify-guard)
    dify_p = subparsers.add_parser("dify", help="LangGenius Dify visual agentic workflow DAG execution, in-memory BM25 RAG & DifyGuard")
    dify_p.add_argument("dify_args", nargs="*", help="Dify subcommands (demo, run <workflow.json>, audit <path>)")

    dify_guard_p = subparsers.add_parser("dify-guard", help="DifyGuard static AppSec, SSRF & dead-node auditor for Dify workflows (alias)")
    dify_guard_p.add_argument("dify_args", nargs="*", help="Target Dify workflow JSON/YAML file to audit")

    # Direct prompt fallback: `apex-council "my prompt"`
    parser.add_argument("direct_prompt", nargs="?", help="Direct prompt to convene the Council")
    parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Fail immediately with non-zero exit code if any live API call fails")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose diagnostics (provider endpoints, token telemetry, latency)")

    return parser.parse_args(raw_args)


def handle_init_ci() -> int:
    gh_dir = Path(".github/workflows")
    gh_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = gh_dir / "apex-council.yml"

    content = """name: Apex-Council Code Review

on:
  pull_request:
    branches: [ main, dev, master ]

jobs:
  council_audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Apex-Council
        run: pip install .
      - name: Run Council Audit on PR
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          apex-council diff --format markdown -o council_verdict.md
"""
    workflow_path.write_text(content, encoding="utf-8")
    print(f"Created GitHub Action workflow at: {workflow_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = parse_args(argv)

    # Enterprise DLP Test
    if args.command == "dlp-test":
        print("\n[APEX-COUNCIL] Running Enterprise DLP Sanitization...\n")
        res = EnterpriseDLP.sanitize(args.text)
        print(f"Redactions Made: {res.redactions_count}")
        print(f"Categories Found: {res.categories_found}")
        print(f"Sanitized Text:   {res.clean_text}\n")
        return 0

    # Enterprise Audit Verify
    if args.command == "audit-verify":
        print(f"\n[APEX-COUNCIL] Verifying SOC2 Cryptographic Audit Trail: {args.log}...\n")
        logger = CryptographicAuditLogger(log_path=args.log)
        valid, count, err = logger.verify_integrity()
        if valid:
            print(f"✓ AUDIT TRAIL VERIFIED: All {count} cryptographic hash chains are intact and tamper-free.")
            return 0
        else:
            print(f"✗ AUDIT INTEGRITY BREACH: {err}")
            return 1

    # Enterprise Policy Check
    if args.command == "policy-check":
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        content = args.file.read_text(encoding="utf-8", errors="ignore")
        print(f"\n[APEX-COUNCIL] Checking Enterprise Compliance Policies for: {args.file}...\n")
        passed, violations = EnterprisePolicyEngine.audit_enterprise_policies(content)
        if passed:
            print("✓ PASSED: Code adheres 100% to Enterprise Compliance & Licensing Baselines.")
            return 0
        else:
            print(f"✗ VIOLATIONS DETECTED ({len(violations)}):")
            for v in violations:
                print(f"  • [{v.rule_id}] {v.policy_name}: {v.description}")
                print(f"    Fix: {v.remediation}")
            return 1

    # Command 17: Personalized PageRank Repo-Map Engine
    if args.command == "repomap":
        repo_path = Path(args.repo).resolve()
        if not repo_path.exists():
            sys.stderr.write(f"Error: Directory not found: {repo_path}\n")
            return 2
        print(f"\n[APEX-COUNCIL] Scanning repository: {repo_path}...")
        focus = [f.strip() for f in args.focus.split(",")] if args.focus else None
        repo_map = RepoMap(repo_path, max_tokens=args.tokens)
        rendered = repo_map.generate_map(focus_files=focus, token_budget=args.tokens)
        summary = repo_map.get_summary()
        print(f"\nIndexed {summary['total_files']} files, {summary['total_symbols']} symbols.")
        print("Top Architectural Hubs:")
        for hub in summary["top_architectural_hubs"]:
            print(f"  • {hub['file']} [PageRank: {hub['pagerank']}]")
        print("\n" + rendered + "\n")
        return 0

    # Command 18: Autonomous 5-Role SWE Swarm
    if args.command == "swarm":
        print(CyberpunkTUI.render_banner())
        repo_path = Path(args.repo).resolve() if args.repo else Path(".")
        print(f"\n[SWARM] Initializing 5-Role Autonomous Swarm for: \"{args.task}\"...\n")
        vault = MemoryVault(Path(".apex/memory.db"))
        coordinator = SwarmCoordinator(repo_dir=repo_path, memory_vault=vault)
        solution = coordinator.solve(task_prompt=args.task, mcts_iterations=args.iters)
        print(CyberpunkTUI.render_swarm_card(solution))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(solution.verified_code, encoding="utf-8")
            print(f"\nVerified & signed code written to: {args.output}")
        return 0 if solution.is_passing else 1

    # Command 19: Persistent Episodic Memory Vault
    if args.command == "memory":
        vault = MemoryVault(Path(".apex/memory.db"))
        if args.query:
            matcher = MemoryMatcher(vault)
            rules = matcher.find_relevant_rules(args.query)
            episodes = matcher.find_relevant_episodes(args.query)
            print(f"\n[MEMORY] Query results for: \"{args.query}\"")
            print(f"Matched {len(rules)} heuristics and {len(episodes)} past episodes:")
            for r in rules:
                print(f"  • [{r.category}] {r.rule_text} (Confidence: {r.confidence_score})")
            for ep in episodes:
                print(f"  • [Episode] {ep.task_prompt} ➔ {ep.lesson_learned}")
        elif args.list:
            episodes = vault.get_all_episodes(limit=20)
            heuristics = vault.get_all_heuristics()
            print(f"\n[MEMORY] Institutional Knowledge Vault ({len(episodes)} episodes, {len(heuristics)} rules):")
            for ep in episodes:
                print(f"  • [{ep.status}] {ep.task_prompt[:50]} (Files: {', '.join(ep.target_files)})")
            for h in heuristics:
                print(f"  • [Rule: {h.category}] {h.rule_text}")
        else:
            print("Specify --query <text> or --list to inspect memory.")
        return 0

    # Command 20: Zero-API-Key Offline Flight Recorder Replay / Live Demo
    if args.command == "demo":
        if getattr(args, "live", False):
            from .ui.demo_engine import run_live_demo
            return run_live_demo(animated=not args.fast)
        delay = 0.0 if args.fast else 0.35
        FlightRecorderReplay.run_replay(delay_sec=delay)
        return 0

    if args.command == "demo-live":
        from .ui.demo_engine import run_live_demo
        return run_live_demo()

    if args.command == "bench-live":
        from .ui.benchmark_engine import run_benchmark_suite
        return run_benchmark_suite()

    if args.command == "review":
        from .ui.review_engine import run_code_review
        return run_code_review(args.target)

    # Command 90: Local Ollama Model Manager (apex ollama)
    if args.command == "ollama":
        from .providers.ollama_engine import handle_ollama_cli
        return handle_ollama_cli(args.ollama_args)

    # Command 91: Apex Sovereign Portable Binary Runner (apex runner / apex llamafile)
    if args.command in {"runner", "llamafile"}:
        from .providers.llamafile_engine import handle_runner_cli
        return handle_runner_cli(args.runner_args)

    # Command 92: Cloudflare Defensive Security Audit Engine (apex audit-sec / apex security-audit)
    if args.command in {"audit-sec", "security-audit"}:
        from .security.cloudflare_auditor import handle_security_audit_cli
        return handle_security_audit_cli(args.audit_args)

    # Command 93: Scala 3 Functional & Actor Concurrency Engine (apex scala / apex scala-guard)
    if args.command in {"scala", "scala-guard"}:
        from .scala.engine import handle_scala_cli
        if args.command == "scala-guard":
            return handle_scala_cli(["guard"] + args.scala_args)
        return handle_scala_cli(args.scala_args)

    # Command 94: Apache Spark Unified Analytics Engine (apex spark / apex spark-guard)
    if args.command in {"spark", "spark-guard"}:
        from .spark.engine import handle_spark_cli
        if args.command == "spark-guard":
            return handle_spark_cli(["guard"] + args.spark_args)
        return handle_spark_cli(args.spark_args)

    # Command 95: LangGenius Dify Agentic Workflow & RAG Engine (apex dify / apex dify-guard)
    if args.command in {"dify", "dify-guard"}:
        from .dify.engine import handle_dify_cli
        if args.command == "dify-guard":
            return handle_dify_cli(["guard"] + args.dify_args)
        return handle_dify_cli(args.dify_args)

    # Command 21: Cryptographic Hash-Chained Audit Ledger Verifier
    if args.command == "verify-ledger":
        ledger = CryptographicLedger(ledger_path=args.ledger)
        valid, count, msg = ledger.verify_chain()
        if valid:
            print(f"\n✓ AUDIT LEDGER VERIFIED: All {count} HMAC-SHA512 cryptographic blocks are tamper-free and intact.\n")
            return 0
        else:
            print(f"\n✗ TAMPER DETECTED: {msg}\n")
            return 1

    # 1. Autonomous AI Engineer: Build entire project from spec
    if args.command == "engineer":
        print(f"\n[APEX-COUNCIL] Autonomous AI Engineer activated for: \"{args.spec}\"...")
        print(f"[APEX-COUNCIL] Target output directory: {args.output}\n")
        engineer = AutonomousEngineer(force_offline=args.offline)
        proj = engineer.build_project(args.spec, args.output)
        print("==========================================================")
        print("   🤖 AUTONOMOUS AI ENGINEER: PROJECT COMPLETE   ")
        print("==========================================================")
        print(f"  Target Dir:    {proj.output_dir}")
        print(f"  Files Built:   {len(proj.files_created)}")
        for f in proj.files_created:
            status = "✓ OK" if f.syntax_valid and f.security_score >= 80 else "✗ CHECK"
            print(f"    • {f.relative_path:<16} (Security: {f.security_score:.0f}%, Status: {status})")
        print(f"  Tests Verified: {'✓ PASSED' if proj.tests_passed else '✗ FAILED'}")
        print(f"  Total Duration: {proj.total_time_ms:.1f} ms")
        print(f"  Git Status:     Initialized and committed autonomously!")
        print("==========================================================\n")
        return 0 if proj.tests_passed else 1

    # 2. Autonomous Issue Solver / Bug Hunter
    if args.command == "solve":
        if getattr(args, "file", None):
            print(f"\n[APEX] Issue Solver investigating: \"{args.issue}\" in {args.file}...\n")
            solver = AutonomousIssueSolver(repo_dir=args.repo)
            report = solver.solve_issue(
                target_file_rel=args.file,
                issue_description=args.issue,
                test_harness=getattr(args, "tests", ""),
            )
            print("==========================================================")
            print("         🔍 APEX ISSUE RESOLUTION REPORT                  ")
            print("==========================================================")
            print(f"  Target File:    {report.target_file}")
            print(f"  Status:         {'✓ PASSED & SIGNED' if report.success else '✗ FAILED'}")
            print(f"  Suspicious Lns: {report.suspicious_lines}")
            print(f"  Merkle Root:    {report.merkle_root[:16]}...")
            print(f"  Ledger Block:   #{report.ledger_block_index}")
            print(f"  Duration:       {report.duration_ms:.1f} ms")
            print("==========================================================\n")
            if getattr(args, "html", None):
                diff_text = CyberpunkTUI.render_diff(report.original_code, report.patched_code)
                HTMLReportGenerator.generate_report(
                    title="Apex Issue Resolution",
                    task_prompt=args.issue,
                    target_file=report.target_file,
                    diff_text=diff_text,
                    is_passing=report.success,
                    merkle_root=report.merkle_root,
                    signature=report.details.get("signature", "N/A"),
                    duration_ms=report.duration_ms,
                    output_path=args.html,
                )
                print(f"[✓] Standalone HTML report generated: {args.html}\n")
            return 0 if report.success else 1

        print(f"\n[APEX-COUNCIL] Autonomous Bug Hunter investigating issue: \"{args.issue}\"...")
        print(f"[APEX-COUNCIL] Scanning repository: {args.repo}...\n")
        engineer = AutonomousEngineer(force_offline=args.offline)
        res = engineer.solve_issue(args.repo, args.issue)
        print("==========================================================")
        print("   🔍 AUTONOMOUS ISSUE RESOLUTION REPORT   ")
        print("==========================================================")
        print(f"  Status:         {res['status'].upper()}")
        print(f"  Files Patched:  {res['files_repaired']}")
        print(f"  Summary:        {res['summary']}")
        print(f"  Duration:       {res['duration_ms']:.1f} ms")
        print("==========================================================\n")
        return 0

    # 3. Autonomous Self-Healing Mode
    if args.command == "heal":
        print(f"\n[APEX-COUNCIL] Starting Autonomous Closed-Loop Self-Healing for: {args.file}...\n")
        healer = SelfHealingLoop(force_offline=args.offline)
        res = healer.heal(
            target_file=args.file,
            test_script=args.tests,
            max_attempts=args.max_attempts,
            auto_write=not args.no_write,
        )
        print("==========================================================")
        print("   🩺 AUTONOMOUS SELF-HEALING REPAIR REPORT   ")
        print("==========================================================")
        status_text = "✓ SUCCESSFULLY HEALED" if res.healed else "✗ HEALING INCOMPLETE"
        print(f"  Status:          {status_text}")
        print(f"  Iterations Run:  {res.iterations_run} / {args.max_attempts}")
        print(f"  Security Score:  {res.initial_security_score:.0f}% ➔ {res.final_security_score:.0f}%")
        print(f"  Duration:        {res.total_time_ms:.1f} ms")
        if res.healed:
            action = "File overwritten on disk" if not args.no_write else "Dry run (not written to disk)"
            print(f"  Action:          {action}")
        else:
            print(f"  Final Error:     {res.final_error}")
        print("==========================================================\n")
        return 0 if res.healed else 1

    # 4. GitHub PR Review
    if args.command == "pr":
        print(f"\n[APEX-COUNCIL] Fetching and reviewing GitHub PR: {args.target}...\n")
        pr_res = review_github_pr(args.target, token=args.token, force_offline=args.offline)
        print(pr_res["markdown_comment"])
        return 0

    # 5. MCP Server
    if args.command == "mcp":
        server = ApexCouncilMCPServer(force_offline=args.offline)
        server.run()
        return 0

    # 6. Benchmark Tournament
    if args.command == "benchmark":
        if getattr(args, "runtime", False):
            from .ui.benchmark_engine import run_benchmark_suite
            return run_benchmark_suite()
        print("\n[APEX-COUNCIL] Starting SWE Benchmark Tournament across 5 production challenges...\n")
        bench_data = run_benchmark_tournament(force_offline=args.offline)
        if args.format == "json":
            import json
            print(json.dumps(bench_data, indent=2))
        else:
            print(format_benchmark_table(bench_data))
        return 0

    # 7. Red-Team Fuzzer
    if args.command == "redteam":
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        content = args.file.read_text(encoding="utf-8", errors="ignore")
        print(f"\n[APEX-COUNCIL] Red-Teaming code in: {args.file}...\n")
        report = run_redteam_analysis(content)
        print("==========================================================")
        print("   ⚔️ RED-TEAM ADVERSARIAL STRESS & FUZZING REPORT   ")
        print("==========================================================")
        print(f"  Probes Run:    {report.total_probes}")
        print(f"  Passed Probes: {report.passed_probes}")
        print(f"  Failed Probes: {report.failed_probes}")
        print(f"  Survival Rate: {report.survival_rate}%\n")
        if report.findings:
            print("  Vulnerabilities & Weaknesses Detected:")
            for f in report.findings:
                print(f"    • {f}")
        else:
            print("  ✓ Zero vulnerabilities triggered by hostile attack probes!")
        print("==========================================================\n")
        return 0 if report.failed_probes == 0 else 1

    # 8. Git Diff Review
    if args.command == "diff":
        print("\n[APEX-COUNCIL] Inspecting uncommitted Git diff...\n")
        diff_res = review_git_diff(staged_only=args.staged, force_offline=args.offline)
        if diff_res["status"] == "clean":
            print(f"✓ {diff_res['message']}")
            return 0
        c_res = diff_res["council_result"]
        if args.format == "json":
            print(c_res.to_json())
        elif args.format == "markdown":
            print(CouncilReporter.format_markdown(c_res))
        else:
            print(CouncilReporter.format_terminal(c_res))
        return 0

    # 9. Handle init-ci
    if args.command == "init-ci":
        return handle_init_ci()

    # 10. Handle serve
    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0

    # 11. Handle relay
    if args.command == "relay":
        print(f"\n[APEX-COUNCIL] Running Collaborative Relay for: \"{args.prompt}\"...\n")
        engine = CouncilEngine(force_offline=args.offline)
        res = engine.collaborative_relay(args.prompt)
        print(f"--- RELAY PIPELINE COMPLETE ({res['total_time_ms']:.1f}ms) ---")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(res["combined_code"], encoding="utf-8")
            print(f"Saved to: {args.output}")
        else:
            print(res["combined_code"])
        return 0

    # 12. Handle audit
    if args.command == "audit":
        print(f"\n[APEX-COUNCIL] Auditing file: {args.file}...\n")
        engine = CouncilEngine(force_offline=args.offline)
        audit_res = engine.audit_file(args.file)
        c_res = audit_res["council_result"]
        if args.format == "json":
            print(c_res.to_json())
        elif args.format == "markdown":
            print(CouncilReporter.format_markdown(c_res))
        else:
            print(f"Original Security Score: {audit_res['original_security_score']}%")
            if audit_res['original_security_issues']:
                print(f"Issues Detected: {audit_res['original_security_issues']}")
            print(CouncilReporter.format_terminal(c_res))
        return 0

    # 13. Spectrum-Based Fault Localization (Ochiai)
    if args.command == "localize":
        if not args.file.exists():
            sys.stderr.write(f"Error: Target file not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        tests = ""
        if getattr(args, "tests_file", None) and args.tests_file:
            if not args.tests_file.exists():
                sys.stderr.write(f"Error: Tests file not found: {args.tests_file}\n")
                return 2
            tests = args.tests_file.read_text(encoding="utf-8")
        elif getattr(args, "tests", None):
            test_path = Path(args.tests)
            if test_path.exists():
                tests = test_path.read_text(encoding="utf-8")
            else:
                tests = args.tests
        else:
            sys.stderr.write("Error: Either --tests or --tests-file must be provided.\n")
            return 2
        print(f"\n[APEX-COUNCIL] Running Ochiai Fault Localization on: {args.file}...")
        localizer = OchiaiFaultLocalizer()
        localizer.trace_execution(code, tests, args.file.name)
        ranked = localizer.rank_suspicious_statements()
        print("==========================================================")
        print("   🔍 OCHIAI SPECTRUM-BASED FAULT LOCALIZATION   ")
        print("==========================================================")
        if not ranked:
            print("  No suspicious statements identified (all tests passed or no trace).")
        else:
            for s in ranked[:10]:
                print(f"  Line {s.line_number:4d} | Suspiciousness: {s.suspiciousness:.4f} | {s.source_code.strip()[:60]}")
        print("==========================================================\n")
        return 0

    # 14. Build Standalone Executable (zipapp)
    if args.command == "build-pyz":
        import importlib
        build_mod = importlib.import_module("scripts.build_pyz")
        out_path = build_mod.build_standalone_pyz(output_path=args.output)
        return 0

    # 15. Micro-SWE-Bench Tournament
    if args.command == "swe-bench":
        import importlib
        bench_mod = importlib.import_module("benchmarks.micro_swebench")
        bench_mod.run_benchmark()
        return 0

    # 16. CPython Bytecode Autopsy
    if args.command == "autopsy":
        from .autopsy.bytecode_inspector import BytecodeInspector
        from .security.safe_exec import safe_exec
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        def run_target() -> None:
            scope = {}
            safe_exec(code, scope, filename=str(args.file))
            if args.tests:
                safe_exec(args.tests, scope, filename=f"test_{args.file.name}")

        _, report = BytecodeInspector.execute_and_autopsy(run_target)
        print("==========================================================")
        print("   🔬 CPYTHON BYTECODE CRASH AUTOPSY REPORT   ")
        print("==========================================================")
        if report and report.crashed:
            print(f"  Crashed: True")
            print(f"  Exception: {report.exception_type}: {report.exception_message}")
            print(f"  Location: {report.crashing_file}:{report.crashing_line} in {report.crashing_function}()")
            if report.crashing_instruction:
                print(f"  Crashing Opcode: {report.crashing_instruction.opname} (offset {report.crashing_instruction.offset})")
            print("  Surrounding Disassembly:")
            for op in report.surrounding_opcodes:
                marker = ">>>" if op.is_crashing else "   "
                print(f"    {marker} {op.offset:4d} {op.opname:<20} {op.argval if op.argval is not None else ''}")
        else:
            print("  Crashed: False")
            print("  Execution completed cleanly with zero unhandled exceptions.")
        print("==========================================================\n")
        return 0

    # 17. Deterministic AST Synthesis
    if args.command == "synthesize":
        from .synthesis.ast_synthesizer import DeterministicASTSynthesizer
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        target_lines = [args.line] if args.line else None
        candidates = DeterministicASTSynthesizer.synthesize_repairs(code, suspicious_lines=target_lines)
        print("==========================================================")
        print(f"   🧬 DETERMINISTIC AST SYNTHESIS ({len(candidates)} candidates)   ")
        print("==========================================================")
        for i, cand in enumerate(candidates, 1):
            print(f"\nCandidate {i} [{cand.repair_strategy} | Edit Dist: {cand.ast_edit_distance}]:")
            print(cand.candidate_code)
        print("==========================================================\n")
        return 0

    # 18. Verify Git Proof Note
    if args.command == "verify-proof":
        from .git_engine.proof_notes import GitProofNotesEngine
        engine = GitProofNotesEngine(args.repo)
        valid, msg, proof = engine.verify_proof(args.commit)
        print("==========================================================")
        print("      🛡️ APEX CRYPTOGRAPHIC PROOF VERIFICATION           ")
        print("==========================================================")
        print(f"  Status: {'[VALID]' if valid else '[INVALID]'}")
        print(f"  Message: {msg}")
        if proof:
            print(f"  Commit: {proof.commit_sha}")
            print(f"  Target File: {proof.target_file}")
            print(f"  Ochiai SBFL Score: {proof.ochiai_score}")
            print(f"  Mutation Kill Score: {proof.mutation_kill_score:.1f}%")
            print(f"  Merkle Root: {proof.merkle_root}")
            print(f"  Timestamp: {proof.timestamp_iso}")
        print("==========================================================\n")
        return 0 if valid else 1

    # 19. Raspberry Pi & ESP32 Edge Runner
    if args.command == "edge":
        from .edge.edge_runner import ApexEdgeRunner
        runner = ApexEdgeRunner()
        if args.verify or not args.file:
            print("\n[APEX-COUNCIL] Running Raspberry Pi & ESP32 Edge Self-Verification Suite...\n")
            test_cases = [
                (
                    "Case 1: Sensor Window Off-By-One Bug (IndexError)",
                    "def moving_sum(readings):\n    total = 0\n    for i in range(len(readings) + 1):\n        total += readings[i]\n    return total\n",
                    "assert moving_sum([10, 20, 30]) == 60\nassert moving_sum([]) == 0\n",
                ),
                (
                    "Case 2: Telemetry Voltage Divider Crash (ZeroDivisionError)",
                    "def compute_efficiency(output_watts, input_watts):\n    ratio = output_watts / input_watts\n    return round(ratio * 100.0, 2)\n",
                    "assert compute_efficiency(50.0, 100.0) == 50.0\nassert compute_efficiency(0.0, 0.0) == 0.0\n",
                ),
                (
                    "Case 3: ESP32 Packet Header Missing Key (KeyError)",
                    "def extract_rssi(packet):\n    rssi = packet['rssi_dbm']\n    return rssi if rssi is not None else -100\n",
                    "assert extract_rssi({'rssi_dbm': -62}) == -62\nassert extract_rssi({'node_id': 'esp32_01'}) == -100\n",
                ),
            ]
            for title, buggy_src, test_src in test_cases:
                res = runner.solve(buggy_src.strip(), test_src.strip())
                status_mark = "✓" if res.repaired else "✗"
                print(f"[{status_mark}] {title}")
                print(f"    Strategy: {res.strategy} ({res.execution_ms:.1f}ms) | Opcodes: {res.post_patch_opcodes} | Peak RAM: {res.post_patch_peak_bytes}B")
                print(f"    HMAC-SHA512: {res.hmac_sha512_signature[:40]}...")
            print("\n[✓] Edge runner verification complete.\n")
            return 0

        if not args.file.exists():
            sys.stderr.write(f"Error: Target file not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        res = runner.solve(code, args.tests)
        print("==========================================================")
        print("               ⚡ APEX EDGE RUNNER REPORT                 ")
        print("==========================================================")
        print(f"  Repaired:        {res.repaired}")
        print(f"  Strategy:        {res.strategy}")
        print(f"  Opcodes:         {res.post_patch_opcodes} VM instructions")
        print(f"  Peak RAM:        {res.post_patch_peak_bytes} bytes")
        print(f"  Latency:         {res.execution_ms:.1f} ms")
        print(f"  HMAC-SHA512:     {res.hmac_sha512_signature[:48]}...")
        print(f"  Hardware Temp:   {res.hardware_status.cpu_temp_celsius:.1f}°C")
        print(f"  Free RAM:        {res.hardware_status.available_ram_mb} MB")
        print("  Patched AST:")
        for l in res.patched_code.splitlines():
            print(f"    | {l}")
        print("==========================================================\n")
        if res.repaired:
            args.file.write_text(res.patched_code, encoding="utf-8")
            print(f"[✓] Overwritten {args.file} with verified patch.\n")
        return 0 if res.repaired else 1

    # 20. Staff Performance & Latency Optimizer
    if args.command == "perf":
        from .swarm.specialists.performance_engineer import PerformanceOptimizer
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        rep = PerformanceOptimizer.profile_and_optimize(code, getattr(args, "tests", ""))
        print("==========================================================")
        print("   ⚡ STAFF PERFORMANCE & LATENCY REPORT   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Antipatterns:    {len(rep.antipatterns_detected)}")
        print(f"  Orig Duration:   {rep.original_duration_ms:.2f} ms")
        print(f"  Opt Duration:    {rep.optimized_duration_ms:.2f} ms")
        print(f"  Peak Memory:     {rep.peak_memory_bytes} bytes")
        print(f"  Speedup Ratio:   {rep.speedup_ratio:.2f}x")
        print(f"  Has Regressed:   {'✗ YES (>5%)' if rep.has_regressed else '✓ NO'}")
        if rep.antipatterns_detected:
            print("  Detected Bottlenecks:")
            for a in rep.antipatterns_detected:
                print(f"    - [{a.severity}] {a.category} (Line {a.lineno}): {a.description}")
        print("==========================================================\n")
        return 1 if rep.has_regressed else 0

    # 21. Autonomous Chaos & Resilience SRE
    if args.command == "chaos":
        from .swarm.specialists.chaos_engineer import ChaosResilienceEngineer
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        rep = ChaosResilienceEngineer.run_chaos_experiments(code, getattr(args, "tests", ""))
        print("==========================================================")
        print("   🐒 AUTONOMOUS CHAOS & SRE RESILIENCE REPORT   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Experiments:     {rep.total_experiments}")
        print(f"  Resilient Count: {rep.resilient_count} / {rep.total_experiments}")
        print(f"  Resilience Score:{rep.resilience_score:.1f}%")
        print(f"  Production Ready:{'✓ YES' if rep.is_production_ready else '✗ FRAGILE'}")
        print("  Chaos Experiment Results:")
        for r in rep.results:
            mark = "✓ PASS" if r.survived else "✗ FAIL"
            print(f"    - [{mark}] {r.scenario_name} ({r.fault_type}): {r.duration_ms:.1f}ms")
        print("==========================================================\n")
        return 0 if rep.is_production_ready else 1

    # 22. Principal AppSec & Penetration Tester
    if args.command == "appsec":
        from .swarm.specialists.appsec_engineer import AppSecPenetrationTester
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        rep = AppSecPenetrationTester.audit_and_remediate(code)
        print("==========================================================")
        print("   🛡️ PRINCIPAL APPSEC PENETRATION AUDIT   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Taint Flows:     {len(rep.taint_flows)}")
        print(f"  Vulnerabilities: {len(rep.vulnerabilities)}")
        print(f"  Security Score:  {rep.security_score:.1f}%")
        print(f"  Airtight:        {'✓ YES' if rep.is_airtight else '✗ VULNERABLE'}")
        if rep.vulnerabilities:
            print("  Security Findings:")
            for v in rep.vulnerabilities:
                print(f"    - [{v.severity}] {v.category} (Line {v.lineno}): {v.description}")
        print("==========================================================\n")
        if getattr(args, "remediate", False) and not rep.is_airtight:
            args.file.write_text(rep.remediated_code, encoding="utf-8")
            print(f"[✓] Overwritten {args.file} with remediated secure code.\n")
        return 0 if rep.is_airtight else 1

    # 23. Principal Database & Storage Architect
    if args.command == "db-tune":
        from .swarm.specialists.database_architect import DatabaseArchitect
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        rep = DatabaseArchitect.analyze_and_tune(code)
        print("==========================================================")
        print("   🗄️ PRINCIPAL DATABASE ARCHITECTURE REPORT   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Antipatterns:    {len(rep.antipatterns)}")
        print(f"  Opt Score:       {rep.optimization_score:.1f}%")
        print(f"  Optimized:       {'✓ YES' if rep.is_optimized else '✗ BOTTLENECKS DETECTED'}")
        if rep.antipatterns:
            print("  Query Antipatterns:")
            for a in rep.antipatterns:
                print(f"    - [{a.severity}] {a.category} (Line {a.lineno}): {a.description}")
        if rep.recommended_indexes:
            print("  Synthesized B-Tree Indexes:")
            for idx in rep.recommended_indexes:
                print(f"    + {idx}")
        print("==========================================================\n")
        return 0

    # 24. Legacy Modernizer & Refactoring Engineer
    if args.command == "modernize":
        from .swarm.specialists.codebase_modernizer import CodebaseModernizer
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        rep = CodebaseModernizer.modernize_code(code)
        print("==========================================================")
        print("   🔄 PYTHON 3.10+ MODERNIZATION REPORT   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Transformations: {len(rep.transformations_applied)}")
        print(f"  Modernity Score: {rep.modernity_score:.1f}%")
        if rep.transformations_applied:
            print("  Codemods Applied:")
            for t in rep.transformations_applied:
                print(f"    - [{t.category}] (Line {t.lineno}): {t.description}")
        print("==========================================================\n")
        if getattr(args, "write", False):
            args.file.write_text(rep.modernized_code, encoding="utf-8")
            print(f"[✓] Overwritten {args.file} with modern Python 3.10+ AST syntax.\n")
        return 0

    # 25. Autonomous Release Captain & SemVer Auditor
    if args.command == "release":
        from .swarm.specialists.release_captain import ReleaseCaptain
        if not args.base_file.exists() or not args.candidate_file.exists():
            sys.stderr.write("Error: Both base_file and candidate_file must exist.\n")
            return 2
        base_src = args.base_file.read_text(encoding="utf-8")
        cand_src = args.candidate_file.read_text(encoding="utf-8")
        rep = ReleaseCaptain.evaluate_release(base_src, cand_src, current_version=getattr(args, "version", "1.0.0"))
        print("==========================================================")
        print("   🚀 AUTONOMOUS RELEASE CAPTAIN & SEMVER REPORT   ")
        print("==========================================================")
        print(f"  Current Version: {rep.current_version}")
        print(f"  Next Version:    {rep.next_version} ({rep.bump_type})")
        print(f"  Breaking Change: {'⚠️ YES (Major Bump)' if rep.is_breaking else '✓ NO'}")
        print(f"  API Deltas:      {len(rep.deltas)}")
        print(f"  Release Root:    {rep.release_merkle_root[:16]}...")
        print(f"  Release Sig:     {rep.release_signature[:32]}...")
        print("\n--- GENERATED CHANGELOG ---")
        print(rep.changelog_markdown)
        print("==========================================================\n")
        return 0

    # Command 35: Unified SBFL Triad
    if args.command == "sbfl":
        from .autopsy.sbfl_triad import SBFLTriadEngine
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        test_text = ""
        if getattr(args, "tests_file", None) and args.tests_file:
            if not args.tests_file.exists():
                sys.stderr.write(f"Error: Tests file not found: {args.tests_file}\n")
                return 2
            test_text = args.tests_file.read_text(encoding="utf-8")
        elif getattr(args, "tests", None):
            test_path = Path(args.tests)
            if test_path.exists():
                test_text = test_path.read_text(encoding="utf-8")
            else:
                test_text = args.tests
        else:
            sys.stderr.write("Error: Either --tests or --tests-file must be provided.\n")
            return 2
        engine = SBFLTriadEngine(star_exponent=getattr(args, "star", 2.0))
        rep = engine.localize(src, test_text, target_filename=str(args.file))
        print("==========================================================")
        print("   🔍 UNIFIED SBFL FAULT LOCALIZATION TRIAD   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Total Tests:     {rep.total_tests} (Pass: {rep.passed_tests}, Fail: {rep.failed_tests})")
        print(f"  Top Suspicious:  Line {rep.top_suspicious_line or 'N/A'}")
        print(f"  Confidence:      {rep.consensus_confidence * 100:.1f}%")
        print("  Top Suspicious Statements:")
        for r in rep.ranked_lines[:5]:
            print(f"    - Line {r.lineno:3d} | Ensemble: {r.ensemble:.3f} | Ochiai: {r.ochiai:.3f} | D*: {r.dstar:.3f} | Tarantula: {r.tarantula:.3f}")
            print(f"      Code: {r.source_line.strip()[:60]}")
        print("==========================================================\n")
        return 0

    # Command 36: Formal Hoare Logic Verifier
    if args.command == "hoare":
        from .formal.hoare_invariants import HoareInvariantVerifier
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        rep = HoareInvariantVerifier.verify_code(src)
        print("==========================================================")
        print("   📐 FORMAL HOARE LOGIC & INVARIANT VERIFICATION   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Provably Safe:   {'✓ YES' if rep.is_provably_safe else '✗ VIOLATIONS DETECTED'}")
        print(f"  Safety Score:    {rep.safety_confidence * 100:.1f}%")
        print(f"  Triples Checked: {rep.hoare_triples_verified} / {rep.total_invariants_checked}")
        if rep.violations:
            print("  Invariant Violations:")
            for v in rep.violations:
                print(f"    - [{v.severity}] {v.category} (Line {v.lineno}): {v.expression}")
                print(f"      Weakest Precondition: {v.weakest_precondition}")
                print(f"      Remediation:          {v.remediation_hint}")
        print("==========================================================\n")
        return 0 if rep.is_provably_safe else 1

    # Command 37: Control Flow Graph & Dominator Trees
    if args.command == "cfg":
        from .graph.cfg_dominator import CFGDominatorEngine
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        rep = CFGDominatorEngine.analyze_source(src)
        print("==========================================================")
        print("   🌳 CONTROL FLOW GRAPH & LENGAUER-TARJAN DOMINATOR TREE   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Basic Blocks:    {rep.total_blocks}")
        print(f"  CFG Edges:       {rep.total_edges}")
        print(f"  Complexity M:    {rep.cyclomatic_complexity}")
        print(f"  Natural Loops:   {len(rep.natural_loops)}")
        print("  Immediate Dominators (idom):")
        for node, dom in sorted(rep.immediate_dominators.items()):
            print(f"    - Block {node} <= idom: {f'Block {dom}' if dom is not None else 'ROOT (Entry)'}")
        if rep.natural_loops:
            print("  Natural Loop Headers:")
            for idx, loop in enumerate(rep.natural_loops, 1):
                print(f"    + Loop #{idx}: Header B{loop.header} (Back-edge: B{loop.back_edge_source} -> B{loop.header}, Blocks: {sorted(loop.body_blocks)})")
        print("==========================================================\n")
        return 0

    # Command 38: Abstract Interpretation & Interval Polyhedra Prover
    if args.command == "abstract-interp":
        from .formal.abstract_interpreter import ASTAbstractInterpreter
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        analyzer = ASTAbstractInterpreter()
        rep = analyzer.analyze(src)
        print("==========================================================")
        print("   🌐 ABSTRACT INTERPRETATION & INTERVAL POLYHEDRA PROVER   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Total Proofs:    {rep.total_proofs}")
        print(f"  Certified Safe:  {rep.proven_safe_count} / {rep.total_proofs}")
        print(f"  Zero-Div Risks:  {rep.zero_division_risks}")
        print("  Variable Intervals (Fixed-Point):")
        for var, inv in sorted(rep.final_state.environment.items()):
            print(f"    • {var}: {inv}")
        if rep.safety_proofs:
            print("  Static Safety Invariant Proofs:")
            for p in rep.safety_proofs:
                mark = "✓ SAFE" if p.is_provably_safe else "✗ VIOLATION"
                print(f"    - [{mark}] Line {p.lineno} ({p.proof_type}): {p.explanation}")
        print("==========================================================\n")
        return 0 if rep.zero_division_risks == 0 else 1

    # Command 39: Counterexample-Guided Inductive Synthesis (CEGIS)
    if args.command == "cegis":
        from .synthesis.cegis_engine import CEGISEngine
        from .ui.repair_report import render_repair
        from .autopsy.sbfl_triad import SBFLTriadEngine
        from .security.sandbox import HermeticExecutionSandbox

        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        tests = ""
        if getattr(args, "tests_file", None) and args.tests_file:
            if not args.tests_file.exists():
                sys.stderr.write(f"Error: Tests file not found: {args.tests_file}\n")
                return 2
            tests = args.tests_file.read_text(encoding="utf-8")
        elif getattr(args, "tests", None):
            test_path = Path(args.tests)
            if test_path.exists():
                tests = test_path.read_text(encoding="utf-8")
            else:
                tests = args.tests
        else:
            sys.stderr.write("Error: Either --tests or --tests-file must be provided.\n")
            return 2

        # 1. Run SBFL triad engine for suspicious line hints
        suspects: list[tuple[int, float]] = []
        try:
            sbfl_engine = SBFLTriadEngine()
            sbfl_rep = sbfl_engine.localize(src, tests, target_filename=str(args.file))
            def _rank_key(item):
                code = item.source_line.strip()
                has_ctrl = any(tok in code for tok in ["while", "if", "for", "<", ">", "==", "!=", "<=", ">="])
                return (round(item.ochiai, 4), 1 if has_ctrl else 0, -item.lineno)

            filtered = [
                item for item in sbfl_rep.ranked_lines
                if item.ochiai > 0 and not item.source_line.strip().startswith("def ")
            ]
            filtered.sort(key=_rank_key, reverse=True)
            for item in filtered:
                suspects.append((item.lineno, item.ochiai))
        except Exception:
            pass

        # 2. Run CEGIS engine
        engine = CEGISEngine()
        rep = engine.synthesize_and_verify(src, tests)

        # 3. Parse visible test count
        test_units = [l.strip() for l in tests.splitlines() if l.strip().startswith("assert") or l.strip().startswith("def test_")]
        if not test_units:
            test_units = [l.strip() for l in tests.splitlines() if l.strip() and not l.strip().startswith("#")]
        total_visible = max(1, len(test_units))
        visible = (total_visible, total_visible) if rep.success else (0, total_visible)

        # 4. Run differential oracle / hidden probes
        hidden = None
        if rep.success:
            try:
                from .security.safe_exec import safe_exec
                scope: dict = {}
                safe_exec(rep.synthesized_code, scope, filename="<candidate>")
                cand_fn = scope.get("binary_search") or scope.get("find_in_sorted")
                if cand_fn and callable(cand_fn):
                    from .synthesis.differential_oracle import (
                        find_counterexamples,
                        reference_binary_search,
                        sorted_unique_search_gen,
                    )
                    ces = find_counterexamples(
                        cand_fn,
                        reference_binary_search,
                        sorted_unique_search_gen,
                        n=500,
                        seed=42,
                    )
                    passed_hidden = 500 - len(ces)
                    hidden = (passed_hidden, 500)
                else:
                    hidden_probes = engine.generate_hidden_invariant_probes(src)
                    if hidden_probes:
                        hp_passed = 0
                        for probe in hidden_probes:
                            th = f"{rep.synthesized_code}\n\n{probe}"
                            ok, _, _ = HermeticExecutionSandbox.execute_isolated(th, timeout_sec=2.0)
                            if ok:
                                hp_passed += 1
                        hidden = (hp_passed, len(hidden_probes))
            except Exception:
                pass

        # 5. Render repair terminal report
        report_output = render_repair(
            buggy_src=src,
            fixed_src=rep.synthesized_code if rep.success else src,
            filename=args.file.name,
            suspects=suspects,
            visible=visible,
            hidden=hidden,
            seconds=rep.duration_ms / 1000.0,
            candidates=rep.total_candidates_explored,
        )
        print(report_output)

        if rep.success:
            print("\n--- SYNTHESIZED REPAIRED CODE ---")
            print(rep.synthesized_code)
            print("==========================================================")
        return 0 if rep.success else 1

    # Command 40: Solomonoff Algorithmic Prior
    if args.command == "solomonoff":
        from .search.solomonoff_prior import SolomonoffPriorEngine
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        engine = SolomonoffPriorEngine()
        rep = engine.evaluate_program(src)
        print("==========================================================")
        print("   🧠 SOLOMONOFF UNIVERSAL PRIOR & ALGORITHMIC COMPLEXITY   ")
        print("==========================================================")
        print(f"  Target File:     {args.file}")
        print(f"  Character Count: {rep.raw_character_count}")
        print(f"  LZW Tokens:      {rep.lzw_token_count}")
        print(f"  Compressed Bits: {rep.compressed_bits}")
        print(f"  Compression:     {rep.compression_ratio * 100:.1f}%")
        print(f"  AST Entropy:     {rep.ast_shannon_entropy:.4f} bits/symbol")
        print(f"  Solomonoff Prior:{rep.solomonoff_prior_score:.6f} (Occam Likelihood)")
        print(f"  Kolmogorov Bound:<= {rep.kolmogorov_upper_bound} bits")
        print("==========================================================\n")
        return 0

    # Command 41: Bug Reproduction Oracle (Agentless-style)
    if args.command == "oracle":
        from .claude_engine.oracle_synthesizer import BugReproductionOracle
        issue_p = Path(args.issue)
        issue_text = issue_p.read_text(encoding="utf-8") if issue_p.exists() else args.issue
        spec = BugReproductionOracle.parse_issue(issue_text)
        print("==========================================================")
        print("   🔍 AUTONOMOUS BUG REPRODUCTION ORACLE (AGENTLESS)      ")
        print("==========================================================")
        print(f"  Target File:     {spec.target_file or 'Unknown'}")
        print(f"  Target Symbol:   {spec.target_symbol or 'Unknown'}")
        print(f"  Exception Type:  {spec.exception_type or 'None Detected'}")
        print("----------------------------------------------------------")
        print("Generated reproduce_issue.py:\n")
        print(spec.reproduction_code)
        if args.verify:
            print("\nExecuting oracle against current directory...")
            ok, code, stdout, stderr = BugReproductionOracle.execute_oracle(spec.reproduction_code)
            status_str = "SUCCESS (Bug Resolved)" if ok else f"CRASH / DEFECT REPRODUCED (code {code})"
            print(f"  Execution Status: {status_str}")
            if stdout:
                print(f"  Output: {stdout.strip()}")
            if stderr:
                print(f"  Error:  {stderr.strip()}")
        print("==========================================================\n")
        return 0

    # Command 42: Surgical AST Symbol Navigator (AutoCodeRover-style)
    if args.command == "ast-nav":
        from .claude_engine.ast_navigator import ASTSymbolNavigator
        nav = ASTSymbolNavigator(args.dir)
        matches = nav.search_function(args.query) + nav.search_class(args.query) + nav.search_method(args.query)
        print("==========================================================")
        print("   🧭 SURGICAL AST SYMBOL NAVIGATOR (AUTOCODEROVER)       ")
        print("==========================================================")
        print(f"  Query:           {args.query}")
        print(f"  Search Root:     {args.dir.resolve()}")
        print(f"  Matches Found:   {len(matches)}")
        print("----------------------------------------------------------")
        if not matches:
            print("  No symbols found matching query.")
        for idx, m in enumerate(matches, 1):
            print(f"  {idx}. [{m.kind.upper()}] {m.name}")
            print(f"     Location:   {m.file_path}:{m.lineno}-{m.end_lineno}")
            if m.parameters:
                print(f"     Parameters: ({', '.join(m.parameters)})")
            if m.docstring:
                print(f"     Docstring:  {m.docstring.strip()[:60]}...")
            hier = nav.get_call_hierarchy(m.name)
            if hier.callees:
                print(f"     Calls:      {', '.join(hier.callees[:5])}")
        print("==========================================================\n")
        return 0

    # Command 43: Cognitive Memory Stream (claude-mem style)
    if args.command == "memo-sync":
        from .claude_engine.cognitive_memory import CognitiveMemoryStream
        stream = CognitiveMemoryStream()
        print("==========================================================")
        print("   🧠 COGNITIVE MEMORY STREAM & KNOWLEDGE GRAPH           ")
        print("==========================================================")
        print(f"  Storage Path:    {stream.storage_path}")
        print(f"  Total Records:   {len(stream._records)}")
        if args.search:
            print(f"  Search Query:    {args.search}")
            hits = stream.search(args.search, top_k=3)
            for idx, h in enumerate(hits, 1):
                print(f"    {idx}. [{h.category.upper()}] {h.title} (conf: {h.confidence * 100:.0f}%)")
                print(f"       {h.description}")
        if args.export_claude_md:
            stream.synthesize_claude_md(args.export_claude_md)
            print(f"  [OK] Exported cache-optimized CLAUDE.md to: {args.export_claude_md}")
        print("==========================================================\n")
        return 0

    # Command 44: Mini-SWE ACI
    if args.command == "mini-swe":
        from .claude_engine.mini_swe_aci import MiniSWEAgentACI
        issue_p = Path(args.issue)
        issue_text = issue_p.read_text(encoding="utf-8") if issue_p.exists() else args.issue
        aci = MiniSWEAgentACI(args.workspace)
        print("==========================================================")
        print("   ⚡ MINI-SWE AGENT-COMPUTER INTERFACE (ACI)            ")
        print("==========================================================")
        res = aci.solve_issue_loop(issue_text)
        print(f"  Defect Reproduced on Baseline: {res['defect_reproduced']}")
        print(f"  Target File:                   {res['target_file']}")
        print(f"  Target Symbol:                 {res['target_symbol']}")
        if res.get('symbol_context'):
            print(f"  Symbol Context:\n{res['symbol_context']}")
        print("==========================================================\n")
        return 0

    # Command 45: Semantic Code Ontology (NVIDIA auto-ontology style)
    if args.command == "ontology":
        from .ontology.code_ontology import CodeOntologyEngine
        engine = CodeOntologyEngine()
        target_p = Path(args.path)
        if target_p.is_file():
            engine.index_source(str(target_p), target_p.read_text(encoding="utf-8"))
        elif target_p.is_dir():
            for root, _, files in os.walk(target_p):
                for f in files:
                    if f.endswith(".py"):
                        fp = Path(root) / f
                        engine.index_source(str(fp), fp.read_text(encoding="utf-8", errors="replace"))
        print("==========================================================")
        print("   🕸️  SEMANTIC CODE ONTOLOGY & REASONING LAYER          ")
        print("==========================================================")
        print(f"  Target:          {args.path}")
        print(f"  Total Entities:  {len(engine.entities)}")
        print(f"  Total Relations: {len(engine.relations)}")
        if args.check_invariants:
            violations = engine.check_invariants()
            print(f"  Violations:      {len(violations)}")
            for v in violations:
                print(f"    [{v.severity}] {v.rule_id}: {v.message}")
                print(f"      Recommendation: {v.recommendation}")
        if args.impact:
            impact = engine.explain_impact(args.impact)
            print(f"  Impact Analysis for '{args.impact}':")
            print(f"    Blast Radius Count: {impact['transitive_impact_count']}")
            print(f"    Impacted Layers:    {', '.join(impact['impacted_layers'])}")
            print(f"    High Blast Radius:  {impact['is_high_blast_radius']}")
        if getattr(args, "hr_audit", False):
            from .ontology.enterprise_auto_ontology import EnterpriseAutoOntology
            ent_onto = EnterpriseAutoOntology()
            # Register typical HR organizational schema
            ent_onto.register_table("employees", [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
                {"name": "salary", "type": "REAL"},
                {"name": "department_id", "type": "INTEGER"},
                {"name": "manager_id", "type": "INTEGER"},
            ])
            ent_onto.register_table("departments", [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
            ])
            ent_onto.infer_semantic_foreign_keys()
            audit_res = ent_onto.hr_workforce_analytics_audit()
            print("----------------------------------------------------------")
            print("   👥 ENTERPRISE HR & PEOPLE ANALYTICS AUDIT              ")
            print("----------------------------------------------------------")
            print(f"  HR Schema Ready:          {audit_res['hr_schema_ready']}")
            print(f"  Span of Control Enabled:  {audit_res['span_of_control_supported']}")
            print(f"  PII Governed Columns:     {audit_res['pii_governed_columns']}")
            for ins in audit_res['hr_diagnostic_insights']:
                print(f"  - {ins}")
        if getattr(args, "query", None):
            from .ontology.enterprise_auto_ontology import EnterpriseAutoOntology
            ent_onto = EnterpriseAutoOntology()
            ent_onto.register_table("employees", [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
                {"name": "salary", "type": "REAL"},
                {"name": "department_id", "type": "INTEGER"},
                {"name": "manager_id", "type": "INTEGER"},
            ])
            ent_onto.register_table("departments", [
                {"name": "id", "type": "INTEGER", "is_pk": True},
                {"name": "name", "type": "TEXT"},
            ])
            ent_onto.infer_semantic_foreign_keys()
            plan = ent_onto.generate_nl_query_plan(args.query)
            print("----------------------------------------------------------")
            print(f"   💬 NL-TO-SQL QUERY: \"{args.query}\"")
            print("----------------------------------------------------------")
            print(plan.sql)
            print("\n  Provenance Trace:")
            for tr in plan.provenance_trace:
                print(f"    - {tr}")
        print("==========================================================\n")
        return 0

    # Command 46: Spec-Driven Development Engine (github/spec-kit style)
    if args.command == "sdd":
        from .spec.sdd_engine import SDDEngine
        spec_text = Path(args.spec).read_text(encoding="utf-8")
        spec = SDDEngine.parse_spec_text(spec_text)
        print("==========================================================")
        print("   📐 SPEC-DRIVEN DEVELOPMENT (SDD) CONTRACT ENGINE       ")
        print("==========================================================")
        print(f"  Spec Name:       {spec.name} (v{spec.version})")
        print(f"  Requirements:    {len(spec.requirements)}")
        for r in spec.requirements:
            print(f"    - {r.req_id}: {r.title} -> {r.target_function}()")
        if args.gen_tests:
            suite = SDDEngine.generate_contract_test_suite(spec, args.gen_tests)
            out_file = f"test_{spec.name.lower()}_contracts.py"
            Path(out_file).write_text(suite, encoding="utf-8")
            print(f"  [OK] Generated contract test suite: {out_file}")
        if args.validate:
            rep = SDDEngine.validate_spec_compliance(spec, args.validate)
            print(f"  Compliance Score: {rep.compliance_score * 100:.1f}% ({rep.passed_requirements}/{rep.total_requirements} Pass)")
        print("==========================================================\n")
        return 0

    # Command 47: Worktree Trunk (max-sixty/worktrunk style)
    if args.command == "worktrunk":
        from .git_engine.worktrunk import WorktrunkEngine
        trunk = WorktrunkEngine()
        print("==========================================================")
        print("   🌿 PARALLEL AGENT GIT WORKTREE TRUNK                   ")
        print("==========================================================")
        if args.allocate:
            sess = trunk.allocate_worktree(args.allocate)
            print(f"  [OK] Allocated worktree for '{args.allocate}' at: {sess.worktree_path}")
            print(f"  Branch: {sess.branch_name}")
        elif args.prune:
            trunk.prune_worktree(args.prune)
            print(f"  [OK] Pruned worktree for agent: {args.prune}")
        elif args.cleanup_all:
            cnt = trunk.cleanup_all()
            print(f"  [OK] Cleaned up {cnt} active agent worktrees.")
        else:
            active = trunk.list_active_worktrees()
            print(f"  Active Worktrees: {len(active)}")
            for a in active:
                print(f"    - Agent '{a.agent_id}': {a.worktree_path} ({a.branch_name})")
        print("==========================================================\n")
        return 0

    # Command 48: Startup Executive Review (inspired by gstack)
    if args.command == "executive":
        from .swarm.executive_stack import ExecutiveStackOrchestrator
        diff_content = ""
        if args.diff:
            diff_p = Path(args.diff)
            diff_content = diff_p.read_text(encoding="utf-8") if diff_p.exists() else args.diff
        consensus = ExecutiveStackOrchestrator.evaluate_proposal(args.title, args.desc, diff_content)
        print("==========================================================")
        print("   👔 STARTUP EXECUTIVE LEADERSHIP REVIEW (GSTACK STYLE)   ")
        print("==========================================================")
        print(f"  Proposal:        {args.title}")
        print(f"  Suggested Bump:  {consensus.suggested_semver}")
        print(f"  Aggregate Score: {consensus.aggregate_score:.1f}/10.0")
        print(f"  Unanimous:       {'YES (APPROVED FOR MERGE)' if consensus.unanimous_approval else 'NO (CHANGES REQUESTED)'}")
        print("----------------------------------------------------------")
        for v in consensus.verdicts:
            mark = "✅" if v.approved else "❌"
            print(f"  {mark} {v.role} ({v.score:.1f}/10): {v.summary}")
            for act in v.action_items:
                print(f"     Action Item: {act}")
        print("==========================================================\n")
        return 0

    # Command 49: Worktrunk Interactive Git Worktree Matrix (max-sixty/worktrunk style - Image 1)
    if args.command == "wt":
        from .git_engine.worktrunk_advanced import WorktrunkAdvancedEngine
        engine = WorktrunkAdvancedEngine(Path("."))
        sub = getattr(args, "subaction", "list") or "list"
        if sub == "list":
            table = engine.render_table(full=args.full)
            print(table)
            return 0
        elif sub == "switch":
            if not args.branch:
                print("Error: Target branch required for 'switch'")
                return 1
            path = engine.switch_worktree(args.branch)
            print(f"Switched to worktree for {args.branch} @ {path}")
            return 0
        elif sub == "add":
            if not args.branch:
                print("Error: Target branch required for 'add'")
                return 1
            path = engine.add_worktree(args.branch)
            print(f"Created worktree for {args.branch} @ {path}")
            return 0
        elif sub == "remove":
            target = args.branch
            succ = engine.remove_worktree(target)
            if succ:
                print(f"Removed worktree {target or 'active'}")
                return 0
            else:
                print(f"Failed to remove worktree {target or 'active'}")
                return 1

    # Command 50: Interactive Claude Code Style Terminal Console (Image 3)
    if args.command == "console":
        from .ui.apex_console import ApexInteractiveConsole
        console = ApexInteractiveConsole(workspace_dir=".")
        console.mascot_style = getattr(args, "mascot", "falcon")
        console.mascot_theme = getattr(args, "theme", "gold")
        console.launch()
        return 0

    # Command 51: MLflow Agent Tracing & OpenTelemetry Exporter
    if args.command == "mlflow-trace":
        from .mlflow_engine.tracer import AgentTracer
        tracer = AgentTracer(session_name=args.session)
        with tracer.span("apex_council_root_turn", attributes={"agent": "Apex-Council-Supreme", "framework": "Pure-Python"}) as span:
            span.attributes["council_members"] = "Gemini-Pro,Claude-Opus,GPT-4o"
            span.attributes["status"] = "ACTIVE"
        print("==========================================================")
        print("   🔍 MLFLOW & OPENTELEMETRY AGENT TRACER                 ")
        print("==========================================================")
        print(f"  Session Name:    {args.session}")
        print(f"  Spans Recorded:  {len(tracer.spans)}")
        print(f"  Trace ID:        {tracer.trace_id}")
        if getattr(args, "export_json", None):
            tracer.export_json(args.export_json)
            print(f"  [OK] Exported OpenTelemetry trace to: {args.export_json}")
        else:
            print("  Trace Summary:   Valid OpenTelemetry GenAI span tree initialized.")
        print("==========================================================\n")
        return 0

    # Command 52: MLflow LLM Judge Evaluation
    if args.command == "mlflow-eval":
        from .mlflow_engine.evaluator import LLMJudgeEvaluator
        target_path = Path(args.file)
        if not target_path.exists():
            print(f"Error: Target file not found: {target_path}")
            return 1
        code_content = target_path.read_text(encoding="utf-8", errors="replace")
        evaluator = LLMJudgeEvaluator()
        result = evaluator.evaluate_code(prompt=args.prompt, generated_code=code_content)
        print("==========================================================")
        print("   ⚖️ MLFLOW LLM-AS-A-JUDGE EVALUATION REPORT             ")
        print("==========================================================")
        print(f"  Target File:     {target_path}")
        print(f"  Evaluation Prompt: {args.prompt}")
        print(f"  Verdict:         {'PASSED' if result.passed else 'FAILED'}")
        print(f"  Overall Score:   {result.overall_score * 100:.1f}%")
        print("----------------------------------------------------------")
        for m in result.metrics:
            status_icon = "PASS" if m.passed else "FAIL"
            print(f"  [{status_icon}] {m.name:<25} ({m.score * 100:>5.1f}%)")
            print(f"         {m.rationale}")
        print("==========================================================\n")
        return 0 if result.passed else 1

    # Command 53: OmO Dual-Pane Live DAG & Task Visualizer (Image 1)
    if args.command == "omo":
        from .omo.dag_compiler import DagCompiler, DagNodeInput
        from .omo.dag_executor import DagExecutor
        from .omo.dag_tui import DagTuiRenderer
        nodes = [
            DagNodeInput(id="navigation", prompt="Map shell navigation", category="quick", label="navigation"),
            DagNodeInput(id="gate-wiring", prompt="Wire linear gate verification", category="quick", label="gate-wiring"),
            DagNodeInput(id="test-coverage", prompt="Run unit and integration coverage", category="quick", label="test-coverage"),
            DagNodeInput(id="verify-evidence", prompt="Verify attestation signatures and evidence", category="quick", label="verify-evidence", depends_on=["navigation", "gate-wiring", "test-coverage"]),
        ]
        res = DagCompiler.compile(nodes)
        executor = DagExecutor(res)
        telemetry = executor.execute_all()
        tui = DagTuiRenderer.render_full_screen(
            dag_result=res,
            telemetry=telemetry,
            task_title=getattr(args, "task", "Linear gates integration evidence 1/1"),
            run_id=getattr(args, "run_id", "01a97526"),
        )
        print("\n" + tui + "\n")
        return 0

    # Command 54: Task DAG Compilation & Scheduling Analysis
    if args.command == "dag":
        from .omo.dag_compiler import DagCompiler, DagNodeInput
        nodes = [
            DagNodeInput(id="arch-spec", prompt="Specify architectural boundaries", category="planning"),
            DagNodeInput(id="tdd-tests", prompt="Synthesize property test harnesses", category="testing", depends_on=["arch-spec"]),
            DagNodeInput(id="impl-core", prompt="Implement sovereign core logic", category="coding", depends_on=["arch-spec"]),
            DagNodeInput(id="gatekeeper", prompt="Verify Merkle attestation & PEP-578 hooks", category="security", depends_on=["tdd-tests", "impl-core"]),
        ]
        res = DagCompiler.compile(nodes)
        print("==========================================================")
        print("          🕸️ APEX: OMO TASK DAG WAVE GRAPH                ")
        print("==========================================================")
        print(f"  Valid DAG:       {'YES (Topologically Sorted)' if res.ok else 'NO'}")
        print(f"  Total Nodes:     {len(res.nodes)}")
        print(f"  Total Waves:     {len(res.waves)}")
        print(f"  Critical Path:   {' -> '.join(res.critical_path)}")
        print(f"  Bottlenecks:     {', '.join(res.bottlenecks) if res.bottlenecks else 'None'}")
        print("----------------------------------------------------------")
        for wave in res.waves:
            print(f"  Wave {wave.index} (Parallel Barrier Execution):")
            for nid in wave.node_ids:
                node = next(n for n in res.nodes if n.id == nid)
                deps_str = f"(depends on: {', '.join(node.depends_on)})" if node.depends_on else "(root node)"
                print(f"    • [{node.route.value}] {node.id:<16} {deps_str}")
        print("==========================================================\n")
        return 0 if res.ok else 1

    # Command 55: Garry Tan gstack Virtual Engineering Team Suite
    if args.command == "gstack":
        from .gstack.office_hours import GarryTanOfficeHoursEngine
        from .gstack.cso_audit import ChiefSecurityOfficerEngine
        from .gstack.pre_landing_review import PreLandingReviewEngine
        from .gstack.ship_engine import ReleaseShippingEngine
        from .gstack.gstack_orchestrator import GStackOrchestrator
        from .ui.mascot import MascotRenderer, ApexAgentPersona

        action = args.action
        target_code = ""
        target_path = getattr(args, "diff", None) or args.target
        if target_path and Path(target_path).exists():
            target_code = Path(target_path).read_text(encoding="utf-8", errors="replace")
        elif getattr(args, "diff", None):
            target_code = args.diff

        if action == "office-hours":
            idea = args.target or "Build an autonomous AI developer agent that out-thinks existing coding tools"
            plan = GarryTanOfficeHoursEngine.conduct_session(idea)
            print("\n" + MascotRenderer.render_agent_speech(
                persona=ApexAgentPersona.COMMANDER,
                speech_lines=[
                    f'"{plan.painkiller_verdict}: Ruthlessly targeting high customer pain."',
                    f'"Moat: {plan.defensible_moat[:65]}..."',
                    f'"Trimmed {len(plan.scope_cuts)} non-essential distraction features for v1."',
                ],
                status_tag="STRATEGIC FOUNDER REVIEW"
            ) + "\n")
            print("==========================================================")
            print(f"   👔 STARTUP FOUNDER OFFICE HOURS DESIGN DOC             ")
            print("==========================================================")
            print(plan.design_doc_markdown)
            print("==========================================================\n")
            return 0

        elif action == "cso":
            source = target_code or "import os\nos.system('echo test')\n"
            report = ChiefSecurityOfficerEngine.audit_code(source, target_name=args.target or "workspace")
            print("\n" + MascotRenderer.render_agent_speech(
                persona=ApexAgentPersona.SENTINEL,
                speech_lines=[
                    f'"OWASP Top 10 & STRIDE Threat Audit: Score {report.security_score:.1f}/10.0"',
                    f'"Status: {"PASSED" if report.passed else "BLOCKED - THREATS FOUND"}"',
                    f'"Detected {len(report.findings)} security threat vectors."',
                ],
                status_tag="CSO SECURITY DEFENSE"
            ) + "\n")
            print("==========================================================")
            print("   🛡️ CHIEF SECURITY OFFICER (CSO) STRIDE AUDIT REPORT     ")
            print("==========================================================")
            print(f"  Target:          {report.target_name}")
            print(f"  Security Score:  {report.security_score:.1f}/10.0")
            print(f"  Verdict:         {'PASSED' if report.passed else 'BLOCKED'}")
            print("----------------------------------------------------------")
            for f in report.findings:
                print(f"  [{f.severity}] {f.stride_category} ({f.owasp_top10}) line {f.line_number or '?'}:")
                print(f"       {f.description}")
                print(f"       Remediation: {f.remediation}")
            print("==========================================================\n")
            return 0 if report.passed else 1

        elif action == "review":
            source = target_code or "def solve():\n    # TODO: implement later\n    pass\n"
            files = [args.target] if args.target and not Path(args.target).exists() else ([args.target] if args.target else ["app.py"])
            rev = PreLandingReviewEngine.review_diff(files, source)
            print("\n" + MascotRenderer.render_agent_speech(
                persona=ApexAgentPersona.NINJA,
                speech_lines=[
                    f'"Pre-Landing Gate [{rev.pr_type.upper()}]: Score {rev.score:.1f}/10.0"',
                    f'"Found {len(rev.issues)} items across checklists."',
                    f'"Verdict: {"CLEARED FOR LANDING" if rev.passed else "CHANGES REQUIRED"}"',
                ],
                status_tag="PRE-LANDING GATEKEEPER"
            ) + "\n")
            print("==========================================================")
            print(f"   🔍 GSTACK PRE-LANDING REVIEW: [{rev.pr_type.upper()}]      ")
            print("==========================================================")
            print(f"  Score:           {rev.score:.1f}/10.0")
            print(f"  Status:          {'PASSED' if rev.passed else 'BLOCKED'}")
            print("  Checklist:")
            for chk, ok in rev.checklist_status.items():
                mark = "✓" if ok else "✗"
                print(f"    {mark} {chk}")
            if rev.issues:
                print("----------------------------------------------------------")
                for iss in rev.issues:
                    print(f"  [{iss.severity}] {iss.category} at line {iss.line_number or '?'}: {iss.message}")
                    print(f"       Fix: {iss.suggested_fix}")
            print("==========================================================\n")
            return 0 if rev.passed else 1

        elif action == "ship":
            bump_choice = None if args.bump == "auto" else args.bump
            commits = [args.target] if args.target else ["feat: implement sovereign gstack virtual engineering team"]
            ship = ReleaseShippingEngine.prepare_shipment(
                current_version="v0.9.0",
                commit_messages=commits,
                diff_summary=target_code,
                force_bump=bump_choice,
            )
            print("\n" + MascotRenderer.render_agent_speech(
                persona=ApexAgentPersona.NINJA,
                speech_lines=[
                    f'"Ship clearance approved: Bump {ship.version_bump} -> {ship.new_version}"',
                    f'"Generated Keep-a-Changelog release entry."',
                    f'"PR Title: {ship.pr_title[:60]}"',
                ],
                status_tag="RELEASE SHIPPING"
            ) + "\n")
            print("==========================================================")
            print("   🚀 AUTONOMOUS RELEASE ENGINEERING SHIP RECEIPT         ")
            print("==========================================================")
            print(f"  PR Title:        {ship.pr_title}")
            print(f"  Version:         {ship.new_version} ({ship.version_bump})")
            print("----------------------------------------------------------")
            print(ship.pr_body_markdown)
            print("==========================================================\n")
            return 0

        elif action == "autoplan":
            prompt = args.target or "Build autonomous distributed key-value store"
            source = target_code or "class DistributedKV:\n    pass\n"
            res = GStackOrchestrator.run_full_pipeline(prompt, ["store.py"], source)
            print("\n" + "\n\n".join(res.transcript_speeches) + "\n")
            print("==========================================================")
            print(f"   🌟 GSTACK AUTOPLAN SPRINT REPORT                       ")
            print("==========================================================")
            print(f"  Overall Status:  {'PASSED & READY TO SHIP' if res.passed else 'BLOCKED'}")
            print(f"  CSO Security:    {res.cso_report.security_score:.1f}/10.0")
            print(f"  Pre-Landing:     {res.pre_landing.score:.1f}/10.0")
            if res.ship_receipt:
                print(f"  Shipment Bump:   {res.ship_receipt.new_version} ({res.ship_receipt.version_bump})")
            print("==========================================================\n")
            return 0 if res.passed else 1

    # Command 56: GBrain Persistent Memory (garrytan/gbrain)
    if args.command == "gbrain":
        from .gbrain.brain import GBrainEngine
        from .ui.mascot import MascotRenderer, ApexAgentPersona

        engine = GBrainEngine()
        action = args.action
        params = args.params

        if action == "store":
            if len(params) < 2:
                print("Usage: apex gbrain store <key> <fact_text>")
                return 1
            key, text = params[0], " ".join(params[1:])
            fact_id = engine.store_fact(key, text, source=args.source, tags=args.tags)
            print(f"\n[GBRAIN] Fact #{fact_id} stored successfully: '{key}' -> '{text}'\n")
            return 0

        elif action == "recall":
            query = " ".join(params) if params else ""
            facts = engine.recall_facts(query)
            print(f"\n==========================================================")
            print(f"   🧠 GBRAIN PERSISTENT MEMORY RECALL: '{query}'          ")
            print(f"==========================================================")
            if not facts:
                print("  No relevant facts found.")
            for f in facts:
                print(f"  [#{f.fact_id}] ({f.key}) {f.text}")
                print(f"       Tags: {f.tags} | Confidence: {f.confidence} | Source: {f.source}")
            print("==========================================================\n")
            return 0

        elif action == "correct":
            if len(params) < 2:
                print("Usage: apex gbrain correct <fact_id> <new_text>")
                return 1
            fact_id = int(params[0])
            new_text = " ".join(params[1:])
            ok = engine.correct_fact(fact_id, new_text)
            print(f"\n[GBRAIN] Fact #{fact_id} correction: {'Success' if ok else 'Not Found'}\n")
            return 0 if ok else 1

        elif action == "withdraw":
            if not params:
                print("Usage: apex gbrain withdraw <fact_id>")
                return 1
            fact_id = int(params[0])
            ok = engine.withdraw_fact(fact_id)
            print(f"\n[GBRAIN] Fact #{fact_id} withdrawn: {'Success' if ok else 'Not Found'}\n")
            return 0 if ok else 1

        elif action == "lock":
            if len(params) < 2:
                print("Usage: apex gbrain lock <lock_name> <session_id>")
                return 1
            lock_name, session_id = params[0], params[1]
            ok = engine.acquire_lock(lock_name, session_id)
            print(f"\n[GBRAIN] Lock '{lock_name}' for session '{session_id}': {'ACQUIRED' if ok else 'LOCKED BY OTHER'}\n")
            return 0 if ok else 1

    # Command 57: Scrapling Resilient Web Scraper (D4Vinci/Scrapling)
    if args.command == "scrape":
        from .scrapling.scraper import ScraplingEngine
        engine = ScraplingEngine()
        target = args.target

        print(f"\n[SCRAPLING] Scraping target: {target}...")
        res = engine.scrape(target)

        print("\n==========================================================")
        print(f"   🕷️  SCRAPLING EXTRACTION REPORT                        ")
        print("==========================================================")
        print(f"  Status:       {res.status_code}")
        print(f"  Title:        {res.title}")
        print(f"  Text Length:  {len(res.text)} characters")
        print("----------------------------------------------------------")
        if args.tables:
            tables = res.extract_tables()
            print(f"  Extracted Tables: {len(tables)}")
            for idx, tbl in enumerate(tables, 1):
                print(f"  --- Table #{idx} ({len(tbl)} rows) ---")
                for row in tbl[:5]:
                    print(f"    {row}")
        else:
            print(res.html_to_markdown()[:1200])
        print("==========================================================\n")
        return 0

    # Command 58: Floci AWS Local Cloud Emulator (floci-io/floci)
    if args.command == "floci":
        from .cloud.floci_emulator import FlociCloudEmulator
        floci = FlociCloudEmulator()
        service = args.service
        action = args.action
        params = args.params

        if service == "stats":
            stats = floci.get_cloud_stats()
            print("\n==========================================================")
            print("   ☁️  FLOCI LOCAL AWS CLOUD EMULATOR STATS               ")
            print("==========================================================")
            for k, v in stats.items():
                print(f"  {k:28}: {v}")
            print("==========================================================\n")
            return 0

        elif service == "s3":
            if action == "put":
                if len(params) < 3:
                    print("Usage: apex floci s3 put <bucket> <key> <data>")
                    return 1
                b, k, d = params[0], params[1], " ".join(params[2:])
                obj = floci.s3_put_object(b, k, d)
                print(f"[FLOCI-S3] Object put: s3://{b}/{k} (Size: {obj.size} bytes, ETag: {obj.etag})")
                return 0
            elif action == "list":
                b = params[0] if params else "apex-bucket"
                objs = floci.s3_list_objects(b)
                print(f"\n[FLOCI-S3] Bucket s3://{b} objects ({len(objs)} total):")
                for o in objs:
                    print(f"  - {o['Key']} ({o['Size']} bytes)")
                return 0

        elif service == "sqs":
            if action == "send":
                if len(params) < 2:
                    print("Usage: apex floci sqs send <queue> <message>")
                    return 1
                q, m = params[0], " ".join(params[1:])
                msg_id = floci.sqs_send_message(q, m)
                print(f"[FLOCI-SQS] Message sent to '{q}': {msg_id}")
                return 0
            elif action == "receive":
                q = params[0] if params else "apex-queue"
                msgs = floci.sqs_receive_messages(q)
                print(f"\n[FLOCI-SQS] Received {len(msgs)} messages from '{q}':")
                for m in msgs:
                    print(f"  [{m.message_id}] {m.body}")
                return 0

        elif service == "dynamo":
            if action == "put":
                if len(params) < 2:
                    print("Usage: apex floci dynamo put <table> <id> [field=val...]")
                    return 1
                tbl, item_id = params[0], params[1]
                item_dict = {"id": item_id}
                for f in params[2:]:
                    if "=" in f:
                        k, v = f.split("=", 1)
                        item_dict[k] = v
                floci.dynamo_put_item(tbl, item_dict)
                print(f"[FLOCI-DYNAMO] PutItem into '{tbl}': {item_dict}")
                return 0
            elif action == "get":
                if len(params) < 2:
                    print("Usage: apex floci dynamo get <table> <id>")
                    return 1
                tbl, item_id = params[0], params[1]
                item = floci.dynamo_get_item(tbl, item_id)
                print(f"[FLOCI-DYNAMO] GetItem from '{tbl}': {item}")
                return 0

        print(f"Service/Action combination '{service} {action}' executed.")
        return 0

    # Command 59: VibeVoice Frontier Acoustic Synthesizer (microsoft/VibeVoice)
    if args.command == "voice":
        from .voice.vibe_voice import VibeVoiceSynthesizer, COUNCIL_VOICE_PROFILES
        from .ui.mascot import MascotRenderer, ApexAgentPersona

        synth = VibeVoiceSynthesizer()
        persona = args.persona
        text = args.text
        out_wav = args.output

        raw_bytes, path = synth.synthesize_speech(text, profile_name=persona, output_wav_path=out_wav)
        profile = COUNCIL_VOICE_PROFILES[persona]

        persona_map = {
            "falcon": ApexAgentPersona.COMMANDER,
            "guardian": ApexAgentPersona.ARCHITECT,
            "aegis": ApexAgentPersona.SENTINEL,
            "ninja": ApexAgentPersona.NINJA,
        }

        print("\n" + MascotRenderer.render_agent_speech(
            persona=persona_map[persona],
            speech_lines=[
                f'"{text}"',
                f'Synthesized Broadcast WAV: {path}',
                f'Profile: {profile.description} ({profile.base_freq}Hz)',
            ],
            status_tag="VIBEVOICE ACOUSTIC CADENCE"
        ) + "\n")
        return 0

    # Command 60: Garden Skills Registry (ConardLi/garden-skills & google/skills)
    if args.command == "skills":
        from .skills.garden_registry import GardenSkillsRegistry
        reg = GardenSkillsRegistry()
        action = args.action

        if action == "list":
            skills = reg.list_skills(tag=args.tag)
            print("\n==========================================================")
            print(f"   🌱 APEX GARDEN SKILLS REGISTRY ({len(skills)} Available)      ")
            print("==========================================================")
            for s in skills:
                print(f"  • {s['name']:22} (v{s['version']}) by {s['author']}")
                print(f"    {s['description']}")
                print(f"    Tags: {', '.join(s['tags'])}")
            print("==========================================================\n")
            return 0

        elif action == "run":
            if not args.name:
                print("Usage: apex skills run <skill_name>")
                return 1
            res = reg.execute_skill(args.name)
            print(f"\n[GARDEN-SKILLS] Execution result for '{args.name}':")
            if res.get("success"):
                print(res.get("compiled_prompt", res.get("result")))
            else:
                print(f"Error: {res.get('error')}")
            return 0 if res.get("success") else 1

    # Command 61: Agent Browser Automation (vercel-labs/agent-browser)
    if args.command == "browser":
        from .browser.agent_browser import AgentBrowserSession
        sess = AgentBrowserSession()
        action = args.action
        target = args.url

        sess.goto(target)

        if action == "goto":
            print(f"[BROWSER] Navigated to {target}. Total accessible elements: {len(sess.nodes_by_ref)}")
            return 0
        elif action == "snapshot":
            print("\n" + sess.snapshot() + "\n")
            return 0
        elif action == "extract":
            print("\n" + sess.extract_text() + "\n")
            return 0
        elif action == "viewport":
            print("\n" + sess.render_ascii_viewport() + "\n")
            return 0

    # Command 62: Electron Desktop Shell Bridge (electron/electron)
    if args.command == "electron":
        from .ui.electron_bridge import generate_electron_scaffold, ElectronBridgeServer
        action = args.action

        if action == "scaffold":
            files = generate_electron_scaffold(args.dir)
            print(f"\n==========================================================")
            print(f"   ⚡ APEX ELECTRON DESKTOP SHELL GENERATED               ")
            print("==========================================================")
            print(f"  Target Directory: {args.dir}")
            for f in files:
                print(f"  ✓ {f}")
            print("\n  Launch via: cd electron && npm install && npm start\n")
            print("==========================================================\n")
            return 0

        elif action == "bridge":
            bridge = ElectronBridgeServer(port=args.port)
            bound_port = bridge.start_background()
            print(f"\n[ELECTRON-BRIDGE] Apex IPC Bridge listening on http://127.0.0.1:{bound_port}")
            print("[ELECTRON-BRIDGE] Press Ctrl+C to terminate bridge session.\n")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                bridge.stop()
                print("[ELECTRON-BRIDGE] Stopped bridge.")
            return 0

    # Command 63: REA (Reverse Engineering Anything)
    if args.command == "rea":
        from .rea import inspect_artifact, disassemble_source, EvidenceLedger
        import json

        # Ledger verification action
        if getattr(args, "verify_ledger", False):
            ledger_file = getattr(args, "ledger_file", None)
            ledger = EvidenceLedger(ledger_file=ledger_file)
            valid, count, msg = ledger.verify_chain()
            if valid:
                print(f"\n✓ REA EVIDENCE CHAIN VERIFIED: {count} cryptographic blocks intact and tamper-free.\n")
                return 0
            else:
                print(f"\n✗ REA EVIDENCE CHAIN BREACH: {msg}\n")
                return 1

        target = getattr(args, "target_file", None) or getattr(args, "target", None)
        if not target:
            sys.stderr.write("Error: Please specify target artifact path or --verify-ledger.\n")
            return 2

        target_path = Path(target)
        if not target_path.exists():
            sys.stderr.write(f"Error: Target artifact not found: {target_path}\n")
            return 2

        print(f"\n[APEX-REA] Inspecting artifact: {target_path}...")
        inspection = inspect_artifact(target_path)
        disasm_res = None
        evidence_rec = None

        if getattr(args, "disasm", False) or target_path.suffix.lower() in (".py", ".pyc"):
            disasm_res = disassemble_source(target_path)

        if getattr(args, "evidence", False):
            ledger_file = getattr(args, "ledger_file", None)
            ledger = EvidenceLedger(ledger_file=ledger_file)
            claim = getattr(args, "claim", "Automated REA artifact inspection")
            ev_data = {
                "format": inspection.format,
                "size_bytes": inspection.size_bytes,
                "sha256": inspection.sha256,
                "metadata": inspection.metadata,
            }
            if disasm_res:
                ev_data["complexity_score"] = disasm_res.complexity_score
                ev_data["heuristics"] = disasm_res.heuristics
            evidence_rec = ledger.record(
                claim=claim,
                artifact_path=str(target_path),
                data=ev_data,
            )
            print(f"[APEX-REA] Recorded Evidence: {evidence_rec.evidence_id}")

        fmt = getattr(args, "format", "table")
        if fmt == "json":
            out_dict = {"inspection": inspection.to_dict()}
            if disasm_res:
                out_dict["disassembly"] = disasm_res.to_dict()
            if evidence_rec:
                out_dict["evidence"] = evidence_rec.to_dict()
            rendered = json.dumps(out_dict, indent=2, default=str)
        else:
            lines = [
                "=" * 64,
                "   🔍 APEX-COUNCIL REVERSE ENGINEERING INSPECTION (REA)   ",
                "=" * 64,
                f"  Target:       {inspection.target_path}",
                f"  Format:       {inspection.format} ({'Binary' if inspection.is_binary else 'Source/Text'})",
                f"  Size:         {inspection.size_bytes:,} bytes",
                f"  SHA-256:      {inspection.sha256}",
                f"  MIME:         {inspection.mime_type}",
            ]
            if "machine" in inspection.metadata:
                lines.append(f"  Architecture: {inspection.metadata['machine']}")
            if "entry_point" in inspection.metadata:
                lines.append(f"  Entry Point:  {inspection.metadata['entry_point']}")
            if "section_names" in inspection.metadata:
                lines.append(f"  Sections:     {', '.join(inspection.metadata['section_names'][:8])}")

            if disasm_res:
                lines.extend([
                    "-" * 64,
                    f"  Disassembly:  {disasm_res.architecture} ({len(disasm_res.instructions)} opcodes)",
                    f"  Complexity:   {disasm_res.complexity_score} (Branch count: {disasm_res.heuristics.get('branch_count', 0)})",
                    f"  Symbols:      {len(disasm_res.symbols)} symbols detected",
                ])
                if disasm_res.heuristics.get("dangerous_calls_detected"):
                    lines.append(f"  ⚠️ Risk Flags: {', '.join(disasm_res.heuristics['dangerous_calls_detected'])}")

            if evidence_rec:
                lines.extend([
                    "-" * 64,
                    f"  Evidence ID:  {evidence_rec.evidence_id}",
                    f"  Claim:        {evidence_rec.claim}",
                    f"  Signature:    {evidence_rec.signature[:24]}...",
                ])
            lines.append("=" * 64)
            rendered = "\n".join(lines)

        print("\n" + rendered + "\n")
        out_file = getattr(args, "output", None) or getattr(args, "export", None)
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(rendered, encoding="utf-8")
            print(f"Report saved to: {out_file}")
        return 0

    # Command 64: reviewdog
    if args.command == "reviewdog":
        from .reviewdog import parse_diagnostics, filter_diagnostics, report_diagnostics, Severity
        import subprocess

        raw_content = ""
        inp_file = getattr(args, "input_file", None)
        if not inp_file and getattr(args, "input", None) and args.input != "-":
            inp_file = Path(args.input)

        if inp_file:
            if not inp_file.exists():
                sys.stderr.write(f"Error: Input diagnostic file not found: {inp_file}\n")
                return 2
            raw_content = inp_file.read_text(encoding="utf-8", errors="replace")
        elif not sys.stdin.isatty():
            raw_content = sys.stdin.read()
        else:
            sys.stderr.write("Error: Please provide diagnostics via file or pipe to stdin.\n")
            return 1

        diagnostics = parse_diagnostics(
            raw_content,
            format_type=getattr(args, "format", "auto"),
            pattern=getattr(args, "pattern", None),
        )

        diff_text = ""
        if getattr(args, "git", False):
            try:
                proc = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True, check=False)
                diff_text = proc.stdout
            except Exception:
                diff_text = ""
        elif getattr(args, "diff", None):
            diff_arg = str(args.diff)
            if Path(diff_arg).exists():
                diff_text = Path(diff_arg).read_text(encoding="utf-8", errors="replace")
            else:
                diff_text = diff_arg

        filter_mode = getattr(args, "filter_mode", "added")
        if diff_text and filter_mode != "nofilter":
            filtered = filter_diagnostics(diagnostics, diff_text, mode=filter_mode)
        else:
            filtered = diagnostics

        reporter_fmt = getattr(args, "reporter", "text")
        if reporter_fmt == "terminal":
            reporter_fmt = "text"
        elif reporter_fmt == "github-pr":
            reporter_fmt = "markdown"

        rendered = report_diagnostics(
            filtered,
            output_format=reporter_fmt,
            no_color=getattr(args, "no_color", False),
        )
        print("\n" + rendered + "\n")

        out_file = getattr(args, "output", None) or getattr(args, "export", None)
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(rendered, encoding="utf-8")
            print(f"[APEX-REVIEWDOG] Report saved to: {out_file}")

        if getattr(args, "fail_on_error", False) and any(d.severity == Severity.ERROR for d in filtered):
            return 1
        return 0

    # Command 65: Netdata
    if args.command == "netdata":
        from .netdata import (
            collect_snapshot,
            collect_system_metrics,
            NetdataProtocol,
            NetdataClient,
            NetdataEmulatorServer,
        )
        import json
        import time

        # Mode A: Run Local REST API Emulator Server
        if getattr(args, "serve", False):
            port = getattr(args, "port", 19999)
            print(f"\n[APEX-NETDATA] Starting Netdata REST API Emulator daemon on http://127.0.0.1:{port}...")
            server = NetdataEmulatorServer(port=port)
            bound_port = server.start(background=False)
            return 0

        # Mode B: Query /api/v1/info
        if getattr(args, "info", False):
            url = getattr(args, "url", "http://127.0.0.1:19999")
            print(f"\n[APEX-NETDATA] Querying Netdata info from: {url}...")
            client = NetdataClient(base_url=url)
            info = client.get_info()
            print("\n" + json.dumps(info, indent=2) + "\n")
            return 0 if "error" not in info else 1

        # Mode C: Stream Netdata Wire Protocol to stdout
        if getattr(args, "stream", False):
            interval = getattr(args, "interval", 1.0)
            print(f"\n[APEX-NETDATA] Streaming Netdata wire protocol (interval: {interval}s, Press Ctrl+C to stop)...")
            try:
                while True:
                    snap = collect_snapshot()
                    wire_frame = NetdataProtocol.encode_snapshot(snap)
                    sys.stdout.write(wire_frame)
                    sys.stdout.flush()
                    time.sleep(interval)
            except KeyboardInterrupt:
                print("\n[APEX-NETDATA] Stopped telemetry stream.")
            return 0

        # Mode D: Single Snapshot capture (Default / --once)
        snap = collect_snapshot()
        output_text = ""
        export_mode = getattr(args, "export", "json")
        if export_mode == "allmetrics":
            url = getattr(args, "url", "http://127.0.0.1:19999")
            client = NetdataClient(base_url=url)
            allm = client.get_allmetrics()
            output_text = json.dumps(allm, indent=2)
        elif export_mode == "wire":
            output_text = NetdataProtocol.encode_snapshot(snap)
        else:
            summary = snap.to_summary_dict()
            output_text = json.dumps({
                "summary": summary,
                "snapshot": snap.to_dict(),
            }, indent=2)

        print("\n" + output_text + "\n")
        out_file = getattr(args, "output", None)
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(output_text, encoding="utf-8")
            print(f"[APEX-NETDATA] Telemetry exported to: {out_file}")
        return 0

    # Command 66: Lint (Built-in Zero-Dependency Linter)
    if args.command == "lint":
        from .lint.rules import iter_files, lint_source
        import json
        diags: list[dict] = []
        for f in iter_files(args.paths):
            diags += lint_source(f.read_text(encoding="utf-8", errors="replace"), str(f))
        if args.format == "rdjson":
            print(json.dumps({"source": {"name": "apex-lint"}, "diagnostics": diags}))
        else:
            for d in diags:
                loc = d["location"]
                print(f"{loc['path']}:{loc['range']['start']['line']}: [{d['code']['value']}] {d['message']}")
            print(f"{len(diags)} finding(s)")
        return 1 if getattr(args, "fail_on_error", False) and any(d["severity"] == "ERROR" for d in diags) else 0

    # Command 67: Pipe Fix (pytest | apex fix)
    if args.command == "fix":
        from .repair.pipe_fixer import run_pipe_repair
        log_input = getattr(args, "log", "-")
        if log_input == "-" or not log_input:
            if sys.stdin.isatty():
                sys.stderr.write("Apex Fix: No traceback provided via stdin. Pipe failure output to apex fix:\n  pytest | apex fix\n")
                return 1
            trace_text = sys.stdin.read()
        else:
            p = Path(log_input)
            if not p.exists():
                sys.stderr.write(f"Error: Traceback log file not found: {p}\n")
                return 2
            trace_text = p.read_text(encoding="utf-8", errors="replace")
        return run_pipe_repair(trace_text, apply_fix=getattr(args, "apply", False), tests_content=getattr(args, "tests", None))

    # Command 68: Self-Healing Git Hook (apex hook)
    if args.command == "hook":
        from .git.hook import install_hook, uninstall_hook, run_pre_commit_hook
        action = getattr(args, "action", "run")
        if action == "install":
            return 0 if install_hook() else 1
        elif action == "uninstall":
            return 0 if uninstall_hook() else 1
        else:
            return run_pre_commit_hook()

    # Command 69: Mutation Challenge (apex challenge)
    if args.command == "challenge":
        from .evaluator.mutation_challenge import run_mutation_challenge, render_challenge_report
        if not args.file.exists():
            sys.stderr.write(f"Error: Target file not found: {args.file}\n")
            return 2
        src = args.file.read_text(encoding="utf-8")
        tests = ""
        if getattr(args, "tests_file", None) and args.tests_file:
            if not args.tests_file.exists():
                sys.stderr.write(f"Error: Tests file not found: {args.tests_file}\n")
                return 2
            tests = args.tests_file.read_text(encoding="utf-8")
        elif getattr(args, "tests", None):
            test_path = Path(args.tests)
            if test_path.exists():
                tests = test_path.read_text(encoding="utf-8")
            else:
                tests = args.tests
        else:
            sys.stderr.write("Error: Either --tests or --tests-file must be provided.\n")
            return 2
        try:
            rep = run_mutation_challenge(src, tests, target_name=args.file.name, max_mutants=getattr(args, "mutants", 30))
            print(render_challenge_report(rep, filename=args.file.name))
            return 0
        except Exception as ex:
            sys.stderr.write(f"Apex Mutation Challenge Error: {ex}\n")
            return 1

    # Command 70: Kotlin-Style Null Safety (apex null-guard)
    if args.command == "null-guard":
        from .lint.rules import iter_files
        from .lint.null_guard import analyze_null_safety, apply_null_fixes
        total_violations = 0
        for f in iter_files(args.paths):
            src = f.read_text(encoding="utf-8", errors="replace")
            violations = analyze_null_safety(src, filename=str(f))
            if violations:
                total_violations += len(violations)
                print(f"\n[APEX NULL-GUARD] {f} - Found {len(violations)} potentially unsafe None dereference(s):")
                for v in violations:
                    print(f"  Line {v.lineno:3d} | Variable '{v.variable_name}' from {v.source_origin}")
                    print(f"    - Unsafe:   {v.statement_code}")
                    print(f"    + Suggested: {v.suggested_fix}")
                if getattr(args, "fix", False):
                    fixed_code = apply_null_fixes(src, violations)
                    f.write_text(fixed_code, encoding="utf-8")
                    print(f"    [OK] Applied Kotlin-style safe navigation codemods to {f.name}")
        if total_violations == 0:
            print("\n[APEX NULL-GUARD] [OK] All paths verified. Zero unguarded None dereferences detected.")
            return 0
        return 0 if getattr(args, "fix", False) else 1

    # Command 71: Continuous Watcher (apex watch)
    if args.command == "watch":
        from .repair.watcher import run_watch_loop
        return run_watch_loop(
            target_path=getattr(args, "path", "."),
            command=getattr(args, "command", None),
            interval=getattr(args, "interval", 0.5),
            auto_fix=getattr(args, "fix", False),
            once=getattr(args, "once", False),
        )

    # Command 72: Program Slicing (apex slice)
    if args.command == "slice":
        from .formal.slicer import compute_backward_slice, format_slice_report
        target_str = args.target
        line_num = getattr(args, "line", None)
        if ":" in target_str and line_num is None:
            parts = target_str.rsplit(":", 1)
            target_file = Path(parts[0])
            line_num = int(parts[1])
        else:
            target_file = Path(target_str)
            if line_num is None:
                sys.stderr.write("Error: Line number required (e.g. file.py:42 or --line 42)\n")
                return 2

        if not target_file.exists():
            sys.stderr.write(f"Error: Target file not found: {target_file}\n")
            return 2

        src = target_file.read_text(encoding="utf-8", errors="replace")
        vars_set = set(args.var.split(",")) if getattr(args, "var", None) else None
        slice_lines, _ = compute_backward_slice(src, line_num, variables=vars_set)
        report = format_slice_report(target_file.name, line_num, slice_lines, src)
        print(report)
        return 0

    # Command 73: Python 3.10+ / 3.12+ Modernizer (apex modern)
    if args.command == "modern":
        from .lint.modernizer import modernize_file
        from .lint.rules import iter_files
        write_mode = getattr(args, "write", False)
        total_changed = 0
        for f in iter_files(args.files):
            res = modernize_file(str(f), write=write_mode)
            if res.get("changed"):
                total_changed += 1
                action_label = "[MODERNIZED]" if write_mode else "[DIFF]"
                print(f"\n{action_label} {f} ({len(res.get('changes', []))} upgrade(s)):")
                for c in res.get("changes", []):
                    print(f"  • {c}")
                if not write_mode and res.get("diff"):
                    print(res.get("diff"))
        if total_changed == 0:
            print("[APEX MODERN] Codebase is already modern. 0 transformations needed.")
        return 0

    # Command 74: Language Server Protocol (apex lsp)
    if args.command == "lsp":
        from .lsp.server import start_lsp_server
        start_lsp_server()
        return 0

    # Command 75: Autonomous Closed-Loop Repair (apex loop)
    if args.command == "loop":
        from .repair.autonomous_loop import run_autonomous_loop
        res = run_autonomous_loop(
            test_command=getattr(args, "test_command", None),
            max_iterations=getattr(args, "max_iterations", 5),
            auto_commit=getattr(args, "auto_commit", False),
            verbose=getattr(args, "verbose", False),
        )
        return 0 if res.get("success") else 1

    # Command 76: Patch Export (apex patch-export)
    if args.command == "patch-export":
        from .repair.patch_export import export_patch_file
        ok, msg = export_patch_file(args.file, output_patch=getattr(args, "output", None), backup_file=getattr(args, "backup", None))
        if ok:
            print(msg)
            return 0
        else:
            sys.stderr.write(f"Error: {msg}\n")
            return 1

    # Command 77: Crash Fingerprint (apex crash-fingerprint)
    if args.command == "crash-fingerprint":
        from .analysis.fingerprint import compute_crash_fingerprint, format_fingerprint_report
        log_input = getattr(args, "log", "-")
        if log_input == "-" or not log_input:
            if sys.stdin.isatty():
                sys.stderr.write("Apex Crash Fingerprint: Pipe traceback via stdin or pass log file path.\n")
                return 1
            text = sys.stdin.read()
        else:
            p = Path(log_input)
            if not p.exists():
                sys.stderr.write(f"Error: File not found: {p}\n")
                return 2
            text = p.read_text(encoding="utf-8", errors="replace")
        fp = compute_crash_fingerprint(text)
        if not fp:
            sys.stderr.write("Could not parse traceback from input.\n")
            return 1
        print(format_fingerprint_report(fp))
        return 0

    # Command 78: Terminal Flamegraph (apex flamegraph)
    if args.command == "flamegraph":
        from .analysis.flamegraph import profile_function_or_file
        rep = profile_function_or_file(target_path=args.target, top_n=getattr(args, "top", 8))
        print(rep)
        return 0

    # Command 79: PR Summary (apex pr-summary)
    if args.command == "pr-summary":
        from .git.pr_summary import get_git_diff, generate_pr_summary_markdown
        diff_text = get_git_diff(getattr(args, "base", None))
        summary = generate_pr_summary_markdown(diff_text, title=getattr(args, "title", None), base_ref=getattr(args, "base", None))
        print(summary)
        return 0

    # Command 80: Secret Mask (apex secret-mask)
    if args.command == "secret-mask":
        from .security.secret_mask import mask_secrets
        inp = getattr(args, "input", "-")
        if inp == "-" or not inp:
            if sys.stdin.isatty():
                sys.stderr.write("Apex Secret Mask: Pipe text via stdin or pass file path.\n")
                return 1
            text = sys.stdin.read()
        else:
            p = Path(inp)
            if not p.exists():
                sys.stderr.write(f"Error: File not found: {p}\n")
                return 2
            text = p.read_text(encoding="utf-8", errors="replace")
        masked, count = mask_secrets(text)
        print(masked)
        return 0

    # Command 81: Shell Completion (apex completion)
    if args.command == "completion":
        from .cli_completion import generate_completion_script
        print(generate_completion_script(args.shell, KNOWN_COMMANDS))
        return 0

    # Command 82: Zero-Division Guard (apex zero-div)
    if args.command == "zero-div":
        from .lint.rules import iter_files
        from .lint.zero_div_guard import analyze_zero_divisions
        total_violations = 0
        for f in iter_files(args.paths):
            src = f.read_text(encoding="utf-8", errors="replace")
            violations = analyze_zero_divisions(src)
            if violations:
                total_violations += len(violations)
                print(f"\n[APEX ZERO-DIV] {f} - Found {len(violations)} potentially unsafe division(s):")
                for v in violations:
                    tag = "[LITERAL ZERO ERROR]" if v.is_literal_zero else "[UNGUARDED]"
                    print(f"  Line {v.lineno:3d} {tag} Denominator: '{v.denominator}'")
                    print(f"    Code: {v.statement_code}")
        if total_violations == 0:
            print("[APEX ZERO-DIV] [OK] All division operations verified safe.")
            return 0
        return 1

    # Command 83: Apple Instruments Memory Profiler (apex instruments)
    if args.command == "instruments":
        from .instruments.alloc_profiler import profile_memory_allocations
        rep = profile_memory_allocations(target_path=args.target, top_n=getattr(args, "top", 6))
        print(rep)
        return 0

    # Command 84: Apple Swift-Guard Prover (apex swift-guard)
    if args.command == "swift-guard":
        from .lint.rules import iter_files
        from .formal.swift_guard import audit_swift_safety, format_swift_report
        total_findings = 0
        for f in iter_files(args.paths):
            src = f.read_text(encoding="utf-8", errors="replace")
            findings = audit_swift_safety(src)
            total_findings += len(findings)
            print(format_swift_report(findings, f.name))
        return 0 if total_findings == 0 else 1

    # Command 85: Apple Pro Studio Console (apex studio)
    if args.command == "studio":
        from .ui.studio import render_studio_dashboard, launch_studio_web
        if getattr(args, "terminal", False):
            print(render_studio_dashboard())
            return 0
        launch_studio_web(
            host=getattr(args, "host", "127.0.0.1"),
            port=getattr(args, "port", 8765),
            open_browser=not getattr(args, "no_browser", False),
            blocking=True,
        )
        return 0

    # Command 86: Master Verification Runner (apex test-all)
    if args.command == "test-all":
        from .test_all_runner import run_all_systems_test
        return run_all_systems_test()

    # Default bare invocation (`python main.py` or `apex` with no arguments) -> Launch Interactive Agent Console
    if args.command is None and args.direct_prompt is None and getattr(args, "prompt", None) is None:
        from .ui.apex_console import ApexInteractiveConsole
        console = ApexInteractiveConsole()
        console.launch()
        return 0

    # 26. Handle battle / default prompt
    prompt = getattr(args, "prompt", None) or args.direct_prompt or "Build an LRU cache with TTL support"
    offline = getattr(args, "offline", False)
    strict = getattr(args, "strict", False)
    fmt = getattr(args, "format", "table")
    out = getattr(args, "output", None)
    verbose = getattr(args, "verbose", False)

    def _safe_mask_key(key: str | None) -> str:
        if not key:
            return "[NOT SET -> Simulation]"
        clean = key.strip()
        if clean in ("...", "TODO", "your_gemini_api_key", "your_api_key_here"):
            return f"[PLACEHOLDER: {clean}]"
        if len(clean) <= 4:
            return "[SET: ****]"
        return f"[SET: {clean[:4]}**** ({len(clean)} chars)]"

    if verbose:
        print("=" * 70)
        print("  [APEX-VERBOSE] Diagnostic Trace & Runtime Telemetry")
        print("=" * 70)
        print(f"  Python Runtime:      {sys.version.split()[0]} on {sys.platform}")
        print(f"  Working Directory:   {Path('.').resolve()}")
        print(f"  Offline Flag:        {offline}")
        print(f"  Strict Mode:         {strict}")
        print(f"  GEMINI_API_KEY:      {_safe_mask_key(os.getenv('GEMINI_API_KEY'))}")
        print(f"  ANTHROPIC_API_KEY:   {_safe_mask_key(os.getenv('ANTHROPIC_API_KEY'))}")
        print(f"  OPENAI_API_KEY:      {_safe_mask_key(os.getenv('OPENAI_API_KEY'))}")
        print(f"  OLLAMA_MODEL:        {os.getenv('OLLAMA_MODEL', '[Not set]')}")
        print("=" * 70 + "\n")

    print(f"\n[APEX-COUNCIL] Convening the Supreme Council for task: \"{prompt}\"...\n")
    engine = CouncilEngine(force_offline=offline, strict=strict)

    if verbose:
        print("[APEX-VERBOSE] Active Provider Instances:")
        for p_enum, p_impl in engine.providers.items():
            print(f"  • {p_enum.value}: {p_impl.__class__.__name__} (Model: {p_impl.model_name})")
        print()

    result = engine.convene_council(prompt)

    if verbose:
        print("\n" + "=" * 70)
        print("  [APEX-VERBOSE] Latency & Evaluation Telemetry Breakdown")
        print("=" * 70)
        for p_enum, sub in result.submissions.items():
            print(f"  • {p_enum.value:<18} | Latency: {sub.latency_ms:6.1f}ms | Length: {len(sub.code):4d} chars | Model: {sub.model_name}")
            print(f"    Source/Explanation: {sub.explanation}")
        print("=" * 70 + "\n")

    if fmt == "json":
        output = result.to_json()
    elif fmt == "markdown":
        output = CouncilReporter.format_markdown(result)
    else:
        output = CouncilReporter.format_terminal(result)

    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
        print(f"Report saved to: {out}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
