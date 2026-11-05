#!/usr/bin/env python3
"""
Apex: Startup Founder Office Hours & Strategic Review
Inspired by garrytan/gstack (office-hours / plan-ceo-review concepts)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, List, Optional


@dataclasses.dataclass(frozen=True)
class OfficeHoursStrategicPlan:
    product_name: str
    problem_statement: str
    painkiller_verdict: str  # "PAINKILLER (High Urgency)" | "VITAMIN (Low Urgency)"
    target_users: List[str]
    leverage_multiple: str  # e.g. "10x Leverage via Pure Python Zero-Deps"
    defensible_moat: str
    scope_cuts: List[str]
    core_milestones: List[str]
    design_doc_markdown: str


class GarryTanOfficeHoursEngine:
    """
    Simulates Garry Tan (YC CEO) Founder Office Hours.
    Challenges incremental thinking, cuts bloat, and drafts a sharp design doc.
    """

    @classmethod
    def conduct_session(
        cls,
        raw_concept: str,
        target_audience: Optional[str] = None,
    ) -> OfficeHoursStrategicPlan:
        concept_lower = raw_concept.lower()

        # 1. Evaluate Painkiller vs Vitamin
        is_painkiller = any(w in concept_lower for w in ["broken", "slow", "fail", "bug", "security", "expensive", "critical", "crash"])
        painkiller = "PAINKILLER (Must-Have Fix)" if is_painkiller else "VITAMIN (Enhancement - Needs Urgency Injection)"

        # 2. Extract product title
        words = raw_concept.split()
        product_name = " ".join(words[:4]).strip(".,;:").title()

        # 3. Identify Scope Cuts (Ruthless YC Prioritization)
        scope_cuts = [
            "Cut 3rd-party SaaS integrations for v1 (keep core self-contained).",
            "Eliminate custom CSS framework dependencies (use semantic zero-dep styles).",
            "Postpone multi-tenant billing until single-player workflow is verified.",
        ]

        # 4. Define Moat
        moat = "Zero-dependency pure Python runtime + cryptographic verification proofs (cannot be broken by package supply-chain attacks)."

        # 5. Core Milestones (Thin Vertical Slice)
        milestones = [
            "Milestone 1: End-to-end working terminal CLI prototype in under 200 lines.",
            "Milestone 2: Automated unit test harness verifying 100% test pass.",
            "Milestone 3: Single-file executable (.pyz) compiled and distributed.",
        ]

        # 6. Synthesize Design Doc
        doc_md = f"""# Strategic Design Doc: {product_name}
**Review Framework:** Startup Founder Office Hours (Apex Council, inspired by gstack)
**Classification:** {painkiller}

## 1. Problem Statement
{raw_concept}

## 2. Target Audience
{target_audience or "Autonomous software engineers, tech leads, and founders shipping high-leverage code."}

## 3. The 10x Advantage & Defensible Moat
{moat}

## 4. Scope Trimming (What We Are NOT Building in v1)
""" + "\n".join(f"- {c}" for c in scope_cuts) + f"""

## 5. Core Execution Milestones
""" + "\n".join(f"{i+1}. {m}" for i, m in enumerate(milestones)) + "\n"

        return OfficeHoursStrategicPlan(
            product_name=product_name,
            problem_statement=raw_concept,
            painkiller_verdict=painkiller,
            target_users=[target_audience or "Engineers & Founders"],
            leverage_multiple="10x Leverage via Zero-Dep Runtime",
            defensible_moat=moat,
            scope_cuts=scope_cuts,
            core_milestones=milestones,
            design_doc_markdown=doc_md,
        )
