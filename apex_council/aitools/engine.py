#!/usr/bin/env python3
"""
Apex Awesome-AITools Engine: Offline Search, Discovery, & Recommendation.
100% Pure Python Standard Library (pip = 0).
Integrates ikaijua/Awesome-AITools (262+ curated tools across 38 categories).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..ui.terminal import TerminalColors

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@dataclass
class AITool:
    name: str
    category: str
    description: str
    url: str
    fees: str

    @property
    def desc(self) -> str:
        return self.description

    @property
    def is_free(self) -> bool:
        f = (self.fees or "").lower()
        return "free" in f or "open source" in f or "0" in f or f == ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "url": self.url,
            "fees": self.fees,
        }


class AwesomeAIToolsEngine:
    """Offline search and recommendation engine for Awesome AI Tools."""

    RAW_URL = "https://raw.githubusercontent.com/ikaijua/Awesome-AITools/main/README.md"

    def __init__(self, custom_readme: Optional[Path | str] = None) -> None:
        self.custom_readme = Path(custom_readme) if custom_readme else None
        self._categories: List[str] = []
        self._tools: List[AITool] = []
        self._load_data()

    @property
    def tools(self) -> List[AITool]:
        return self._tools

    @property
    def categories(self) -> List[str]:
        return self._categories

    def _load_data(self) -> None:
        # 1. Check local scratch directory or custom path first
        candidates = [
            self.custom_readme,
            Path(__file__).resolve().parent.parent.parent.parent / "scratch" / "Awesome-AITools" / "README.md",
            Path.home() / ".apex" / "aitools" / "README.md",
        ]
        loaded_from_disk = False
        for cand in candidates:
            if cand and cand.exists():
                try:
                    self._parse_markdown(cand.read_text(encoding="utf-8"))
                    loaded_from_disk = True
                    break
                except Exception:
                    pass

        # 2. Fall back to embedded compressed catalog data
        if not loaded_from_disk or not self._tools:
            try:
                from .catalog_data import load_catalog_data
                data = load_catalog_data()
                self._categories = data.get("c", [])
                raw_tools = data.get("t", [])
                self._tools = [
                    AITool(
                        name=re.sub(r"[^\x00-\x7F]+", "", t[0]).strip(),
                        category=self._categories[t[1]] if t[1] < len(self._categories) else "General",
                        description=re.sub(r"[^\x00-\x7F]+", "", t[2]).strip(),
                        url=t[3],
                        fees=re.sub(r"[^\x00-\x7F]+", "", t[4]).strip(),
                    )
                    for t in raw_tools
                ]
            except Exception:
                pass

    def _parse_markdown(self, text: str) -> None:
        sections = re.split(r"\n###\s+", text)
        categories: List[str] = []
        tools: List[AITool] = []

        for sec in sections[1:]:
            lines = sec.splitlines()
            cat_name = lines[0].strip()
            if cat_name not in categories:
                categories.append(cat_name)

            for line in lines[1:]:
                if line.startswith("|") and not line.startswith("| Name |") and not line.startswith("| --- |"):
                    parts = [p.strip() for p in line.strip().strip("|").split("|")]
                    if len(parts) >= 4:
                        name = re.sub(r"<[^>]+>", "", parts[0])
                        name = re.sub(r"[^\x00-\x7F]+", "", name).strip()
                        urls = re.findall(r"https?://[^\s\)\"\'>]+", parts[2])
                        url = urls[0] if urls else ""
                        desc = re.sub(r"<[^>]+>", " ", parts[1]).replace("\n", " ")
                        desc = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", desc)
                        desc = re.sub(r"[^\x00-\x7F]+", "", desc)
                        desc = re.sub(r"\s+", " ", desc).strip()
                        if len(desc) > 160:
                            desc = desc[:157] + "..."
                        fees = re.sub(r"<[^>]+>", "", parts[3])
                        fees = re.sub(r"[^\x00-\x7F]+", "", fees).strip()
                        tools.append(AITool(name=name, category=cat_name, description=desc, url=url, fees=fees))

        if tools:
            self._categories = categories
            self._tools = tools

    @property
    def total_tools(self) -> int:
        return len(self._tools)

    @property
    def total_categories(self) -> int:
        return len(self._categories)

    def list_categories(self) -> List[Tuple[str, int]]:
        counts: Dict[str, int] = {}
        for t in self._tools:
            counts[t.category] = counts.get(t.category, 0) + 1
        return sorted(counts.items(), key=lambda x: -x[1])

    def get_category_tools(self, category_query: str) -> List[AITool]:
        q = category_query.lower()
        matched_cat = next((c for c in self._categories if q in c.lower()), None)
        if not matched_cat:
            return []
        return [t for t in self._tools if t.category == matched_cat]

    def get_tool(self, name_query: str) -> Optional[AITool]:
        q = name_query.lower()
        exact = next((t for t in self._tools if t.name.lower() == q), None)
        if exact:
            return exact
        return next((t for t in self._tools if q in t.name.lower()), None)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        free_only: bool = False,
        limit: int = 12,
    ) -> List[AITool]:
        tokens = [k.lower() for k in re.split(r"\s+", query.strip()) if k]
        if not tokens and not category and not free_only:
            return self._tools[:limit]

        scored: List[Tuple[float, AITool]] = []
        for t in self._tools:
            if category and category.lower() not in t.category.lower():
                continue
            if free_only and not ("free" in t.fees.lower() or "mit" in t.fees.lower() or "apache" in t.fees.lower()):
                continue

            score = 0.0
            name_lower = t.name.lower()
            cat_lower = t.category.lower()
            desc_lower = t.description.lower()

            for tok in tokens:
                if tok == name_lower:
                    score += 15.0
                elif tok in name_lower:
                    score += 7.0
                if tok in cat_lower:
                    score += 4.0
                if tok in desc_lower:
                    score += 2.0

            if not tokens or score > 0:
                scored.append((score, t))

        scored.sort(key=lambda x: -x[0])
        return [item[1] for item in scored[:limit]]

    def recommend(self, spec: str, limit: int = 5) -> List[AITool]:
        """Recommends top tools matching an architecture, engineering task, or spec."""
        s = spec.lower()
        matched_terms = []
        term_map = {
            "code review": ["review", "pr", "diff", "lint", "analyzer"],
            "coding agent": ["agent", "terminal", "cli", "ide", "coder"],
            "browser automation": ["browser", "scrape", "crawl", "playwright", "puppeteer"],
            "speech": ["tts", "voice", "audio", "speech", "transcribe"],
            "image": ["image", "diffusion", "art", "ui design", "poster"],
            "video": ["video", "animation", "motion"],
            "llm inference": ["inference", "ollama", "vllm", "llama", "local"],
            "agent memory": ["memory", "vector", "rag", "embeddings"],
            "security": ["security", "audit", "cwe", "vuln", "reverse"],
            "finance": ["quant", "finance", "trading", "crypto", "investment"],
        }
        for cat_key, words in term_map.items():
            if any(w in s for w in words):
                matched_terms.append(cat_key)

        search_query = " ".join(matched_terms) if matched_terms else spec
        return self.search(search_query, limit=limit)

    def render_summary(self) -> str:
        c = TerminalColors
        lines = [
            "\n" + c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            c.CYAN + c.BOLD + f"  🚀  APEX SOVEREIGN: AWESOME AI TOOLS REGISTRY & ADVISOR ENGINE" + c.RESET,
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}Total AI Tools  :{c.RESET} {c.GOLD}{self.total_tools}{c.RESET} curated tools",
            f"  {c.BOLD}Categories      :{c.RESET} {c.NEON_GREEN}{self.total_categories}{c.RESET} active domains",
            f"  {c.BOLD}Source Upstream :{c.RESET} ikaijua/Awesome-AITools (GitHub)",
            f"  {c.BOLD}Execution Mode  :{c.RESET} {c.NEON_GREEN}100% Offline Fast Search + Live Sync Capability{c.RESET}",
            "",
            f"  {c.BOLD}Top Categories:{c.RESET}",
        ]
        for cat, cnt in self.list_categories()[:8]:
            lines.append(f"    • {c.CYAN}{cat:<36}{c.RESET} ({cnt} tools)")

        lines.extend([
            "",
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}Quick Commands:{c.RESET}",
            f"    apex aitools search <query>    Search across 260+ AI tools (e.g. 'coding agent')",
            f"    apex aitools categories        List all 38 categories with counts",
            f"    apex aitools list <category>   List tools in a specific category",
            f"    apex aitools info <name>       Show detailed info & links for a tool",
            f"    apex aitools recommend <spec>  Get tool recommendations for your coding spec",
            f"    apex aitools sync              Sync latest tools from GitHub upstream",
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET + "\n",
        ])
        return "\n".join(lines)

    def render_table(self, tools: List[AITool], title: str = "Search Results") -> str:
        c = TerminalColors
        if not tools:
            return f"\n{c.GOLD}[!] No matching AI tools found.{c.RESET}\n"

        lines = [
            "\n" + c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            c.CYAN + c.BOLD + f"  🎯  AWESOME AI TOOLS: {title.upper()} ({len(tools)} Matches)" + c.RESET,
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}{'NAME':<24} {'CATEGORY':<24} {'FEES':<12} {'URL'}{c.RESET}",
            "  " + "-" * 75,
        ]
        for t in tools:
            lines.append(f"  {c.NEON_GREEN}{t.name[:23]:<24}{c.RESET} {c.CYAN}{t.category[:23]:<24}{c.RESET} {c.GOLD}{t.fees[:11]:<12}{c.RESET} {c.DIM}{t.url[:24]}{c.RESET}")
            lines.append(f"    {c.DIM}↳ {t.description[:85]}{c.RESET}")
        lines.append(c.CYAN + c.BOLD + "===============================================================================" + c.RESET + "\n")
        return "\n".join(lines)

    def render_tool_detail(self, tool: AITool) -> str:
        c = TerminalColors
        lines = [
            "\n" + c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            c.CYAN + c.BOLD + f"  🔍  AI TOOL DOSSIER: {tool.name.upper()}" + c.RESET,
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET,
            f"  {c.BOLD}Name        :{c.RESET} {c.NEON_GREEN}{tool.name}{c.RESET}",
            f"  {c.BOLD}Category    :{c.RESET} {c.CYAN}{tool.category}{c.RESET}",
            f"  {c.BOLD}Pricing     :{c.RESET} {c.GOLD}{tool.fees}{c.RESET}",
            f"  {c.BOLD}Website/Repo:{c.RESET} {c.CYAN}{tool.url or 'N/A'}{c.RESET}",
            "",
            f"  {c.BOLD}Description & Capabilities:{c.RESET}",
            f"    {tool.description}",
            "",
            c.CYAN + c.BOLD + "===============================================================================" + c.RESET + "\n",
        ]
        return "\n".join(lines)

    def sync(self) -> Tuple[bool, str]:
        """Pulls latest README.md from GitHub or local scratch clone."""
        # 1. Check local scratch repository first
        scratch_readme = Path(__file__).resolve().parent.parent.parent.parent / "scratch" / "Awesome-AITools" / "README.md"
        if scratch_readme.exists():
            try:
                self._parse_markdown(scratch_readme.read_text(encoding="utf-8"))
                return True, f"Successfully synced {len(self._tools)} tools from local Awesome-AITools scratch repository."
            except Exception as e:
                pass

        # 2. Try fetching from GitHub
        try:
            req = urllib.request.Request(self.RAW_URL, headers={"User-Agent": "Apex-Awesome-AITools"})
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                text = resp.read().decode("utf-8")
                self._parse_markdown(text)
                cache_dir = Path.home() / ".apex" / "aitools"
                cache_dir.mkdir(parents=True, exist_ok=True)
                (cache_dir / "README.md").write_text(text, encoding="utf-8")
                return True, f"Successfully synced {len(self._tools)} tools directly from GitHub upstream."
        except Exception as e:
            return False, f"Sync failed: {e}. Using embedded offline catalog ({len(self._tools)} tools available)."


def handle_aitools_cli(args_list: List[str]) -> int:
    """Dispatches CLI: apex aitools [search|categories|list|info|recommend|sync]."""
    engine = AwesomeAIToolsEngine()

    if not args_list:
        print(engine.render_summary())
        return 0

    sub = args_list[0].lower()

    if sub in {"cat", "cats", "categories"}:
        c = TerminalColors
        print("\n" + c.CYAN + c.BOLD + "===============================================================================" + c.RESET)
        print(c.CYAN + c.BOLD + f"  📂  AWESOME AI TOOLS: ALL {engine.total_categories} CATEGORIES" + c.RESET)
        print(c.CYAN + c.BOLD + "===============================================================================" + c.RESET)
        for cat, cnt in engine.list_categories():
            print(f"  • {c.CYAN}{cat:<42}{c.RESET} {c.GOLD}{cnt:>3} tools{c.RESET}")
        print(c.CYAN + c.BOLD + "===============================================================================" + c.RESET + "\n")
        return 0

    if sub in {"list", "ls"}:
        cat_query = " ".join(args_list[1:]) if len(args_list) > 1 else ""
        if not cat_query:
            print("[!] Please specify a category. Run 'apex aitools categories' to view available domains.")
            return 1
        tools = engine.get_category_tools(cat_query)
        print(engine.render_table(tools, title=f"Category: {cat_query}"))
        return 0

    if sub in {"search", "find", "query"}:
        free_only = "--free" in args_list
        clean_args = [a for a in args_list[1:] if a != "--free"]
        q = " ".join(clean_args)
        tools = engine.search(q, free_only=free_only, limit=15)
        print(engine.render_table(tools, title=f"Query: '{q}'{' (Free Only)' if free_only else ''}"))
        return 0

    if sub in {"info", "show", "view", "dossier"}:
        if len(args_list) < 2:
            print("[!] Please specify a tool name: apex aitools info <name>")
            return 1
        name = " ".join(args_list[1:])
        tool = engine.get_tool(name)
        if not tool:
            print(f"[!] Tool '{name}' not found in registry. Run 'apex aitools search {name}' to find related tools.")
            return 1
        print(engine.render_tool_detail(tool))
        return 0

    if sub in {"recommend", "rec", "advise"}:
        spec = " ".join(args_list[1:]) if len(args_list) > 1 else "coding agent for developer productivity"
        tools = engine.recommend(spec, limit=8)
        print(engine.render_table(tools, title=f"Recommendations for: '{spec}'"))
        return 0

    if sub in {"sync", "update", "pull"}:
        print("• Syncing Awesome-AITools registry...")
        ok, msg = engine.sync()
        if ok:
            print(f"✓ {msg}")
            return 0
        else:
            print(f"[!] {msg}")
            return 1

    # Treat unknown first argument as search query
    q = " ".join(args_list)
    tools = engine.search(q, limit=12)
    print(engine.render_table(tools, title=f"Search: '{q}'"))
    return 0
