#!/usr/bin/env python3
"""
Apex-Sovereign: Agent Browser Automation Engine
Inspired by vercel-labs/agent-browser (Computer use CLI for AI agents)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
from html.parser import HTMLParser
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request


@dataclasses.dataclass
class BrowserNode:
    ref_id: int
    tag: str
    attrs: Dict[str, str]
    text: str = ""
    children: List[BrowserNode] = dataclasses.field(default_factory=list)
    parent: Optional[BrowserNode] = None

    @property
    def is_interactive(self) -> bool:
        if self.tag in {"a", "button", "input", "select", "textarea", "form"}:
            return True
        if self.attrs.get("role") in {"button", "link", "checkbox", "menuitem", "tab", "textbox"}:
            return True
        if "onclick" in self.attrs:
            return True
        return False

    def get_accessible_label(self) -> str:
        label = self.attrs.get("aria-label") or self.attrs.get("placeholder") or self.attrs.get("title")
        if not label:
            label = self.text.strip()
        if not label and self.attrs.get("name"):
            label = self.attrs.get("name")
        return label or f"<{self.tag}>"


class _BrowserHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ref_counter = 0
        self.root = BrowserNode(ref_id=0, tag="body", attrs={})
        self.current = self.root
        self.nodes_by_ref: Dict[int, BrowserNode] = {0: self.root}
        self.skip_tags = {"script", "style", "noscript", "svg"}
        self._in_skip = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            self._in_skip += 1
            return
        if self._in_skip > 0:
            return

        self.ref_counter += 1
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        node = BrowserNode(
            ref_id=self.ref_counter,
            tag=tag_lower,
            attrs=attr_dict,
            parent=self.current,
        )
        self.nodes_by_ref[node.ref_id] = node
        self.current.children.append(node)
        self.current = node

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self.skip_tags:
            if self._in_skip > 0:
                self._in_skip -= 1
            return
        if self._in_skip > 0:
            return

        if self.current.parent is not None:
            self.current = self.current.parent

    def handle_data(self, data: str) -> None:
        if self._in_skip > 0:
            return
        if self.current:
            self.current.text += data


class AgentBrowserSession:
    """
    Autonomous AI Browser Session.
    Provides snapshotting, accessible element tree generation with reference IDs,
    click/type interaction, and text extraction for agent workflows.
    """

    def __init__(self) -> None:
        self.current_url: str = "about:blank"
        self.history: List[str] = ["about:blank"]
        self.history_index: int = 0
        self.dom_root: Optional[BrowserNode] = None
        self.nodes_by_ref: Dict[int, BrowserNode] = {}
        self.raw_html: str = ""
        self.console_logs: List[str] = []

    def goto(self, url: str, mock_html: Optional[str] = None) -> Dict[str, Any]:
        """Navigate to a URL or load provided HTML mock."""
        start_time = time.time()
        self.current_url = url

        if mock_html is not None:
            self.raw_html = mock_html
        elif url.startswith("http://") or url.startswith("https://"):
            try:
                from ..security.safe_net import safe_http_request
                req = safe_http_request(
                    url,
                    headers={"User-Agent": "Apex-Sovereign-Agent-Browser/3.0.0"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    self.raw_html = resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                self.raw_html = f"<html><body><h1>Navigation Error</h1><p>{str(e)}</p></body></html>"
                self.console_logs.append(f"[ERROR] Failed to fetch {url}: {e}")
        else:
            self.raw_html = "<html><body><h1>Apex Blank Canvas</h1></body></html>"

        # Parse DOM into Accessible Reference Tree
        parser = _BrowserHTMLParser()
        parser.feed(self.raw_html)
        self.dom_root = parser.root
        self.nodes_by_ref = parser.nodes_by_ref

        # Update History
        if self.history_index < len(self.history) - 1:
            self.history = self.history[: self.history_index + 1]
        self.history.append(url)
        self.history_index = len(self.history) - 1

        load_duration_ms = (time.time() - start_time) * 1000
        return {
            "status": 200,
            "url": self.current_url,
            "nodes_count": len(self.nodes_by_ref),
            "duration_ms": round(load_duration_ms, 2),
        }

    def snapshot(self, max_depth: int = 8) -> str:
        """
        Generates an LLM-friendly accessible snapshot tree where interactive
        elements are tagged with [@ref:ID] for deterministic agent actuation.
        """
        if not self.dom_root:
            return "[Empty Document]"

        lines: List[str] = [f"=== Browser Snapshot: {self.current_url} ==="]

        def _traverse(node: BrowserNode, depth: int) -> None:
            if depth > max_depth:
                return

            indent = "  " * depth
            text = node.text.strip()
            if node.is_interactive:
                label = node.get_accessible_label()
                ref_tag = f"[@ref:{node.ref_id}]"
                tag_desc = f"{indent}- {ref_tag} <{node.tag}> {label}"
                if node.tag == "input":
                    val = node.attrs.get("value", "")
                    typ = node.attrs.get("type", "text")
                    tag_desc += f" (type={typ}, value='{val}')"
                elif node.tag == "a":
                    href = node.attrs.get("href", "#")
                    tag_desc += f" -> {href}"
                lines.append(tag_desc)
            elif text and len(text) > 1 and node.tag in {"h1", "h2", "h3", "h4", "p", "li", "span", "td", "th"}:
                lines.append(f"{indent}- <{node.tag}> {text[:120]}")

            for child in node.children:
                _traverse(child, depth + 1)

        _traverse(self.dom_root, 0)
        return "\n".join(lines)

    def click(self, ref_id: int) -> Dict[str, Any]:
        """Simulate agent click on element with @ref:ID."""
        node = self.nodes_by_ref.get(ref_id)
        if not node:
            return {"success": False, "error": f"Element ref:{ref_id} not found"}

        if node.tag == "a" and "href" in node.attrs:
            target_href = node.attrs["href"]
            resolved_url = urllib.parse.urljoin(self.current_url, target_href)
            self.console_logs.append(f"[ACTION] Clicked link @ref:{ref_id} navigating to {resolved_url}")
            return self.goto(resolved_url)

        self.console_logs.append(f"[ACTION] Clicked @ref:{ref_id} <{node.tag}> '{node.get_accessible_label()}'")
        return {"success": True, "ref_id": ref_id, "tag": node.tag, "action": "clicked"}

    def type_text(self, ref_id: int, text: str) -> Dict[str, Any]:
        """Simulate typing text into an input or textarea element."""
        node = self.nodes_by_ref.get(ref_id)
        if not node:
            return {"success": False, "error": f"Element ref:{ref_id} not found"}

        node.attrs["value"] = text
        node.text = text
        self.console_logs.append(f"[ACTION] Typed '{text}' into @ref:{ref_id} <{node.tag}>")
        return {"success": True, "ref_id": ref_id, "value": text}

    def extract_text(self) -> str:
        """Extract clean human-readable text from the page."""
        if not self.dom_root:
            return ""

        extracted = []

        def _walk(node: BrowserNode) -> None:
            if node.text.strip():
                extracted.append(node.text.strip())
            for child in node.children:
                _walk(child)

        _walk(self.dom_root)
        return "\n".join(extracted)

    def render_ascii_viewport(self, width: int = 60) -> str:
        """Render a mini terminal ASCII viewport preview."""
        header = f"┌{'─' * (width - 2)}┐"
        footer = f"└{'─' * (width - 2)}┘"
        title = f" Apex Agent Browser | {self.current_url[:width - 26]} "
        title_line = f"│{title.center(width - 2)}│"
        divider = f"├{'─' * (width - 2)}┤"

        body_lines = []
        for line in self.extract_text().splitlines()[:10]:
            clean = line.strip()[: width - 4]
            if clean:
                body_lines.append(f"│ {clean.ljust(width - 4)} │")

        if not body_lines:
            body_lines.append(f"│ {'[Blank Viewport]'.center(width - 4)} │")

        return "\n".join([header, title_line, divider] + body_lines + [footer])
