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
                    scope = {}
                    code_obj = compile(source, filename, "exec")
                    exec(code_obj, scope)
                    if test:
                        test_obj = compile(test, f"test_{filename}", "exec")
                        exec(test_obj, scope)

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
