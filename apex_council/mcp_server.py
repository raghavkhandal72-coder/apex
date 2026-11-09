"""Model Context Protocol (MCP) Server for Apex-Sovereign.
Exposes JSON-RPC 2.0 tools over stdio for Claude Desktop, Cursor, and any MCP client.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .autopsy.bytecode_inspector import BytecodeInspector
from .autopsy.ochiai import OchiaiFaultLocalizer
from .engine import CouncilEngine
from .git_engine.proof_notes import GitProofNotesEngine
from .graph.repo_map import RepoMap
from .synthesis.ast_synthesizer import DeterministicASTSynthesizer


class ApexCouncilMCPServer:
    """Standard Model Context Protocol (MCP) Server for Apex-Council.

    Communicates via JSON-RPC 2.0 over standard I/O (stdio).
    Enables Claude Desktop, Cursor, Claude Code, and Cline to call the Council directly.
    """

    def __init__(self, force_offline: bool = False, repo_dir: Optional[Path | str] = None) -> None:
        self.engine = CouncilEngine(force_offline=force_offline)
        self.repo_dir = Path(repo_dir or ".").resolve()

    def run(self) -> None:
        # Configure unbuffered stdin/stdout for JSON-RPC
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)},
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

    def handle_request(self, req: Dict[str, Any]) -> Dict[str, Any] | None:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "apex-council",
                        "version": "1.0.0",
                    },
                },
            }

        elif method == "notifications/initialized":
            return None

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "convene_council",
                            "description": "Pit multiple LLM reasoning engines against each other, cross-critique code, run AST security verification, and return synthesized flaw-free code.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {
                                        "type": "string",
                                        "description": "The coding task or challenge to solve.",
                                    }
                                },
                                "required": ["prompt"],
                            },
                        },
                        {
                            "name": "audit_code",
                            "description": "Audit a code snippet for security vulnerabilities, AST anomalies, and bugs.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "The code text to audit.",
                                    },
                                    "filename": {
                                        "type": "string",
                                        "description": "Optional filename for context.",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "collaborative_relay",
                            "description": "Execute a collaborative 3-tier pipeline: Architecture -> Defensive Implementation -> Unit Tests.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {
                                        "type": "string",
                                        "description": "Goal or feature specification.",
                                    }
                                },
                                "required": ["prompt"],
                            },
                        },
                        {
                            "name": "repomap",
                            "description": "Generate a token-budgeted repository skeleton map using Personalized PageRank and AST extraction.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tokens": {
                                        "type": "integer",
                                        "description": "Maximum token budget (default: 1024).",
                                    },
                                    "focus_files": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "Optional filepaths to prioritize in PageRank personalization.",
                                    },
                                },
                            },
                        },
                        {
                            "name": "ochiai_localize",
                            "description": "Execute spectrum-based fault localization (SBFL) with sys.settrace to pinpoint buggy lines using the Ochiai formula.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Target Python source code.",
                                    },
                                    "test_code": {
                                        "type": "string",
                                        "description": "Test code that asserts behavior.",
                                    },
                                    "filename": {
                                        "type": "string",
                                        "description": "Target filename.",
                                    },
                                },
                                "required": ["source_code", "test_code"],
                            },
                        },
                        {
                            "name": "bytecode_autopsy",
                            "description": "Disassemble Python crash site with CPython dis, inspect opcode offsets, and extract local variable snapshots.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code.",
                                    },
                                    "test_code": {
                                        "type": "string",
                                        "description": "Failing test code.",
                                    },
                                    "filename": {
                                        "type": "string",
                                        "description": "Target filename.",
                                    },
                                },
                                "required": ["source_code", "test_code"],
                            },
                        },
                        {
                            "name": "synthesize_fix",
                            "description": "Synthesize candidate bug fixes deterministically using AST node transformations with zero LLM calls.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Buggy Python source code.",
                                    },
                                    "suspicious_lines": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                        "description": "Suspicious line numbers to mutate.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "verify_proof",
                            "description": "Verify cryptographic HMAC-SHA512 execution proof note on refs/notes/apex-proof for a git commit.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "commit_sha": {
                                        "type": "string",
                                        "description": "Commit SHA to verify (default: HEAD).",
                                    },
                                },
                            },
                        },
                        {
                            "name": "apex_solve",
                            "description": "Autonomous issue resolver: executes Ochiai SBFL, MCTS PUCT test-time compute, and cryptographic proof attestation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue": {
                                        "type": "string",
                                        "description": "Description of the issue or bug to resolve.",
                                    },
                                    "target_file": {
                                        "type": "string",
                                        "description": "Relative path of the target file to repair.",
                                    },
                                    "tests": {
                                        "type": "string",
                                        "description": "Optional unit test harness code.",
                                    },
                                    "iterations": {
                                        "type": "integer",
                                        "description": "Number of MCTS iterations (default: 3).",
                                    },
                                },
                                "required": ["issue", "target_file"],
                            },
                        },
                        {
                            "name": "apex_perf",
                            "description": "Staff Performance Engineer: Profile latency, detect O(N^2) nested loops, in-loop string concatenations, memory allocations, and auto-optimize AST.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Python source code to profile and optimize.",
                                    },
                                    "tests": {
                                        "type": "string",
                                        "description": "Optional unit test harness code.",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "apex_chaos",
                            "description": "Autonomous Chaos & Resilience SRE: Injects socket timeouts, disk full (ENOSPC), and transient RPC jitter into code execution to measure resilience score.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Target Python source code to test.",
                                    },
                                    "tests": {
                                        "type": "string",
                                        "description": "Optional unit test harness code.",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "apex_appsec",
                            "description": "Principal AppSec & Penetration Tester: AST taint flow analysis from untrusted sources to dangerous sinks, weak cryptography detection, and automated secure remediation.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Target Python source code to audit.",
                                    },
                                    "remediate": {
                                        "type": "boolean",
                                        "description": "Whether to auto-remediate insecure patterns (e.g. eval -> ast.literal_eval).",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "apex_db_tune",
                            "description": "Principal Database Architect: Scans for N+1 query antipatterns in loops, auto-synthesizes B-Tree index DDLs, and recommends SQLite WAL configuration.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Python source code containing database operations.",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "apex_modernize",
                            "description": "Legacy Modernizer: Applies modern Python 3.10+ AST codemods (pathlib.Path, PEP 604 type unions, clean I/O with context managers).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "code": {
                                        "type": "string",
                                        "description": "Legacy Python source code to modernize.",
                                    },
                                },
                                "required": ["code"],
                            },
                        },
                        {
                            "name": "apex_release",
                            "description": "Autonomous Release Captain: Compares base and candidate AST public APIs, calculates strict SemVer bumps (MAJOR/MINOR/PATCH), generates Markdown changelogs, and seals with HMAC-SHA512.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "base_code": {
                                        "type": "string",
                                        "description": "Base/current version Python source code.",
                                    },
                                    "candidate_code": {
                                        "type": "string",
                                        "description": "Candidate/new version Python source code.",
                                    },
                                    "current_version": {
                                        "type": "string",
                                        "description": "Current semantic version string (default: 1.0.0).",
                                    },
                                },
                                "required": ["base_code", "candidate_code"],
                            },
                        },
                        {
                            "name": "apex_sbfl_triad",
                            "description": "Unified Spectrum-Based Fault Localization Triad: Computes Ochiai, Tarantula, and DStar (D*) spectra with weighted ensemble scoring.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Target Python source code.",
                                    },
                                    "test_code": {
                                        "type": "string",
                                        "description": "Unit test assertions or test harness.",
                                    },
                                    "star_exponent": {
                                        "type": "number",
                                        "description": "DStar tuning exponent (default: 2.0).",
                                    },
                                },
                                "required": ["source_code", "test_code"],
                            },
                        },
                        {
                            "name": "apex_shapley_consensus",
                            "description": "Cooperative Game-Theoretic Shapley Value attribution engine for fair multi-agent council voting and veto resolution.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "evaluations": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "agent_id": {"type": "string"},
                                                "role": {"type": "string"},
                                                "confidence": {"type": "number"},
                                                "vote": {"type": "string"},
                                                "metric_score": {"type": "number"},
                                                "findings_count": {"type": "integer"},
                                                "weight": {"type": "number"},
                                            },
                                            "required": ["agent_id", "role", "vote"],
                                        },
                                        "description": "Array of agent evaluation records.",
                                    },
                                },
                                "required": ["evaluations"],
                            },
                        },
                        {
                            "name": "apex_hoare_verify",
                            "description": "Formal verification engine: Proves zero-division, loop termination, subscript bounds, and NoneType dereference invariants via Dijkstra Weakest Precondition calculus.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code to formally verify.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "apex_cfg",
                            "description": "Control Flow Graph & Lengauer-Tarjan Dominator Tree analyzer: Extracts basic blocks, immediate dominators, dominance frontiers, and natural loops.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code to analyze.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "apex_abstract_interp",
                            "description": "Abstract Interpretation & Interval Polyhedra safety prover: Computes fixed-point variable intervals and statically proves zero-division and array bounds safety.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code to analyze.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "apex_cegis_solve",
                            "description": "Counterexample-Guided Inductive Synthesizer (CEGIS): Synthesizes provably correct program repairs via inductive search and counterexample verification.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Buggy Python source code.",
                                    },
                                    "test_code": {
                                        "type": "string",
                                        "description": "Initial test harness code.",
                                    },
                                },
                                "required": ["source_code", "test_code"],
                            },
                        },
                        {
                            "name": "apex_solomonoff_eval",
                            "description": "Solomonoff universal prior and algorithmic information evaluator: Computes LZW compressed bits, Kolmogorov complexity upper bound, and Shannon AST entropy.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code to evaluate.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "apex_oracle_synthesize",
                            "description": "Synthesizes an executable reproduce_issue.py bug reproduction test oracle from unstructured issue text and stack traces (Agentless style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_text": {
                                        "type": "string",
                                        "description": "Issue description or stack trace text.",
                                    },
                                },
                                "required": ["issue_text"],
                            },
                        },
                        {
                            "name": "apex_ast_navigate",
                            "description": "Surgical AST symbol search and call hierarchy navigation without full-repo scanning (AutoCodeRover style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Symbol, function, or class name to search.",
                                    },
                                    "root_dir": {
                                        "type": "string",
                                        "description": "Root directory to index (default: current directory).",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "apex_cognitive_memory",
                            "description": "Queries or updates institutional memory and exports cache-optimized CLAUDE.md / AGENTS.md (claude-mem style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query for institutional memory.",
                                    },
                                    "export_claude_md": {
                                        "type": "boolean",
                                        "description": "Whether to export CLAUDE.md context document.",
                                    },
                                },
                            },
                        },
                        {
                            "name": "apex_mini_swe_solve",
                            "description": "Executes Mini-SWE-Agent ACI loop with Linter-in-the-Loop on an issue description.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "issue_text": {
                                        "type": "string",
                                        "description": "Issue description or bug report.",
                                    },
                                    "workspace_dir": {
                                        "type": "string",
                                        "description": "Target workspace directory.",
                                    },
                                },
                                "required": ["issue_text"],
                            },
                        },
                        {
                            "name": "apex_ontology_analyze",
                            "description": "Analyzes codebase semantic ontology, detects architectural layer boundary violations, and computes impact blast radius (NVIDIA auto-ontology style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "source_code": {
                                        "type": "string",
                                        "description": "Python source code to analyze.",
                                    },
                                    "file_path": {
                                        "type": "string",
                                        "description": "Relative file path of the source code.",
                                    },
                                    "check_invariants": {
                                        "type": "boolean",
                                        "description": "Whether to check layer boundary violations.",
                                    },
                                },
                                "required": ["source_code"],
                            },
                        },
                        {
                            "name": "apex_sdd_validate",
                            "description": "Validates code against formal Spec-Driven Development (SDD) contracts and requirements (github/spec-kit style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "spec_text": {
                                        "type": "string",
                                        "description": "Specification Markdown or JSON.",
                                    },
                                    "target_file": {
                                        "type": "string",
                                        "description": "Implementation file path to validate.",
                                    },
                                },
                                "required": ["spec_text"],
                            },
                        },
                        {
                            "name": "apex_worktrunk_manage",
                            "description": "Manages isolated Git worktrees for parallel agent swarms (max-sixty/worktrunk style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "action": {
                                        "type": "string",
                                        "enum": ["allocate", "list", "prune", "cleanup_all"],
                                        "description": "Worktree action to perform.",
                                    },
                                    "agent_id": {
                                        "type": "string",
                                        "description": "Agent identifier for allocate or prune.",
                                    },
                                },
                                "required": ["action"],
                            },
                        },
                        {
                            "name": "apex_executive_review",
                            "description": "Executes Y Combinator Garry Tan Executive C-Suite review (CEO, Eng Manager, Architect, Release Captain) on a proposal (garrytan/gstack style).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "Proposal or PR title.",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Proposal description.",
                                    },
                                    "diff_or_code": {
                                        "type": "string",
                                        "description": "Diff or code content to review.",
                                    },
                                },
                                "required": ["title", "description"],
                            },
                        },
                    ]
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "convene_council":
                prompt = arguments.get("prompt", "Build a high performance cache")
                res = self.engine.convene_council(prompt)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Verdict: {res.verdict_summary}\n\n"
                                    f"Synthesized Code:\n```python\n{res.consensus_code}\n```"
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "audit_code":
                code = arguments.get("code", "")
                filename = arguments.get("filename", "snippet.py")
                prompt = f"Audit and remediate this code for production security and bugs in {filename}:\n\n```\n{code}\n```"
                res = self.engine.convene_council(prompt)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Audit complete ({res.winner.value} leading verdict).\n\n"
                                    f"Remediated Code:\n```python\n{res.consensus_code}\n```"
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "collaborative_relay":
                prompt = arguments.get("prompt", "")
                res = self.engine.collaborative_relay(prompt)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": res["combined_code"],
                            }
                        ]
                    },
                }

            elif tool_name == "repomap":
                tokens = arguments.get("tokens", 1024)
                focus = arguments.get("focus_files", [])
                repomap = RepoMap(self.repo_dir, max_tokens=tokens)
                skeleton = repomap.generate_map(focus_files=focus)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": skeleton}]
                    },
                }

            elif tool_name == "ochiai_localize":
                source = arguments.get("source_code", "")
                test = arguments.get("test_code", "")
                filename = arguments.get("filename", "solution.py")
                localizer = OchiaiFaultLocalizer()
                localizer.trace_execution(source, test, filename)
                ranked = localizer.rank_suspicious_statements()
                data = [
                    {
                        "line": s.line_number,
                        "suspiciousness": s.suspiciousness,
                        "failed_runs": s.failed_executions,
                        "passed_runs": s.passed_executions,
                        "source": s.source_code,
                    }
                    for s in ranked
                ]
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                    },
                }

            elif tool_name == "bytecode_autopsy":
                source = arguments.get("source_code", "")
                test = arguments.get("test_code", "")
                filename = arguments.get("filename", "solution.py")
                def run_target() -> None:
                    from .security.safe_exec import safe_exec
                    scope = {}
                    safe_exec(source, scope, filename=filename)
                    if test:
                        safe_exec(test, scope, filename=f"test_{filename}")

                _, report = BytecodeInspector.execute_and_autopsy(run_target)
                if report and report.crashed:
                    res_payload = {
                        "crashed": True,
                        "exception_type": report.exception_type,
                        "exception_message": report.exception_message,
                        "crashing_file": report.crashing_file,
                        "crashing_line": report.crashing_line,
                        "crashing_function": report.crashing_function,
                        "crashing_opcode": report.crashing_instruction.opname if report.crashing_instruction else None,
                    }
                else:
                    res_payload = {"crashed": False}

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(res_payload, indent=2),
                            }
                        ]
                    },
                }

            elif tool_name == "synthesize_fix":
                source = arguments.get("source_code", "")
                lines = arguments.get("suspicious_lines", None)
                candidates = DeterministicASTSynthesizer.synthesize_repairs(source, suspicious_lines=lines)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    [
                                        {
                                            "strategy": c.repair_strategy,
                                            "target_line": c.target_line,
                                            "edit_distance": c.ast_edit_distance,
                                            "candidate_code": c.candidate_code,
                                        }
                                        for c in candidates
                                    ],
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "verify_proof":
                commit = arguments.get("commit_sha", "HEAD")
                engine = GitProofNotesEngine(self.repo_dir)
                is_valid, msg, proof = engine.verify_proof(commit)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "is_valid": is_valid,
                                        "message": msg,
                                        "proof": {
                                            "commit_sha": proof.commit_sha,
                                            "target_file": proof.target_file,
                                            "ochiai_score": proof.ochiai_score,
                                            "mutation_kill_score": proof.mutation_kill_score,
                                            "merkle_root": proof.merkle_root,
                                            "timestamp": proof.timestamp_iso,
                                        } if proof else None,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name in ("apex_solve", "solve_issue"):
                from .swarm.solver import AutonomousIssueSolver
                issue = arguments.get("issue", "")
                target_file = arguments.get("target_file", "")
                test_code = arguments.get("tests", "")
                iterations = arguments.get("iterations", 3)
                solver = AutonomousIssueSolver(repo_dir=self.repo_dir)
                report = solver.solve_issue(
                    target_file_rel=target_file,
                    issue_description=issue,
                    test_harness=test_code,
                    mcts_iterations=iterations,
                )
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "success": report.success,
                                        "target_file": report.target_file,
                                        "merkle_root": report.merkle_root,
                                        "suspicious_lines": report.suspicious_lines,
                                        "patched_code": report.patched_code,
                                        "duration_ms": report.duration_ms,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_perf":
                from .swarm.specialists.performance_engineer import PerformanceOptimizer
                code = arguments.get("code", "")
                tests = arguments.get("tests", "")
                rep = PerformanceOptimizer.profile_and_optimize(code, test_harness=tests)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "antipatterns_detected": [
                                            {
                                                "category": b.category,
                                                "lineno": b.lineno,
                                                "description": b.description,
                                                "severity": b.severity,
                                            }
                                            for b in rep.antipatterns_detected
                                        ],
                                        "original_duration_ms": rep.original_duration_ms,
                                        "optimized_duration_ms": rep.optimized_duration_ms,
                                        "peak_memory_bytes": rep.peak_memory_bytes,
                                        "speedup_ratio": rep.speedup_ratio,
                                        "has_regressed": rep.has_regressed,
                                        "optimized_code": rep.optimized_code,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_chaos":
                from .swarm.specialists.chaos_engineer import ChaosResilienceEngineer
                code = arguments.get("code", "")
                tests = arguments.get("tests", "")
                rep = ChaosResilienceEngineer.run_chaos_experiments(code, test_harness=tests)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "total_experiments": rep.total_experiments,
                                        "resilient_count": rep.resilient_count,
                                        "resilience_score": rep.resilience_score,
                                        "is_production_ready": rep.is_production_ready,
                                        "results": [
                                            {
                                                "scenario_name": r.scenario_name,
                                                "fault_type": r.fault_type,
                                                "survived": r.survived,
                                                "duration_ms": r.duration_ms,
                                            }
                                            for r in rep.results
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_appsec":
                from .swarm.specialists.appsec_engineer import AppSecPenetrationTester
                code = arguments.get("code", "")
                remediate = arguments.get("remediate", False)
                rep = AppSecPenetrationTester.audit_and_remediate(code)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "security_score": rep.security_score,
                                        "is_airtight": rep.is_airtight,
                                        "taint_flows_count": len(rep.taint_flows),
                                        "vulnerabilities": [
                                            {
                                                "category": v.category,
                                                "lineno": v.lineno,
                                                "severity": v.severity,
                                                "description": v.description,
                                            }
                                            for v in rep.vulnerabilities
                                        ],
                                        "remediated_code": rep.remediated_code if remediate else None,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_db_tune":
                from .swarm.specialists.database_architect import DatabaseArchitect
                code = arguments.get("code", "")
                rep = DatabaseArchitect.analyze_and_tune(code)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "optimization_score": rep.optimization_score,
                                        "is_optimized": rep.is_optimized,
                                        "antipatterns": [
                                            {
                                                "category": a.category,
                                                "lineno": a.lineno,
                                                "severity": a.severity,
                                                "description": a.description,
                                            }
                                            for a in rep.antipatterns
                                        ],
                                        "recommended_indexes": rep.recommended_indexes,
                                        "tuned_code": rep.tuned_code,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_modernize":
                from .swarm.specialists.codebase_modernizer import CodebaseModernizer
                code = arguments.get("code", "")
                rep = CodebaseModernizer.modernize_code(code)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "modernity_score": rep.modernity_score,
                                        "transformations_applied": [
                                            {
                                                "category": t.category,
                                                "lineno": t.lineno,
                                                "description": t.description,
                                            }
                                            for t in rep.transformations_applied
                                        ],
                                        "modernized_code": rep.modernized_code,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_release":
                from .swarm.specialists.release_captain import ReleaseCaptain
                base_code = arguments.get("base_code", "")
                candidate_code = arguments.get("candidate_code", "")
                current_version = arguments.get("current_version", "1.0.0")
                rep = ReleaseCaptain.evaluate_release(base_code, candidate_code, current_version=current_version)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "current_version": rep.current_version,
                                        "next_version": rep.next_version,
                                        "bump_type": rep.bump_type,
                                        "is_breaking": rep.is_breaking,
                                        "deltas_count": len(rep.deltas),
                                        "release_merkle_root": rep.release_merkle_root,
                                        "release_signature": rep.release_signature,
                                        "changelog_markdown": rep.changelog_markdown,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_sbfl_triad":
                from .autopsy.sbfl_triad import SBFLTriadEngine
                src = arguments.get("source_code", "")
                tests = arguments.get("test_code", "")
                star = float(arguments.get("star_exponent", 2.0))
                engine = SBFLTriadEngine(star_exponent=star)
                rep = engine.localize(src, tests)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "total_tests": rep.total_tests,
                                        "passed_tests": rep.passed_tests,
                                        "failed_tests": rep.failed_tests,
                                        "top_suspicious_line": rep.top_suspicious_line,
                                        "consensus_confidence": rep.consensus_confidence,
                                        "ranked_lines": [
                                            {
                                                "lineno": r.lineno,
                                                "ochiai": r.ochiai,
                                                "tarantula": r.tarantula,
                                                "dstar": r.dstar,
                                                "ensemble": r.ensemble,
                                                "ef": r.ef,
                                                "nf": r.nf,
                                                "ep": r.ep,
                                                "np": r.np,
                                                "scope": r.enclosing_scope,
                                                "source": r.source_line,
                                            }
                                            for r in rep.ranked_lines[:10]
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_shapley_consensus":
                from .consensus.shapley_consensus import AgentEvaluation, ShapleyConsensusEngine
                eval_raw = arguments.get("evaluations", [])
                evals = [
                    AgentEvaluation(
                        agent_id=str(e.get("agent_id", f"agent_{i}")),
                        role=str(e.get("role", "Engineer")),
                        confidence=float(e.get("confidence", 0.9)),
                        vote=str(e.get("vote", "APPROVE")),
                        metric_score=float(e.get("metric_score", 1.0)),
                        findings_count=int(e.get("findings_count", 0)),
                        weight=float(e.get("weight", 1.0)),
                    )
                    for i, e in enumerate(eval_raw)
                ]
                engine = ShapleyConsensusEngine()
                rep = engine.compute_exact_shapley_values(evals)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "coalition_value": rep.coalition_value,
                                        "consensus_verdict": rep.consensus_verdict,
                                        "quorum_passed": rep.quorum_passed,
                                        "vetoing_agents": rep.vetoing_agents,
                                        "efficiency_gap": rep.efficiency_gap,
                                        "attributions": [
                                            {
                                                "agent_id": a.agent_id,
                                                "role": a.role,
                                                "shapley_value": a.shapley_value,
                                                "normalized_influence": a.normalized_influence,
                                                "vote": a.vote,
                                            }
                                            for a in rep.attributions
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_hoare_verify":
                from .formal.hoare_invariants import HoareInvariantVerifier
                src = arguments.get("source_code", "")
                rep = HoareInvariantVerifier.verify_code(src)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "is_provably_safe": rep.is_provably_safe,
                                        "safety_confidence": rep.safety_confidence,
                                        "total_invariants_checked": rep.total_invariants_checked,
                                        "hoare_triples_verified": rep.hoare_triples_verified,
                                        "violations": [
                                            {
                                                "category": v.category,
                                                "lineno": v.lineno,
                                                "expression": v.expression,
                                                "weakest_precondition": v.weakest_precondition,
                                                "severity": v.severity,
                                                "remediation_hint": v.remediation_hint,
                                            }
                                            for v in rep.violations
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_cfg":
                from .graph.cfg_dominator import CFGDominatorEngine
                src = arguments.get("source_code", "")
                rep = CFGDominatorEngine.analyze_source(src)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "total_blocks": rep.total_blocks,
                                        "total_edges": rep.total_edges,
                                        "cyclomatic_complexity": rep.cyclomatic_complexity,
                                        "natural_loops_count": len(rep.natural_loops),
                                        "immediate_dominators": {str(k): v for k, v in rep.immediate_dominators.items()},
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_abstract_interp":
                from .formal.abstract_interpreter import ASTAbstractInterpreter
                src = arguments.get("source_code", "")
                analyzer = ASTAbstractInterpreter()
                rep = analyzer.analyze(src)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "total_proofs": rep.total_proofs,
                                        "proven_safe_count": rep.proven_safe_count,
                                        "zero_division_risks": rep.zero_division_risks,
                                        "variable_intervals": {k: str(v) for k, v in rep.final_state.environment.items()},
                                        "safety_proofs": [
                                            {
                                                "lineno": p.lineno,
                                                "operation": p.operation,
                                                "proof_type": p.proof_type,
                                                "is_safe": p.is_provably_safe,
                                                "explanation": p.explanation,
                                            }
                                            for p in rep.safety_proofs
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_cegis_solve":
                from .synthesis.cegis_engine import CEGISEngine
                src = arguments.get("source_code", "")
                tests = arguments.get("test_code", "")
                engine = CEGISEngine()
                rep = engine.synthesize_and_verify(src, tests)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "success": rep.success,
                                        "verification_certified": rep.verification_certified,
                                        "iterations_run": rep.iterations_run,
                                        "total_candidates_explored": rep.total_candidates_explored,
                                        "duration_ms": rep.duration_ms,
                                        "synthesized_code": rep.synthesized_code,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_solomonoff_eval":
                from .search.solomonoff_prior import SolomonoffPriorEngine
                src = arguments.get("source_code", "")
                engine = SolomonoffPriorEngine()
                rep = engine.evaluate_program(src)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "raw_character_count": rep.raw_character_count,
                                        "lzw_token_count": rep.lzw_token_count,
                                        "compressed_bits": rep.compressed_bits,
                                        "compression_ratio": rep.compression_ratio,
                                        "ast_shannon_entropy": rep.ast_shannon_entropy,
                                        "solomonoff_prior_score": rep.solomonoff_prior_score,
                                        "kolmogorov_upper_bound": rep.kolmogorov_upper_bound,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_oracle_synthesize":
                from .claude_engine.oracle_synthesizer import BugReproductionOracle
                issue_text = arguments.get("issue_text", "")
                spec = BugReproductionOracle.parse_issue(issue_text)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "target_file": spec.target_file,
                                        "target_symbol": spec.target_symbol,
                                        "exception_type": spec.exception_type,
                                        "reproduction_code": spec.reproduction_code,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_ast_navigate":
                from .claude_engine.ast_navigator import ASTSymbolNavigator
                query = arguments.get("query", "")
                root_dir = arguments.get("root_dir", ".")
                nav = ASTSymbolNavigator(root_dir)
                matches = nav.search_function(query) + nav.search_class(query) + nav.search_method(query)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    [
                                        {
                                            "name": m.name,
                                            "kind": m.kind,
                                            "file_path": m.file_path,
                                            "lineno": m.lineno,
                                            "end_lineno": m.end_lineno,
                                            "parameters": m.parameters,
                                            "docstring": m.docstring,
                                        }
                                        for m in matches
                                    ],
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_cognitive_memory":
                from .claude_engine.cognitive_memory import CognitiveMemoryStream
                query = arguments.get("query", "")
                export_claude = arguments.get("export_claude_md", False)
                stream = CognitiveMemoryStream()
                hits = stream.search(query, top_k=5) if query else []
                claude_md_content = stream.synthesize_claude_md() if export_claude else None
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "records_found": len(hits),
                                        "results": [h.to_dict() for h in hits],
                                        "claude_md": claude_md_content,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_mini_swe_solve":
                from .claude_engine.mini_swe_aci import MiniSWEAgentACI
                issue_text = arguments.get("issue_text", "")
                workspace_dir = arguments.get("workspace_dir", ".")
                aci = MiniSWEAgentACI(workspace_dir)
                res = aci.solve_issue_loop(issue_text)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(res, indent=2),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_ontology_analyze":
                from .ontology.code_ontology import CodeOntologyEngine
                src = arguments.get("source_code", "")
                file_path = arguments.get("file_path", "module.py")
                check_inv = arguments.get("check_invariants", True)
                engine = CodeOntologyEngine()
                engine.index_source(file_path, src)
                violations = engine.check_invariants() if check_inv else []
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "entities_count": len(engine.entities),
                                        "relations_count": len(engine.relations),
                                        "violations": [
                                            {
                                                "rule_id": v.rule_id,
                                                "severity": v.severity,
                                                "message": v.message,
                                                "recommendation": v.recommendation,
                                            }
                                            for v in violations
                                        ],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_sdd_validate":
                from .spec.sdd_engine import SDDEngine
                spec_text = arguments.get("spec_text", "")
                target_file = arguments.get("target_file")
                spec = SDDEngine.parse_spec_text(spec_text)
                rep_dict = None
                if target_file:
                    rep = SDDEngine.validate_spec_compliance(spec, target_file)
                    rep_dict = {
                        "compliance_score": rep.compliance_score,
                        "passed_requirements": rep.passed_requirements,
                        "failed_requirements": rep.failed_requirements,
                    }
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "spec_name": spec.name,
                                        "requirements_count": len(spec.requirements),
                                        "validation": rep_dict,
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_worktrunk_manage":
                from .git_engine.worktrunk import WorktrunkEngine
                action = arguments.get("action", "list")
                agent_id = arguments.get("agent_id", "agent-default")
                trunk = WorktrunkEngine()
                res_data = {}
                if action == "allocate":
                    sess = trunk.allocate_worktree(agent_id)
                    res_data = {"allocated": True, "path": str(sess.worktree_path), "branch": sess.branch_name}
                elif action == "prune":
                    ok = trunk.prune_worktree(agent_id)
                    res_data = {"pruned": ok}
                elif action == "cleanup_all":
                    cnt = trunk.cleanup_all()
                    res_data = {"cleaned_worktrees": cnt}
                else:
                    active = trunk.list_active_worktrees()
                    res_data = {"active_worktrees": [dataclasses.asdict(a) for a in active]}
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(res_data, indent=2),
                            }
                        ]
                    },
                }

            elif tool_name == "apex_executive_review":
                from .swarm.executive_stack import ExecutiveStackOrchestrator
                title = arguments.get("title", "")
                desc = arguments.get("description", "")
                diff = arguments.get("diff_or_code", "")
                consensus = ExecutiveStackOrchestrator.evaluate_proposal(title, desc, diff)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "unanimous_approval": consensus.unanimous_approval,
                                        "aggregate_score": consensus.aggregate_score,
                                        "suggested_semver": consensus.suggested_semver,
                                        "verdicts": [dataclasses.asdict(v) for v in consensus.verdicts],
                                    },
                                    indent=2,
                                ),
                            }
                        ]
                    },
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }


def main() -> None:
    server = ApexCouncilMCPServer()
    server.run()


if __name__ == "__main__":
    main()
