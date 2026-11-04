from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import CouncilEngine
from .reporter import CouncilReporter


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="apex-council",
        description="🏛️ The Multi-LLM Code Supreme Court: Pitting Google Gemini, Anthropic Claude, and OpenAI against each other.",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Build an LRU cache with TTL support and clean error handling",
        help="Coding challenge or task prompt to convene the Council for (default: LRU Cache challenge)",
    )
    parser.add_argument(
        "--format",
        choices=["table", "markdown", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Save report and synthesized code to file",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force offline simulation mode without querying live remote APIs",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # Ensure Windows console handles UTF-8 formatting and unicode
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = parse_args(argv)

    print(f"\n[APEX-COUNCIL] Convening the Supreme Council for task: \"{args.prompt}\"...\n")
    engine = CouncilEngine(force_offline=args.offline)
    result = engine.convene_council(args.prompt)

    if args.format == "json":
        output = result.to_json()
    elif args.format == "markdown":
        output = CouncilReporter.format_markdown(result)
    else:
        output = CouncilReporter.format_terminal(result)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
