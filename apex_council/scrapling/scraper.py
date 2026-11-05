#!/usr/bin/env python3
"""
Apex-Sovereign: Scrapling Resilient Web Scraping & DOM Engine
Inspired by D4Vinci/Scrapling (Undetectable & Fast Web Scraper)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
from html.parser import HTMLParser
import os
import re
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.parse


@dataclasses.dataclass
class DOMElement:
    tag: str
    attrs: Dict[str, str]
    children: List[DOMElement] = dataclasses.field(default_factory=list)
    items: List[Any] = dataclasses.field(default_factory=list)
    parent: Optional[DOMElement] = None
    text: str = ""

    def get_attr(self, name: str, default: str = "") -> str:
        return self.attrs.get(name, default)

    def has_class(self, class_name: str) -> bool:
        classes = self.attrs.get("class", "").split()
        return class_name in classes

    def get_text(self, recursive: bool = True) -> str:
        if not recursive:
            return self.text.strip()
        texts: List[str] = []
        for it in self.items:
            if isinstance(it, str):
                if it.strip():
                    texts.append(it.strip())
            elif isinstance(it, DOMElement):
                child_text = it.get_text(recursive=True)
                if child_text:
                    texts.append(child_text)
        if not texts and self.text:
            texts.append(self.text.strip())
        return " ".join(texts)

    def find_all(self, tag: Optional[str] = None, class_name: Optional[str] = None) -> List[DOMElement]:
        results: List[DOMElement] = []
        if (tag is None or self.tag == tag) and (class_name is None or self.has_class(class_name)):
            results.append(self)
        for child in self.children:
            results.extend(child.find_all(tag=tag, class_name=class_name))
        return results


class _TreeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = DOMElement(tag="root", attrs={})
        self.current = self.root
        self.skip_tags = {"script", "style", "noscript", "svg"}
        self._in_skip = 0

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag.lower() in self.skip_tags:
            self._in_skip += 1
            return
        if self._in_skip > 0:
            return

        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        elem = DOMElement(tag=tag.lower(), attrs=attr_dict, parent=self.current)
        self.current.children.append(elem)
        self.current.items.append(elem)
        self.current = elem

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.skip_tags:
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
            self.current.items.append(data)


@dataclasses.dataclass
class ScrapeResult:
    target: str
    status_code: int
    raw_html: str
    title: str
    text: str

    def html_to_markdown(self) -> str:
        return ScraplingEngine.html_to_markdown(self.raw_html)

    def extract_tables(self) -> List[List[Dict[str, str]]]:
        return ScraplingEngine.extract_tables(self.raw_html)


class ScraplingEngine:
    """
    Resilient web scraping and DOM extraction engine.
    Converts arbitrary HTML to clean structured Markdown and extracts tables.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ]

    def scrape(self, target: str) -> ScrapeResult:
        """Scrapes a URL, local HTML file, or raw HTML string."""
        raw_html = ""
        status_code = 200

        if target.startswith("http://") or target.startswith("https://"):
            try:
                req = urllib.request.Request(
                    target,
                    headers={"User-Agent": self.USER_AGENTS[0], "Accept": "text/html,application/xhtml+xml"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_html = resp.read().decode("utf-8", errors="replace")
                    status_code = resp.status
            except Exception as e:
                raw_html = f"<html><body><h1>Scrape Error</h1><p>{str(e)}</p></body></html>"
                status_code = 500
        elif os.path.isfile(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    raw_html = f.read()
            except Exception as e:
                raw_html = f"<html><body><p>{str(e)}</p></body></html>"
                status_code = 500
        else:
            raw_html = target

        root = self.parse_html(raw_html)
        title_elems = root.find_all(tag="title")
        title = title_elems[0].get_text() if title_elems else (target[:40] if "<" not in target else "Scraped Document")
        text = root.get_text()

        return ScrapeResult(
            target=target,
            status_code=status_code,
            raw_html=raw_html,
            title=title,
            text=text,
        )

    @classmethod
    def parse_html(cls, html_content: str) -> DOMElement:
        """Parses HTML into a navigable DOM tree."""
        parser = _TreeHTMLParser()
        parser.feed(html_content)
        return parser.root

    @classmethod
    def html_to_markdown(cls, html_content: str) -> str:
        """Strips HTML boilerplate and converts to clean readable Markdown."""
        root = cls.parse_html(html_content)
        lines: List[str] = []

        def walk(elem: DOMElement):
            tag = elem.tag
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                level = int(tag[1])
                text = elem.get_text()
                if text:
                    lines.append(f"\n{'#' * level} {text}\n")
            elif tag == "p":
                text = elem.get_text()
                if text:
                    lines.append(f"\n{text}\n")
            elif tag in {"li"}:
                text = elem.get_text()
                if text:
                    lines.append(f"- {text}")
            elif tag in {"code", "pre"}:
                text = elem.get_text()
                if text:
                    lines.append(f"`{text}`")
            elif tag == "a":
                href = elem.get_attr("href")
                text = elem.get_text() or href
                if href and text:
                    lines.append(f"[{text}]({href})")
            else:
                for child in elem.children:
                    walk(child)

        walk(root)
        cleaned = "\n".join(lines)
        return re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    @classmethod
    def extract_tables(cls, html_content: str) -> List[List[Dict[str, str]]]:
        """Extracts HTML tables as structured rows of dictionaries."""
        root = cls.parse_html(html_content)
        tables = root.find_all(tag="table")
        parsed_tables: List[List[Dict[str, str]]] = []

        for table in tables:
            headers: List[str] = []
            th_elems = table.find_all(tag="th")
            if th_elems:
                headers = [th.get_text() for th in th_elems]

            rows_data: List[Dict[str, str]] = []
            tr_elems = table.find_all(tag="tr")
            for tr in tr_elems:
                tds = [td.get_text() for td in tr.find_all(tag="td")]
                if tds:
                    if headers and len(headers) == len(tds):
                        row_dict = {headers[i]: tds[i] for i in range(len(headers))}
                    else:
                        row_dict = {f"col_{i}": tds[i] for i in range(len(tds))}
                    rows_data.append(row_dict)

            if rows_data:
                parsed_tables.append(rows_data)

        return parsed_tables
