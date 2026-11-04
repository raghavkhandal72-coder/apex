from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import CouncilEngine
from .reporter import CouncilReporter
from .web.server import run_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apex-council",
        description="🏛️ The Multi-LLM Code Supreme Court: Pitting Google Gemini, Anthropic Claude, and OpenAI against each other.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command 1: Battle / Deliberate (default if no subcommand)
    battle_parser = subparsers.add_parser("battle", help="Run head-to-head competition between Gemini, Claude, and OpenAI")
    battle_parser.add_argument("prompt", nargs="?", default="Build an LRU cache with TTL support", help="Coding task prompt")
    battle_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    battle_parser.add_argument("-o", "--output", type=Path, help="Save report to file")
    battle_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 2: Audit File
    audit_parser = subparsers.add_parser("audit", help="Audit an existing file using the Supreme Council")
    audit_parser.add_argument("file", type=Path, help="Path to code file to audit")
    audit_parser.add_argument("--format", choices=["table", "markdown", "json"], default="table", help="Output format")
    audit_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 3: Collaborative Relay
    relay_parser = subparsers.add_parser("relay", help="Run Collaborative Relay: Gemini (Architecture) -> Claude (Defensive Code) -> OpenAI (Tests)")
    relay_parser.add_argument("prompt", help="Task prompt for the relay pipeline")
    relay_parser.add_argument("-o", "--output", type=Path, help="Save generated code and tests to file")
    relay_parser.add_argument("--offline", action="store_true", help="Force offline simulation mode")

    # Command 4: Web UI Server
    serve_parser = subparsers.add_parser("serve", help="Launch the local interactive Web Dashboard")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to bind server (default: 8080)")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")

    # Command 5: Init CI Workflow
    ci_parser = subparsers.add_parser("init-ci", help="Generate GitHub Actions PR workflow file")

    # Top-level fallback argument for direct prompt: `apex-council "my prompt"`
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
          apex-council "Review PR diff for security flaws, edge cases, and algorithmic optimality" --format markdown -o council_verdict.md
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

    # 1. Handle init-ci
    if args.command == "init-ci":
        return handle_init_ci()

    # 2. Handle serve
    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0

    # 3. Handle relay
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

    # 4. Handle audit
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

    # 5. Handle battle / default prompt
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
