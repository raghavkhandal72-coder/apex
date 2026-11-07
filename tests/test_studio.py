import json
import threading
import time
import unittest
import urllib.request
from http.server import HTTPServer

from apex_council.ui.studio import (
    STUDIO_HTML,
    StudioWebHandler,
    generate_sparkline,
    launch_studio_web,
    render_studio_dashboard,
)


class TestApexStudio(unittest.TestCase):
    def test_sparkline_generator(self):
        spark = generate_sparkline([1.0, 2.0, 5.0, 10.0])
        self.assertEqual(len(spark), 4)
        self.assertEqual(generate_sparkline([]), "")
        self.assertEqual(len(generate_sparkline([5.0, 5.0, 5.0])), 3)

    def test_studio_dashboard_render(self):
        output = render_studio_dashboard(suite_tests=335, binary_size_kb=440.0)
        self.assertIn("APEX PRO STUDIO", output)
        self.assertIn("CEGIS Engine", output)
        self.assertIn("Instruments", output)
        self.assertIn("Apex AI Engine", output)

    def test_studio_html_content(self):
        self.assertIn("APEX PRO STUDIO", STUDIO_HTML)
        self.assertIn("Council Chamber", STUDIO_HTML)
        self.assertIn("Ochiai", STUDIO_HTML)
        self.assertIn("Ollama", STUDIO_HTML)

    def test_studio_web_server_endpoints(self):
        server = HTTPServer(("127.0.0.1", 0), StudioWebHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        base_url = f"http://127.0.0.1:{port}"
        try:
            # 1. Test GET /
            with urllib.request.urlopen(f"{base_url}/") as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("APEX PRO STUDIO", html)

            # 2. Test GET /api/status
            with urllib.request.urlopen(f"{base_url}/api/status") as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(data.get("stdlib_purity"))
                self.assertIn("ollama", data)

            # 3. Test GET /api/benchmarks
            with urllib.request.urlopen(f"{base_url}/api/benchmarks") as resp:
                self.assertEqual(resp.status, 200)
                bdata = json.loads(resp.read().decode("utf-8"))
                self.assertIn("results", bdata)

            # 4. Test POST /api/deliberate
            req_data = json.dumps({"prompt": "Binary Search"}).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/deliberate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                d_resp = json.loads(resp.read().decode("utf-8"))
                self.assertIn("consensus_code", d_resp)

            # 5. Test POST /api/repair
            r_req = urllib.request.Request(
                f"{base_url}/api/repair",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(r_req) as resp:
                self.assertEqual(resp.status, 200)
                r_resp = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(r_resp.get("success"))
                self.assertIn("diff", r_resp)

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
