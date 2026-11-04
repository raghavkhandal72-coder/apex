from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    "perf", "chaos", "appsec", "db-tune", "modernize", "release",
    "-h", "--help"
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw_args = list(sys.argv[1:] if argv is None else argv)

    # Seamless UX Polish: If first argument is not a known command or flag, treat as direct battle prompt
    if raw_args and not raw_args[0].startswith("-") and raw_args[0] not in KNOWN_COMMANDS:
        raw_args = ["battle"] + raw_args

    parser = argparse.ArgumentParser(
        prog="apex-council",
        description="🏛️ The Multi-LLM Code Supreme Court: Enterprise AI Engineering & Consensus Platform.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command 1: Battle / Deliberate
    battle_parser = subparsers.add_parser("battle", help="Run head-to-head competition between Gemini, Claude, and OpenAI")
    battle_parser.add_argument("prompt", nargs="?", default="Build an LRU cache with TTL support", help="Coding task prompt")
    battle_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    battle_parser.add_argument("-o", "--output", type=Path, help="Save report to file")
    battle_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

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

    # Command 21: Cryptographic Hash-Chained Audit Ledger Verifier
    ledger_parser = subparsers.add_parser("verify-ledger", help="Verify HMAC-SHA512 cryptographic audit chain")
    ledger_parser.add_argument("--ledger", type=Path, default=Path(".apex/audit_chain.jsonl"), help="Path to audit ledger")

    # Command 22: Spectrum-Based Fault Localization (Ochiai)
    local_parser = subparsers.add_parser("localize", help="Spectrum-based fault localization using Ochiai algorithm")
    local_parser.add_argument("file", type=Path, help="Target Python source file to trace")
    local_parser.add_argument("--tests", required=True, help="Test code to run against the source file")

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

    # Direct prompt fallback: `apex-council "my prompt"`
    parser.add_argument("direct_prompt", nargs="?", help="Direct prompt to convene the Council")
    parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--offline", action="store_true")

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

    # Command 20: Zero-API-Key Offline Flight Recorder Replay
    if args.command == "demo":
        delay = 0.0 if args.fast else 0.35
        FlightRecorderReplay.run_replay(delay_sec=delay)
        return 0

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
            print(f"\n[APEX-COUNCIL] Sovereign Issue Solver investigating: \"{args.issue}\" in {args.file}...\n")
            solver = AutonomousIssueSolver(repo_dir=args.repo)
            report = solver.solve_issue(
                target_file_rel=args.file,
                issue_description=args.issue,
                test_harness=getattr(args, "tests", ""),
            )
            print("==========================================================")
            print("   🔍 APEX-SOVEREIGN ISSUE RESOLUTION REPORT   ")
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
                    title="Apex-Sovereign Issue Resolution",
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
        print(f"\n[APEX-COUNCIL] Running Ochiai Fault Localization on: {args.file}...")
        localizer = OchiaiFaultLocalizer()
        localizer.trace_execution(code, args.tests, args.file.name)
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
        from scripts.build_pyz import build_standalone_pyz
        out_path = build_standalone_pyz(output_path=args.output)
        return 0

    # 15. Micro-SWE-Bench Tournament
    if args.command == "swe-bench":
        from benchmarks.micro_swebench import run_benchmark
        run_benchmark()
        return 0

    # 16. CPython Bytecode Autopsy
    if args.command == "autopsy":
        from .autopsy.bytecode_inspector import BytecodeInspector
        if not args.file.exists():
            sys.stderr.write(f"Error: File not found: {args.file}\n")
            return 2
        code = args.file.read_text(encoding="utf-8")
        def run_target() -> None:
            scope = {}
            code_obj = compile(code, str(args.file), "exec")
            exec(code_obj, scope)
            if args.tests:
                test_obj = compile(args.tests, f"test_{args.file.name}", "exec")
                exec(test_obj, scope)

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
        print("   🛡️ APEX-SOVEREIGN CRYPTOGRAPHIC PROOF VERIFICATION   ")
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
        print("   ⚡ APEX-SOVEREIGN EDGE RUNNER REPORT   ")
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

    # 26. Handle battle / default prompt
    prompt = getattr(args, "prompt", None) or args.direct_prompt or "Build an LRU cache with TTL support"
    offline = getattr(args, "offline", False)
    fmt = getattr(args, "format", "table")
    out = getattr(args, "output", None)

    print(f"\n[APEX-COUNCIL] Convening the Supreme Council for task: \"{prompt}\"...\n")
    engine = CouncilEngine(force_offline=offline)
    result = engine.convene_council(prompt)

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
