import io
import unittest

from apex_council.lsp.server import (
    ApexLanguageServer,
    read_rpc_message,
    write_rpc_message,
)


class TestApexLSPServer(unittest.TestCase):
    def test_rpc_framing_roundtrip(self):
        buf = io.BytesIO()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "test", "params": {"key": "val"}}
        write_rpc_message(buf, payload)

        buf.seek(0)
        decoded = read_rpc_message(buf)
        self.assertEqual(decoded, payload)

    def test_lsp_server_initialize_and_diagnostics(self):
        in_buf = io.BytesIO()
        out_buf = io.BytesIO()
        server = ApexLanguageServer(in_buf, out_buf)

        # 1. Test initialize
        server.dispatch({"jsonrpc": "2.0", "id": 100, "method": "initialize", "params": {}})
        out_buf.seek(0)
        resp = read_rpc_message(out_buf)
        self.assertEqual(resp["id"], 100)
        self.assertIn("capabilities", resp["result"])

        # 2. Test didOpen with bad code (eval usage -> APX004)
        out_buf.seek(0)
        out_buf.truncate(0)
        bad_code = "def run(x):\n    eval(x)\n"
        server.dispatch({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {"textDocument": {"uri": "file:///test.py", "text": bad_code}},
        })

        out_buf.seek(0)
        diag_msg = read_rpc_message(out_buf)
        self.assertEqual(diag_msg["method"], "textDocument/publishDiagnostics")
        diagnostics = diag_msg["params"]["diagnostics"]
        self.assertTrue(any(d.get("code") == "APX004" for d in diagnostics))


if __name__ == "__main__":
    unittest.main()
