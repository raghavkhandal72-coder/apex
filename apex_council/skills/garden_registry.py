#!/usr/bin/env python3
"""
Apex-Sovereign: Garden Skills & Agent Skills Execution Engine
Inspired by ConardLi/garden-skills and google/skills
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import os
import re
from typing import Any, Callable, Dict, List, Optional


@dataclasses.dataclass
class GardenSkill:
    name: str
    description: str
    author: str
    version: str
    tags: List[str]
    parameters: Dict[str, str]
    system_prompt: str
    handler: Optional[Callable[..., Any]] = None


class GardenSkillsRegistry:
    """
    Curated Agent Skills Registry & Executor.
    Parses SKILL.md specs, manages runtime execution, and exposes specialized agent capabilities.
    """

    def __init__(self, custom_skills_dir: Optional[str] = None) -> None:
        self.custom_skills_dir = custom_skills_dir or ".apex/skills"
        self._skills: Dict[str, GardenSkill] = {}
        self._load_builtin_skills()
        if os.path.exists(self.custom_skills_dir):
            self.load_from_directory(self.custom_skills_dir)

    def _load_builtin_skills(self) -> None:
        """Register the built-in frontier agent skills."""
        self.register(GardenSkill(
            name="code-reviewer",
            description="Deep static review of code for bugs, logic gaps, and edge cases.",
            author="Apex Council",
            version="1.0.0",
            tags=["code", "quality", "review"],
            parameters={"code": "Source code text to analyze", "language": "Programming language (default: python)"},
            system_prompt="You are a principal engineer conducting an uncompromising, meticulous code review.",
        ))

        self.register(GardenSkill(
            name="architecture-prover",
            description="Formal boundary verification using CEGIS and invariant synthesis.",
            author="Apex Council",
            version="1.0.0",
            tags=["formal", "architecture", "cegis"],
            parameters={"spec": "Component specification or invariant formula"},
            system_prompt="You are a formal methods expert proving safety and liveness invariants.",
        ))

        self.register(GardenSkill(
            name="security-sentinel",
            description="Zero-Trust DLP, credential leak detection, and AST vulnerability scanner.",
            author="Apex Council",
            version="1.0.0",
            tags=["security", "dlp", "audit"],
            parameters={"target_path": "Path to scan for secrets and vulnerabilities"},
            system_prompt="You are a Chief Security Officer auditing for OWASP Top 10 and secret leakage.",
        ))

        self.register(GardenSkill(
            name="web-scraper",
            description="Resilient DOM extraction and HTML-to-Markdown synthesis.",
            author="Apex Council",
            version="1.0.0",
            tags=["web", "scraping", "markdown"],
            parameters={"url": "Web address to scrape", "extract_tables": "Boolean flag for tabular extraction"},
            system_prompt="You are an autonomous web intelligence agent extracting clean structured data.",
        ))

        self.register(GardenSkill(
            name="cloud-tester",
            description="Zero-cost AWS S3, SQS, and DynamoDB cloud emulator verification.",
            author="Apex Council",
            version="1.0.0",
            tags=["cloud", "aws", "floci"],
            parameters={"service": "AWS service to emulate (s3, sqs, dynamo)", "action": "Action to test"},
            system_prompt="You are a Cloud Infrastructure Architect verifying serverless deployments hermetically.",
        ))

    def register(self, skill: GardenSkill) -> None:
        self._skills[skill.name.lower()] = skill

    def get_skill(self, name: str) -> Optional[GardenSkill]:
        return self._skills.get(name.lower())

    def list_skills(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for s in self._skills.values():
            if tag and tag.lower() not in [t.lower() for t in s.tags]:
                continue
            results.append({
                "name": s.name,
                "description": s.description,
                "author": s.author,
                "version": s.version,
                "tags": s.tags,
                "parameters": s.parameters,
            })
        return sorted(results, key=lambda x: x["name"])

    def parse_skill_md(self, markdown_content: str) -> Optional[GardenSkill]:
        """Parses a SKILL.md file with YAML-like frontmatter."""
        name = "custom-skill"
        desc = ""
        author = "community"
        version = "1.0.0"
        tags = []
        params = {}

        # Look for YAML frontmatter between --- and ---
        fm_match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", markdown_content, re.DOTALL)
        body = markdown_content
        if fm_match:
            fm_text = fm_match.group(1)
            body = fm_match.group(2)
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k == "name":
                        name = v
                    elif k == "description":
                        desc = v
                    elif k == "author":
                        author = v
                    elif k == "version":
                        version = v
                    elif k == "tags":
                        tags = [t.strip() for t in v.strip("[]").split(",") if t.strip()]

        if not desc:
            # First non-header line of body
            for line in body.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    desc = line
                    break

        return GardenSkill(
            name=name,
            description=desc or "Custom Garden Skill",
            author=author,
            version=version,
            tags=tags or ["custom"],
            parameters=params,
            system_prompt=body.strip(),
        )

    def load_from_directory(self, dir_path: str) -> int:
        count = 0
        if not os.path.isdir(dir_path):
            return 0
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower() == "skill.md" or file.endswith(".skill.md"):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        skill = self.parse_skill_md(content)
                        if skill:
                            self.register(skill)
                            count += 1
                    except Exception:
                        pass
        return count

    def execute_skill(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Executes a registered skill with given arguments."""
        skill = self.get_skill(name)
        if not skill:
            return {"success": False, "error": f"Skill '{name}' not found in Garden registry"}

        if skill.handler:
            try:
                res = skill.handler(**kwargs)
                return {"success": True, "result": res, "skill": skill.name}
            except Exception as e:
                return {"success": False, "error": str(e), "skill": skill.name}

        # Default prompt compilation execution
        compiled_prompt = f"### System Context\n{skill.system_prompt}\n\n### Inputs\n"
        for k, v in kwargs.items():
            compiled_prompt += f"- **{k}**: {v}\n"

        return {
            "success": True,
            "skill": skill.name,
            "description": skill.description,
            "compiled_prompt": compiled_prompt,
            "inputs": kwargs,
        }
