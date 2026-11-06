# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **Unified Master Verification Pipeline (`apex test-all`) & 1-Click PowerShell Runner (`test_all.ps1`)**: Single-command executive scorecard connecting all 11 core subsystems (CEGIS, AST Slicer, Kotlin Null-Guard, Zero-Div Guard, Apple Instruments Memory Profiler, Swift-Guard Exhaustiveness, Terminal Flamegraph, Crash Fingerprinting, Secret Masking, PR Summary, and 315-test Unit Suite) with real-time Apple Pro Studio dashboard telemetry.
- **Apple Instruments Memory Profiler (`apex instruments`)**: Line-by-line heap allocation waterfall, peak footprint analysis, and circular reference leak detection via stdlib `tracemalloc` and `gc`.
- **Apple Swift-Guard Safety Prover (`apex swift-guard`)**: Pattern match exhaustiveness verification, immutability & let-safety checking, and nil-coalescing analysis.
- **Apple Pro Studio Telemetry Console (`apex studio`)**: Apple Pro terminal dashboard with system architecture telemetry, test latency sparklines, and unified health metrics.
- **Git Patch Exporter (`apex patch-export`)**: Generates Git-compatible unified `.patch` / `.diff` files from CEGIS repairs for `git apply`.
- **Deterministic Crash Fingerprint (`apex crash-fingerprint`)**: Computes line-drift-invariant normalized SHA-256 crash signatures to group identical bugs in CI/CD.
- **Terminal Flamegraph Profiler (`apex flamegraph`)**: Zero-dependency hierarchical execution profiler and ASCII flamegraph renderer using stdlib `cProfile` and `pstats`.
- **Automated PR Summary Generator (`apex pr-summary`)**: Inspects git diffs and AST changes to generate rich GitHub PR descriptions with file matrices and risk heuristics.
- **Sensitive Secret Redactor (`apex secret-mask`)**: Real-time log and traceback sanitizer redacting Google API keys, OpenAI tokens, AWS keys, JWTs, and DB passwords.
- **Shell Auto-Completion Generator (`apex completion`)**: Dynamic argument completion script generator for Bash, Zsh, and PowerShell.
- **Zero-Division Static Guard (`apex zero-div`)**: Static AST analyzer and defensive prover preventing `ZeroDivisionError` across division and modulo operators.
- **Continuous File Watcher (`apex watch`)**: Zero-dependency filesystem watcher polling `os.stat` mtimes to continuously trigger test runs and CEGIS repairs on save.
- **AST Program Slicing (`apex slice`)**: Backward and forward data/control dependency program slicing (Mark Weiser 1981) to isolate the minimal causal statements influencing a crash.
- **Python Modernizer Codemod (`apex modern`)**: Zero-dependency AST and token codemod upgrading legacy `typing.Union` / `Optional` / `List` / `Dict` to native Python 3.10+ PEP 604 & 585 syntax.
- **Language Server Protocol Server (`apex lsp`)**: Minimal stdlib JSON-RPC LSP server communicating over stdio to bring Apex diagnostics and quick-fixes into Cursor, VS Code, and Neovim.
- **Autonomous Closed-Loop Repair (`apex loop`)**: Autonomous test-driven loop (Test -> Traceback -> CEGIS Synthesis -> Invariant Verification -> In-Place Patch -> Re-Test) that runs until 100% tests pass.
- **Pipe Repair Engine (`apex fix`)**: Unix pipe traceback auto-repair (`pytest | apex fix --apply`). Parses tracebacks from stdin, isolates crash sites, executes bounded CEGIS, and applies in-place patches with automatic `.bak` backups.
- **Self-Healing Git Pre-Commit Hook (`apex hook install`)**: Zero-dependency Git pre-commit hook that intercepts broken staged commits, repairs regressions via CEGIS, and auto-stages verified fixes.
- **Mutation Challenge Suite (`apex challenge`)**: Standard-library mutation testing engine and Mutation Resilience Score (`%`) that reveals test suite blindspots and fake code coverage.
- **Kotlin-Style Null Guard (`apex null-guard`)**: Static `None`/null-safety analyzer and auto-patcher for Python (`AttributeError: 'NoneType' object has no attribute '...'`) tracking optional types and safe navigation.
- QuixBugs benchmark runner with hidden-test evaluation.
- Differential oracle for CEGIS verifier probes.
- Built-in linter (rdjson) and diff-aware PR review GitHub Action.
- Human-readable repair report (token-level diff, hidden-probe result).
- One-line installer scripts for Unix (`install.sh`) and Windows (`install.ps1`).
- Automated release workflow with sha256 checksums (`.github/workflows/release.yml`).
- Pre-commit hook configuration for zero-dependency linting (`.pre-commit-hooks.yaml`).
- Mutation grammar expansion for boolean logic (`and`/`or`), membership (`in`/`not in`), identity (`is`/`is not`), and generalized integer off-by-one boundary constants.

### Changed
- CEGIS positioned as bounded, test-guided repair (not formal verification).
- Scoreboard ranks only live providers; --strict aborts instead of falling back to simulation.

## [0.1.0] - 2026-11-06

### Added
- Initial public release of Apex zero-dependency program repair (`apex.pyz`).
- Counterexample-Guided Inductive Synthesis (CEGIS) engine.
- Spectrum-based fault localization triad (Ochiai, Tarantula, DStar).
- Diff-aware GitHub PR review action (`action.yml`).
