#!/usr/bin/env python3
"""
Apex-Sovereign: Electron Desktop IPC Bridge & Scaffold
Inspired by electron/electron (Cross-Platform Native Desktop Shell for Apex)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import http.server
import json
import os
import socketserver
import threading
from typing import Any, Callable, Dict, List, Optional


class ElectronBridgeHandler(http.server.BaseHTTPRequestHandler):
    """Handles JSON-RPC requests from the Electron renderer process."""

    server_context: Any = None

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)
        try:
            req_data = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            self._send_json({"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}, "id": None}, 400)
            return

        method = req_data.get("method", "")
        params = req_data.get("params", {})
        req_id = req_data.get("id")

        result = self.server_context.dispatch(method, params)
        self._send_json({"jsonrpc": "2.0", "result": result, "id": req_id}, 200)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "healthy", "service": "apex-electron-bridge"}, 200)
        else:
            self._send_json({"error": "Use POST for JSON-RPC 2.0 calls"}, 404)

    def _send_json(self, data: Dict[str, Any], code: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # Suppress default noisy stdio logging


class ElectronBridgeServer:
    """
    Local JSON-RPC Bridge allowing Electron desktop shells to communicate
    with the Apex Council core.
    """

    def __init__(self, port: int = 4242) -> None:
        self.port = port
        self.methods: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._httpd: Optional[socketserver.TCPServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._register_default_methods()

    def _register_default_methods(self) -> None:
        self.register_method("ping", lambda p: {"pong": True, "version": "0.9.0"})
        self.register_method("get_mascot", lambda p: {
            "mascot": "Apex Sovereign Cyber-Falcon",
            "colors": {"primary": "#E5A93C", "secondary": "#101216"},
            "style": p.get("style", "falcon"),
        })

    def register_method(self, name: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self.methods[name] = handler

    def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        if method in self.methods:
            try:
                return self.methods[method](params)
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"Method '{method}' not implemented"}

    def start_background(self) -> int:
        handler_cls = type("BoundHandler", (ElectronBridgeHandler,), {"server_context": self})
        # Try port and fallback if busy
        for test_port in range(self.port, self.port + 50):
            try:
                self._httpd = socketserver.TCPServer(("127.0.0.1", test_port), handler_cls)
                self.port = test_port
                break
            except OSError:
                continue

        if not self._httpd:
            raise RuntimeError("Unable to bind to any local port for Electron bridge")

        self._server_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._server_thread.start()
        return self.port

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()


def generate_electron_scaffold(target_dir: str = "electron") -> List[str]:
    """Generates a complete ready-to-launch Electron desktop application shell."""
    os.makedirs(target_dir, exist_ok=True)
    created_files = []

    # 1. package.json
    pkg_json = {
        "name": "apex-desktop",
        "version": "0.9.0",
        "description": "Apex Multi-Agent Desktop Shell",
        "main": "main.js",
        "scripts": {
            "start": "electron ."
        },
        "author": "Apex Council",
        "license": "Apache-2.0"
    }
    pkg_path = os.path.join(target_dir, "package.json")
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(pkg_json, f, indent=2)
    created_files.append(pkg_path)

    # 2. main.js
    main_js = """const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    title: 'Apex Sovereign Desktop',
    backgroundColor: '#0d1117',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
"""
    main_path = os.path.join(target_dir, "main.js")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main_js)
    created_files.append(main_path)

    # 3. preload.js
    preload_js = """const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('apexBridge', {
  sendRPC: async (method, params) => {
    const res = await fetch('http://127.0.0.1:4242', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: Date.now(), method, params })
    });
    return await res.json();
  }
});
"""
    preload_path = os.path.join(target_dir, "preload.js")
    with open(preload_path, "w", encoding="utf-8") as f:
        f.write(preload_js)
    created_files.append(preload_path)

    # 4. index.html
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Apex Sovereign Desktop</title>
  <style>
    body {
      background-color: #0b0e14;
      color: #e6edf3;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      margin: 0;
      padding: 24px;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 16px;
      border-bottom: 1px solid #30363d;
      padding-bottom: 16px;
    }
    .mascot {
      color: #e5a93c;
      font-family: monospace;
      white-space: pre;
      font-size: 14px;
      line-height: 1.1;
    }
    .title {
      font-size: 24px;
      font-weight: 700;
      color: #f0883e;
    }
    .status-badge {
      display: inline-block;
      padding: 4px 8px;
      background: #238636;
      border-radius: 12px;
      font-size: 12px;
      margin-top: 4px;
    }
    .terminal {
      background: #010409;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px;
      font-family: Consolas, monospace;
      font-size: 13px;
      margin-top: 20px;
      height: 480px;
      overflow-y: auto;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="mascot">
   ▄██████▄   
 ▟███▀▀██▀▀███▙ 
 ▐███ █▗▖█ ▐███▌
  ████▄▄▄▄████ 
 ▜██████████▛  
    ▀██  ██▀   
    </div>
    <div>
      <div class="title">Apex v0.9.0</div>
      <div class="status-badge">Council Operational · Electron Native Desktop</div>
    </div>
  </div>
  <div class="terminal" id="term">
    [System] Initializing Apex Multi-Agent Council...<br/>
    [Consensus] MCTS PUCT Search Engine Active.<br/>
    [Formal] CEGIS Invariant Prover Online.<br/>
    [Enterprise] Zero-Trust DLP & Cryptographic Merkle Tree Engaged.<br/>
    [Memory] GBrain Persistent Knowledge Store Ready.<br/>
    [Browser] Agent Browser Automation Ready.<br/>
  </div>
</body>
</html>
"""
    html_path = os.path.join(target_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    created_files.append(html_path)

    return created_files
