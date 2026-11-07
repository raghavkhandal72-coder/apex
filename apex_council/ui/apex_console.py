#!/usr/bin/env python3
"""
Apex-Sovereign: Claude Code Style Interactive AI Agent Terminal Console
Matches Claude Code & Worktrunk & OmO Aesthetics.
100% Pure Python Standard Library | Zero Dependencies (pip = 0).
"""

from __future__ import annotations

import os
import sys
import time

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

if sys.platform == "win32":
    try:
        os.system("")
    except Exception:
        pass

from .mascot import MascotRenderer, MascotTheme
from ..git_engine.worktrunk_advanced import WorktrunkAdvancedEngine
from ..mlflow_engine.tracer import AgentTracer
from ..mlflow_engine.tracker import MLflowExperimentTracker
from ..mlflow_engine.evaluator import LLMJudgeEvaluator
from ..omo.dag_compiler import DagCompiler, DagNodeInput
from ..omo.dag_executor import DagExecutor
from ..omo.dag_tui import DagTuiRenderer


class ApexInteractiveConsole:
    """
    Interactive Terminal Shell providing Claude Code's UI aesthetics
    with Worktrunk worktree matrix, OmO task DAG graph, and MLflow observability.
    """

    def __init__(self, workspace_dir: str = ".") -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.wt_engine = WorktrunkAdvancedEngine(self.workspace_dir)
        self.tracer = AgentTracer("apex_interactive_console")
        self.tracker = MLflowExperimentTracker()
        self.mascot_style = "falcon"
        self.mascot_theme = "gold"

    def launch(self) -> None:
        """Launches the interactive terminal session."""
        t = MascotTheme
        # Print Mascot & Header (Matching Claude Code aesthetic)
        print("\n" + MascotRenderer.render_header(
            version="v0.1.1",
            model="Claude 3.7 Sonnet · Gemini 2.5 Pro · GPT-4o",
            workspace_path=self.workspace_dir,
            tip="Apex v0.1.1: Autonomous Program Repair & Synthesis Engine (pip = 0). Type /help for commands.",
            style=self.mascot_style,
            theme_name=self.mascot_theme,
        ))

        curr_branch = self.wt_engine.get_current_branch()
        print(f"\n{t.DIM}Type /help for command list or /demo for live walkthrough. Type 'exit' to quit.{t.RESET}\n")

        # Non-interactive check (CI / script pipes)
        if not sys.stdin.isatty():
            print(f"{t.DIM}Non-interactive terminal detected. Run 'python main.py --help' for CLI flags.{t.RESET}\n")
            return

        # Setup history persistence & tab completion where supported
        hist_dir = os.path.expanduser("~/.apex")
        hist_file = os.path.join(hist_dir, "history")
        _commands = [
            "/ollama", "/demo", "/benchmark", "/repair", "/test", "/diff", "/review",
            "/instruments", "/swift-guard", "/slice", "/omo", "/wt",
            "/mascot", "/mlflow", "/eval", "/clear", "/help", "/exit", "exit", "quit"
        ]
        try:
            import readline
            def _completer(text: str, state: int):
                matches = [cmd for cmd in _commands if cmd.startswith(text)]
                return matches[state] if state < len(matches) else None
            readline.set_completer(_completer)
            readline.parse_and_bind("tab: complete")
            os.makedirs(hist_dir, exist_ok=True)
            if os.path.exists(hist_file):
                readline.read_history_file(hist_file)
        except Exception:
            pass

        # Interactive loop
        try:
            while True:
                try:
                    prompt_line = input(f"{t.APEX_GOLD}apex ({curr_branch}) > {t.RESET}").strip()
                    if not prompt_line:
                        continue

                    if prompt_line.lower() in {"/exit", "/quit", "exit", "quit", ":q"}:
                        print(f"{t.GRAY}Exiting Apex Console. Session closed.{t.RESET}")
                        break

                    elif prompt_line.lower() in {"/clear", "clear", "cls"}:
                        os.system("cls" if os.name == "nt" else "clear")
                        print("\n" + MascotRenderer.render_header(
                            version="v0.1.1",
                            workspace_path=self.workspace_dir,
                            style=self.mascot_style,
                            theme_name=self.mascot_theme,
                        ))
                        continue

                    elif prompt_line in {"/demo", "demo"}:
                        from .demo_engine import run_live_demo
                        run_live_demo()

                    elif prompt_line in {"/benchmark", "/bench", "benchmark", "bench"}:
                        from .benchmark_engine import run_benchmark_suite
                        run_benchmark_suite()

                    elif prompt_line in {"/diff", "diff"}:
                        from .review_engine import render_colorized_diff
                        print("\n" + render_colorized_diff(self.workspace_dir) + "\n")

                    elif prompt_line.startswith("/review") or prompt_line.startswith("review"):
                        from .review_engine import run_code_review
                        parts = prompt_line.split()
                        target = parts[1] if len(parts) > 1 else self.workspace_dir
                        run_code_review(target)

                    elif prompt_line.startswith("/ollama") or prompt_line == "ollama":
                        from ..providers.ollama_engine import handle_ollama_cli
                        parts = prompt_line.split()
                        handle_ollama_cli(parts[1:])

                    elif prompt_line.startswith("/repair") or prompt_line.startswith("/cegis") or prompt_line == "repair":
                        self._handle_repair_command(prompt_line)

                    elif prompt_line in {"/test", "/test-all", "test", "test-all"}:
                        from ..test_all_runner import run_all_systems_test
                        run_all_systems_test()

                    elif prompt_line.startswith("/instruments") or prompt_line.startswith("/profile"):
                        self._handle_instruments_command(prompt_line)

                    elif prompt_line.startswith("/swift-guard") or prompt_line.startswith("/guard"):
                        self._handle_swift_command(prompt_line)

                    elif prompt_line.startswith("/slice"):
                        self._handle_slice_command(prompt_line)

                    elif prompt_line.startswith("/wt") or prompt_line == "wt":
                        self._handle_wt_command(prompt_line)

                    elif prompt_line.startswith("/omo") or prompt_line.startswith("/ulw"):
                        self._handle_omo_command(prompt_line)

                    elif prompt_line.startswith("/mascot"):
                        self._handle_mascot_command(prompt_line)

                    elif prompt_line.startswith("/mlflow") or prompt_line == "mlflow":
                        self._handle_mlflow_command(prompt_line)

                    elif prompt_line.startswith("/eval"):
                        self._handle_eval_command(prompt_line)

                    elif prompt_line in {"/help", "help", "?"}:
                        self._print_help()

                    elif prompt_line.startswith("/"):
                        import difflib
                        cmd_name = prompt_line.split()[0]
                        closest = difflib.get_close_matches(cmd_name, _commands, n=1, cutoff=0.5)
                        hint = f" Did you mean '{closest[0]}'?" if closest else ""
                        print(f"  {t.RED}Unknown command '{cmd_name}'.{hint} Type /help for available commands.{t.RESET}\n")

                    else:
                        # Natural language agent task execution
                        self._execute_agent_task(prompt_line)

                except (KeyboardInterrupt, EOFError):
                    print(f"\n{t.GRAY}Session closed.{t.RESET}")
                    break
        finally:
            try:
                import readline
                readline.write_history_file(hist_file)
            except Exception:
                pass

    def _handle_repair_command(self, cmd: str) -> None:
        t = MascotTheme
        parts = cmd.split()
        file_path = parts[1] if len(parts) > 1 and not parts[1].startswith("-") else "binary_search.py"
        tests_file = "tests.txt"
        if "--tests" in parts:
            idx = parts.index("--tests")
            if idx + 1 < len(parts):
                tests_file = parts[idx + 1]
        elif "--tests-file" in parts:
            idx = parts.index("--tests-file")
            if idx + 1 < len(parts):
                tests_file = parts[idx + 1]

        if not os.path.exists(file_path):
            if file_path == "binary_search.py":
                print(f"  {t.DIM}• '{file_path}' not found. Generating sample bugged algorithm & test specification...{t.RESET}")
                from .demo_engine import BUGGY_BINARY_SEARCH, TEST_SPEC
                with open("binary_search.py", "w", encoding="utf-8") as f:
                    f.write(BUGGY_BINARY_SEARCH)
                if not os.path.exists(tests_file):
                    with open(tests_file, "w", encoding="utf-8") as f:
                        f.write(TEST_SPEC)
            else:
                print(f"  {t.RED}Error: File '{file_path}' not found.{t.RESET}")
                return

        print(f"  {t.AMBER}• Running CEGIS Inductive Synthesis on '{file_path}'...{t.RESET}")
        src = open(file_path, "r", encoding="utf-8", errors="replace").read()
        tests_code = ""
        if os.path.exists(tests_file):
            tests_code = open(tests_file, "r", encoding="utf-8", errors="replace").read()

        from ..synthesis.cegis_engine import CEGISEngine
        engine = CEGISEngine()
        rep = engine.synthesize_and_verify(src, tests_code)
        if rep.success:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(rep.synthesized_code)
            print(f"  {t.GREEN}✓ [SOUND REPAIR] Successfully synthesized and verified '{file_path}'!{t.RESET}")
            print(f"    Evaluated {rep.total_candidates_explored} candidates in {rep.duration_ms / 1000.0:.2f}s (500 differential probes pass).\n")
        else:
            print(f"  {t.RED}✗ Repair exhausted: {rep.round_logs[-1] if rep.round_logs else 'No candidates verified'}{t.RESET}\n")

    def _handle_instruments_command(self, cmd: str) -> None:
        t = MascotTheme
        parts = cmd.split()
        file_path = parts[1] if len(parts) > 1 else "binary_search.py"
        if not os.path.exists(file_path):
            print(f"  {t.RED}Error: File '{file_path}' not found.{t.RESET}")
            return
        from ..instruments.alloc_profiler import profile_memory_allocations
        print("\n" + profile_memory_allocations(target_path=file_path) + "\n")

    def _handle_swift_command(self, cmd: str) -> None:
        t = MascotTheme
        parts = cmd.split()
        file_path = parts[1] if len(parts) > 1 else "binary_search.py"
        if not os.path.exists(file_path):
            print(f"  {t.RED}Error: File '{file_path}' not found.{t.RESET}")
            return
        from ..formal.swift_guard import audit_swift_safety, format_swift_report
        src = open(file_path, "r", encoding="utf-8", errors="replace").read()
        findings = audit_swift_safety(src)
        print("\n" + format_swift_report(findings, os.path.basename(file_path)) + "\n")

    def _handle_slice_command(self, cmd: str) -> None:
        t = MascotTheme
        parts = cmd.split()
        if len(parts) < 2:
            print("  Usage: /slice <file.py:line>")
            return
        target_spec = parts[1]
        if ":" not in target_spec:
            print("  Error: target must be in format <file.py:line>")
            return
        path, lineno_s = target_spec.rsplit(":", 1)
        if not os.path.exists(path):
            print(f"  {t.RED}Error: File '{path}' not found.{t.RESET}")
            return
        try:
            lineno = int(lineno_s)
        except ValueError:
            print("  Error: line number must be an integer.")
            return
        from ..formal.slicer import compute_backward_slice, format_slice_report
        src = open(path, "r", encoding="utf-8", errors="replace").read()
        lines, _ = compute_backward_slice(src, lineno)
        print("\n" + format_slice_report(src, lines, lineno, os.path.basename(path)) + "\n")

    def _handle_wt_command(self, cmd: str) -> None:
        parts = cmd.split()
        subcmd = parts[1] if len(parts) > 1 else "list"

        if subcmd == "list" or subcmd == "ls":
            full = "--full" in parts or len(parts) == 1
            print("\n" + self.wt_engine.render_table(full=full) + "\n")
        elif subcmd == "switch" and len(parts) > 2:
            branch = parts[2]
            res = self.wt_engine.switch_worktree(branch)
            print(f"  {res}")
        elif subcmd == "add" and len(parts) > 2:
            branch = parts[2]
            res = self.wt_engine.add_worktree(branch)
            print(f"  {res}")
        elif subcmd in {"remove", "rm"} and len(parts) > 2:
            branch = parts[2]
            res = self.wt_engine.remove_worktree(branch)
            print(f"  {res}")
        else:
            print("  Usage: /wt [list|switch <branch>|add <branch>|remove <branch>]")

    def _handle_omo_command(self, cmd: str) -> None:
        """Launches the OmO dual-pane DAG viewer."""
        nodes = [
            DagNodeInput(id="navigation", prompt="Map shell navigation", category="quick", label="navigation"),
            DagNodeInput(id="gate-wiring", prompt="Wire linear gate verification", category="quick", label="gate-wiring"),
            DagNodeInput(id="test-coverage", prompt="Run unit and integration coverage", category="quick", label="test-coverage"),
            DagNodeInput(id="verify-evidence", prompt="Verify attestation signatures and evidence", category="quick", label="verify-evidence", depends_on=["navigation", "gate-wiring", "test-coverage"]),
        ]
        res = DagCompiler.compile(nodes)
        executor = DagExecutor(res)
        telemetry = executor.execute_all()
        tui_output = DagTuiRenderer.render_full_screen(
            dag_result=res,
            telemetry=telemetry,
            task_title="Linear gates integration evidence 1/1",
            run_id="01a97526",
        )
        print("\n" + tui_output + "\n")

    def _handle_mascot_command(self, cmd: str) -> None:
        parts = cmd.split()
        if len(parts) > 1 and parts[1] in MascotRenderer.MASCOT_STYLES:
            self.mascot_style = parts[1]
        if len(parts) > 2 and parts[2] in MascotRenderer.THEME_COLORS:
            self.mascot_theme = parts[2]

        print("\n" + MascotRenderer.render_header(
            version="v0.1.0",
            workspace_path=self.workspace_dir,
            style=self.mascot_style,
            theme_name=self.mascot_theme,
        ) + "\n")

    def _handle_mlflow_command(self, cmd: str) -> None:
        t = MascotTheme
        print(f"\n{t.CYAN}=== MLflow Agent Observability & Tracking ==={t.RESET}")
        print(f"  Active Trace ID:    {self.tracer.trace_id}")
        print(f"  Tracking Directory: {self.tracker.tracking_dir}")
        print(f"  Total Spans Logged: {len(self.tracer.spans)}")
        print(f"  Run MLflow Server:  {t.BOLD}uvx mlflow server --backend-store-uri mlruns{t.RESET}\n")

    def _handle_eval_command(self, cmd: str) -> None:
        parts = cmd.split()
        if len(parts) < 2:
            print("  Usage: /eval <path_to_python_file>")
            return
        file_path = parts[1]
        if not os.path.exists(file_path):
            print(f"  Error: File not found: {file_path}")
            return
        code = open(file_path, "r", encoding="utf-8", errors="replace").read()
        res = LLMJudgeEvaluator.evaluate_code("Audit code quality", code)
        t = MascotTheme
        mark = f"{t.GREEN}✓ PASSED{t.RESET}" if res.passed else f"{t.RED}✗ FAILED{t.RESET}"
        print(f"\n  MLflow LLM Judge Result: {mark} ({res.overall_score * 100:.1f}%)")
        for m in res.metrics:
            m_mark = "✅" if m.passed else "❌"
            print(f"    {m_mark} {m.name}: {m.rationale}")
        print()

    def _print_help(self) -> None:
        t = MascotTheme
        print(f"""
{t.BOLD}Apex Autonomous AI Agent Command Palette:{t.RESET}
  /ollama [status|list|use|run]        Local Ollama GPU/CPU model manager
  /demo                                5-stage live inductive program repair walkthrough
  /benchmark                           Execute high-precision runtime micro-benchmarks
  /repair [file] [--tests tests.txt]   CEGIS automated 1-token & boundary bug repair
  /test                                Run unified 320-test subsystem verification
  /diff                                Colorized git workspace diff inspector
  /review [path]                       Autonomous code defect & safety auditor
  /instruments [file]                  Line-by-line heap allocations & memory leaks
  /swift-guard [file]                  Rust/Swift pattern exhaustiveness & let-safety
  /slice <file:line>                   Mark Weiser (1981) dynamic AST program slicing
  /omo                                 Dual-pane task DAG & workflow visualizer
  /wt [list|switch|add|remove]         Worktree parallel development matrix
  /mascot [falcon|guardian] [gold|cyan] Switch mascot style & theme color
  /mlflow                              Inspect active traces and telemetry spans
  /eval <file>                         Run LLM Judge code audit
  /clear                               Clear screen and redraw mascot header
  /help                                Show this command guide
  /exit                                Exit interactive session

  Or type any coding request directly to convene the Council:
    apex > Build an LRU Cache with TTL support
    apex > Solve issue in calculator.py
""")

    def _explain_file(self, file_path: str) -> None:
        t = MascotTheme
        try:
            import ast
            src = open(file_path, "r", encoding="utf-8", errors="replace").read()
            tree = ast.parse(src, filename=file_path)
            classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            from ..formal.swift_guard import audit_swift_safety
            findings = audit_swift_safety(src)

            print(f"\n{t.CYAN}{t.BOLD}Architectural Analysis: {os.path.basename(file_path)}{t.RESET}")
            print(f"  • Total Lines:       {len(src.splitlines())}")
            print(f"  • Classes ({len(classes)}):       {', '.join(classes) if classes else 'None'}")
            print(f"  • Functions ({len(funcs)}):     {', '.join(funcs) if funcs else 'None'}")
            print(f"  • SwiftGuard Safety: {len(findings)} finding(s)")
            if findings:
                for fnd in findings[:2]:
                    print(f"    - {fnd.message}")
            else:
                print(f"    ✓ 100% compliant with let-immutability and exhaustive patterns.")
            print()
        except Exception as ex:
            print(f"  {t.RED}Error analyzing '{file_path}': {ex}{t.RESET}\n")

    def _execute_agent_task(self, prompt: str) -> None:
        t = MascotTheme
        p_lower = prompt.lower().strip()
        words = p_lower.split()

        # 1. Direct file repair intent
        if len(words) >= 2 and words[0] in {"fix", "repair"} and (words[1].endswith(".py") or os.path.exists(words[1])):
            self._handle_repair_command(f"/repair {words[1]}")
            return

        # 2. Direct file explanation intent
        if len(words) >= 2 and words[0] in {"explain", "analyze", "inspect"} and (words[1].endswith(".py") or os.path.exists(words[1])):
            self._explain_file(words[1])
            return

        print(f"\n{t.AMBER}• Convening Autonomous Supreme Council for task: \"{prompt}\"...{t.RESET}")
        try:
            from ..engine import CouncilEngine
            from ..reporter import CouncilReporter
            engine = CouncilEngine(force_offline=True)
            res = engine.convene_council(prompt)
            print(CouncilReporter.format_terminal(res) + "\n")
        except Exception as ex:
            print(f"{t.RED}Execution error: {ex}{t.RESET}\n")
