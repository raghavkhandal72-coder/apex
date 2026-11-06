# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and [SemVer](https://semver.org/).

## [Unreleased]

### Added
- QuixBugs benchmark runner with hidden-test evaluation.
- Differential oracle for CEGIS verifier probes.
- Built-in linter (rdjson) and diff-aware PR review GitHub Action.
- Human-readable repair report (token-level diff, hidden-probe result).

### Changed
- CEGIS positioned as bounded, test-guided repair (not formal verification).
- Scoreboard ranks only live providers; --strict aborts instead of falling back to simulation.

## [0.1.0] - 2026-11-06

### Added
- Initial public release of Apex zero-dependency program repair (`apex.pyz`).
- Counterexample-Guided Inductive Synthesis (CEGIS) engine.
- Spectrum-based fault localization triad (Ochiai, Tarantula, DStar).
- Diff-aware GitHub PR review action (`action.yml`).
