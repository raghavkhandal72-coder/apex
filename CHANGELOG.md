# Changelog

All notable changes to **Apex** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-11-06

### Added
- **Delightful Terminal Repair Report (`apex_council.ui.repair_report`):**
  - Token-level AST diff highlighting with ANSI colors and plain-text fallback.
  - Spectrum-based fault localization suspiciousness bars (`Ochiai` scores).
  - Explicit visible tests passing count and hidden differential oracle probe validation.
  - Automatic fallback for `NO_COLOR` environments and non-UTF8 terminals.
- **Diff-Aware PR Review Action (`action.yml` & `tools/pr_review.py`):**
  - Standalone zero-dependency composite GitHub Action (`Apex PR Review`).
  - Added line range parsing (`parse_added_lines`) from standard git unified diffs.
  - Reviewdog diagnostic format (`rdjson`) parsing and comment filtering.
  - Deterministic inline GitHub PR review comment generation with `--dry-run` and `--fail-on-error` options.
- **Differential Oracle for Program Repair (`apex_council.synthesis.differential_oracle`):**
  - Reference implementation verification against `bisect` for search algorithms.
  - 500-probe randomized domain fuzzing to detect and prevent test overfitting.
- **20-Second Demo Reproducibility:**
  - `binary_search.py` and `tests.txt` root assets for instant single-command evaluation.
  - `demo/demo.tape` for terminal recordings using VHS.
- **Empirical QuixBugs Evaluation Harness (`benchmarks/quixbugs_runner.py`):**
  - Independent benchmark runner reporting verifiable empirical results on 26 attempted programs.

### Changed
- Refactored `apex cegis`, `apex sbfl`, and `apex localize` to support both `--tests` and `--tests-file`.
- Retained machine-readable `--- SYNTHESIZED REPAIRED CODE ---` markers to ensure automated benchmark compatibility while rendering human-delight terminal reports.
- Standardized release versioning to `v0.9.0` with frozen release tags.
- Verified 100% standard library purity across all modules (`tools/check_stdlib_only.py`).

### Security
- Comprehensive git log audit confirming zero credentials or API secrets in commit history.
- Hermetic execution sandbox scrubbing environment variables before child process invocation.
