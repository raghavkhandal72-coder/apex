from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import CouncilEngine
from .evaluator.benchmark import format_benchmark_table, run_benchmark_tournament
from .evaluator.git_review import review_git_diff
from .evaluator.github_pr import review_github_pr
from .evaluator.redteam import run_redteam_analysis
from .evaluator.self_healing import SelfHealingLoop
from .mcp_server import ApexCouncilMCPServer
from .polyglot import detect_language, get_language_prompt_guidelines
from .reporter import CouncilReporter
from .web.server import run_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apex-council",
        description="🏛️ The Multi-LLM Code Supreme Court: Pitting Google Gemini, Anthropic Claude, and OpenAI against each other.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command 1: Battle / Deliberate
    battle_parser = subparsers.add_parser("battle", help="Run head-to-head competition between Gemini, Claude, and OpenAI")
    battle_parser.add_argument("prompt", nargs="?", default="Build an LRU cache with TTL support", help="Coding task prompt")
    battle_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    battle_parser.add_argument("-o", "--output", type=Path, help="Save report to file")
    battle_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 2: Autonomous Self-Healing / Auto-Repair
    heal_parser = subparsers.add_parser("heal", help="Autonomous Closed-Loop Code Repair (Tests -> Traceback -> Fix -> Re-test)")
    heal_parser.add_argument("file", type=Path, help="Path to code file to auto-heal")
    heal_parser.add_argument("--tests", default="", help="Optional test harness script to verify fixes against")
    heal_parser.add_argument("--max-attempts", type=int, default=3, help="Max self-healing iterations (default: 3)")
    heal_parser.add_argument("--no-write", action="store_true", help="Do not overwrite file on disk (dry run)")
    heal_parser.add_argument("--offline", action="store_true")

    # Command 3: GitHub PR Review
    pr_parser = subparsers.add_parser("pr", help="Review a live GitHub Pull Request (URL or owner/repo#123)")
    pr_parser.add_argument("target", help="GitHub PR URL or 'owner/repo#number'")
    pr_parser.add_argument("--token", help="GitHub Personal Access Token (or GITHUB_TOKEN env var)")
    pr_parser.add_argument("--offline", action="store_true")

    # Command 4: Audit File
    audit_parser = subparsers.add_parser("audit", help="Audit an existing file using the Supreme Council")
    audit_parser.add_argument("file", type=Path, help="Path to code file to audit")
    audit_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    audit_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 5: Collaborative Relay
    relay_parser = subparsers.add_parser("relay", help="Run Collaborative Relay: Gemini (Architecture) -> Claude (Defensive Code) -> OpenAI (Tests)")
    relay_parser.add_argument("prompt", help="Task prompt for the relay pipeline")
    relay_parser.add_argument("-o", "--output", type=Path, help="Save generated code and tests to file")
    relay_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 6: Web UI Server
    serve_parser = subparsers.add_parser("serve", help="Launch the local interactive Web Dashboard")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind server (default: 8080)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")

    # Command 7: MCP Server
    mcp_parser = subparsers.add_parser("mcp", help="Run Apex-Council as a Model Context Protocol (MCP) server for Claude Desktop / Cursor")
    mcp_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 8: Git Diff Pre-Commit Review
    diff_parser = subparsers.add_parser("diff", help="Audit uncommitted Git diff changes before commit/push")
    diff_parser.add_argument("--staged", action="store_true", help="Review staged changes only")
    diff_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    diff_parser.add_argument("--offline", action="store_true")

    # Command 9: Red-Team Adversarial Fuzzer
    redteam_parser = subparsers.add_parser("redteam", help="Fuzz code file against adversarial injections and stress vectors")
    redteam_parser.add_argument("file", type=Path, help="Path to file to fuzz")

    # Command 10: SWE Benchmark Tournament
    bench_parser = subparsers.add_parser("benchmark", help="Run 5-Challenge SWE Tournament across Gemini, Claude, and OpenAI")
    bench_parser.add_argument("--format", choices=["table", "json"], default="table")
    bench_parser.add_argument("--offline", action="store_true")

    # Command 11: Init CI Workflow
    ci_parser = subparsers.add_parser("init-ci", help="Generate GitHub Actions PR workflow file")

    # Direct prompt fallback: `apex-council "my prompt"`
    parser.add_argument("direct_prompt", nargs="?", help="Direct prompt to convene the Council")
    parser.add_argument("--format", choices=["table", "markdown", "json"], default="table")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--offline", action="store_true")

    return parser.parse_args(argv)


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
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args(argv)

    # 1. Autonomous Self-Healing Mode
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

    # 2. GitHub PR Review
    if args.command == "pr":
        print(f"\n[APEX-COUNCIL] Fetching and reviewing GitHub PR: {args.target}...\n")
        pr_res = review_github_pr(args.target, token=args.token, force_offline=args.offline)
        print(pr_res["markdown_comment"])
        return 0

    # 3. MCP Server
    if args.command == "mcp":
        server = ApexCouncilMCPServer(force_offline=args.offline)
        server.run()
        return 0

    # 4. Benchmark Tournament
    if args.command == "benchmark":
        print("\n[APEX-COUNCIL] Starting SWE Benchmark Tournament across 5 production challenges...\n")
        bench_data = run_benchmark_tournament(force_offline=args.offline)
        if args.format == "json":
            import json
            print(json.dumps(bench_data, indent=2))
        else:
            print(format_benchmark_table(bench_data))
        return 0

    # 5. Red-Team Fuzzer
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

    # 6. Git Diff Review
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

    # 7. Handle init-ci
    if args.command == "init-ci":
        return handle_init_ci()

    # 8. Handle serve
    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0

    # 9. Handle relay
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

    # 10. Handle audit
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

    # 11. Handle battle / default prompt
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
