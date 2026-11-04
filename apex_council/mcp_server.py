from __future__ import annotations

import json
import sys
from typing import Any, Dict

from .engine import CouncilEngine


class ApexCouncilMCPServer:
    """Standard Model Context Protocol (MCP) Server for Apex-Council.

    Communicates via JSON-RPC 2.0 over standard I/O (stdio).
    Enables Claude Desktop, Cursor, Claude Code, and Cline to call the Council directly.
    """

    def __init__(self, force_offline: bool = False):
        self.engine = CouncilEngine(force_offline=force_offline)

    def run(self):
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
                            "description": "Pit Google Gemini, Anthropic Claude, and OpenAI against each other in real-time, cross-critique their code, run AST security verification, and return synthesized flaw-free code.",
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
                            "description": "Have the Supreme Council audit a code snippet for security vulnerabilities, concurrency hazards, and bugs.",
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
                            "description": "Execute a collaborative 3-tier pipeline: Gemini (Architecture) -> Claude (Defensive Implementation) -> OpenAI (Unit Tests).",
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
                                    f"🏆 Winner: {res.winner.value}\n"
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
                                    f"Audit complete by Supreme Council ({res.winner.value} leading verdict).\n\n"
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


def main():
    server = ApexCouncilMCPServer()
    server.run()


if __name__ == "__main__":
    main()
