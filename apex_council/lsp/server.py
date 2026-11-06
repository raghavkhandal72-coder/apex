"""
Apex LSP: Minimal, zero-dependency Language Server Protocol (LSP) server.
Integrates Apex linter, null-guard, and AST modernizer natively into VS Code, Cursor, and Neovim.
Uses standard library JSON-RPC over stdio (pip = 0).
"""

from __future__ import annotations

import ast
import io
import json
import sys
from typing import Any, BinaryIO, Dict, List, Optional

from apex_council.lint.null_guard import NullGuardAnalyzer
from apex_council.lint.rules import lint_source


def read_rpc_message(stream: BinaryIO) -> Optional[Dict[str, Any]]:
    """Read a JSON-RPC message with Content-Length header from stream."""
    content_length: Optional[int] = None
    while True:
        line_bytes = stream.readline()
        if not line_bytes:
            return None
        line = line_bytes.decode("latin1").strip()
        if not line:
            # End of headers
            break
        if line.lower().startswith("content-length:"):
            parts = line.split(":", 1)
            content_length = int(parts[1].strip())

    if content_length is None or content_length <= 0:
        return None

    body_bytes = stream.read(content_length)
    if not body_bytes or len(body_bytes) < content_length:
        return None

    try:
        return json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def write_rpc_message(stream: BinaryIO, payload: Dict[str, Any]) -> None:
    """Write a JSON-RPC message with Content-Length header to stream."""
    body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode("latin1")
    stream.write(header)
    stream.write(body_bytes)
    stream.flush()


class ApexLanguageServer:
    def __init__(self, in_stream: BinaryIO, out_stream: BinaryIO) -> None:
        self.in_stream = in_stream
        self.out_stream = out_stream
        self.documents: Dict[str, str] = {}
        self.running = True

    def send_response(self, request_id: Any, result: Any) -> None:
        self.send_payload({"jsonrpc": "2.0", "id": request_id, "result": result})

    def send_notification(self, method: str, params: Any) -> None:
        self.send_payload({"jsonrpc": "2.0", "method": method, "params": params})

    def send_payload(self, payload: Dict[str, Any]) -> None:
        write_rpc_message(self.out_stream, payload)

    def run(self) -> None:
        """Main server loop reading JSON-RPC requests."""
        while self.running:
            msg = read_rpc_message(self.in_stream)
            if msg is None:
                break
            self.dispatch(msg)

    def dispatch(self, msg: Dict[str, Any]) -> None:
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize":
            self.handle_initialize(msg_id, params)
        elif method == "initialized":
            pass
        elif method == "shutdown":
            self.send_response(msg_id, None)
        elif method == "exit":
            self.running = False
        elif method == "textDocument/didOpen":
            doc = params.get("textDocument", {})
            uri = doc.get("uri", "")
            text = doc.get("text", "")
            self.documents[uri] = text
            self.publish_diagnostics(uri, text)
        elif method == "textDocument/didChange":
            uri = params.get("textDocument", {}).get("uri", "")
            changes = params.get("contentChanges", [])
            if changes and uri:
                # Full sync model
                text = changes[-1].get("text", "")
                self.documents[uri] = text
                self.publish_diagnostics(uri, text)
        elif method == "textDocument/didSave":
            uri = params.get("textDocument", {}).get("uri", "")
            if uri in self.documents:
                self.publish_diagnostics(uri, self.documents[uri])
        elif method == "textDocument/codeAction":
            self.handle_code_action(msg_id, params)
        else:
            if msg_id is not None:
                # Unsupported method response
                self.send_response(msg_id, None)

    def handle_initialize(self, msg_id: Any, params: Dict[str, Any]) -> None:
        capabilities = {
            "textDocumentSync": 1,  # 1 = Full sync
            "codeActionProvider": True,
        }
        self.send_response(msg_id, {"capabilities": capabilities})

    def publish_diagnostics(self, uri: str, text: str) -> None:
        diagnostics: List[Dict[str, Any]] = []

        # 1. Syntax check via ast.parse
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            line = max((e.lineno or 1) - 1, 0)
            col = max((e.offset or 1) - 1, 0)
            diagnostics.append({
                "range": {
                    "start": {"line": line, "character": col},
                    "end": {"line": line, "character": col + 1},
                },
                "severity": 1,  # 1 = Error
                "source": "Apex",
                "message": f"Syntax Error: {e.msg}",
            })
            self.send_notification("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diagnostics})
            return

        # 2. Built-in Apex Linter (APX001 - APX006)
        lint_issues = lint_source(text, uri)
        for issue in lint_issues:
            loc_range = issue.get("location", {}).get("range", {}).get("start", {})
            line = max(loc_range.get("line", 1) - 1, 0)
            col = max(loc_range.get("column", 1) - 1, 0)
            severity = 1 if issue.get("severity") == "ERROR" else 2  # 2 = Warning
            code_val = issue.get("code", {}).get("value", "APX")
            diagnostics.append({
                "range": {
                    "start": {"line": line, "character": col},
                    "end": {"line": line, "character": col + 10},
                },
                "severity": severity,
                "code": code_val,
                "source": "Apex",
                "message": f"[{code_val}] {issue.get('message')}",
            })

        # 3. Apex Null-Guard
        analyzer = NullGuardAnalyzer(uri)
        analyzer.visit(tree)
        for violation in analyzer.violations:
            line = max(violation.lineno - 1, 0)
            diagnostics.append({
                "range": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": line, "character": 80},
                },
                "severity": 2,  # Warning
                "code": "APX-NULL",
                "source": "Apex Null-Guard",
                "message": f"Potential None dereference on '{violation.variable_name}' (origin: {violation.source_origin})",
            })

        self.send_notification("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": diagnostics})

    def handle_code_action(self, msg_id: Any, params: Dict[str, Any]) -> None:
        # Code actions offer automated quick-fixes in IDEs
        actions: List[Dict[str, Any]] = []
        self.send_response(msg_id, actions)


def start_lsp_server() -> None:
    """Start Apex LSP server over sys.stdin.buffer and sys.stdout.buffer."""
    server = ApexLanguageServer(sys.stdin.buffer, sys.stdout.buffer)
    server.run()
