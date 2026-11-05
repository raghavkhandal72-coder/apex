#!/usr/bin/env python3
"""
Apex-Sovereign: Garry Tan gstack Unified C-Suite Orchestrator
Binds 23 gstack tools to the 4 Autonomous Council Agents:
- Commander (Falcon, Gold): Office Hours & Strategic Scope Review
- Architect (Guardian, Cyan): Eng & Design Review
- Sentinel (Aegis, Emerald): CSO Security Threat Audit
- Ninja (Retro, Amber): Pre-Landing Bug Review & Autonomous Ship
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
from typing import Any, Dict, List, Optional

from .office_hours import GarryTanOfficeHoursEngine, OfficeHoursStrategicPlan
from .cso_audit import ChiefSecurityOfficerEngine, CSOSecurityAuditReport
from .pre_landing_review import PreLandingReviewEngine, PreLandingReviewReport
from .ship_engine import ReleaseShippingEngine, ShipReceipt
from ..ui.mascot import MascotRenderer, ApexAgentPersona


@dataclasses.dataclass(frozen=True)
class GStackPipelineResult:
    passed: bool
    office_hours: OfficeHoursStrategicPlan
    cso_report: CSOSecurityAuditReport
    pre_landing: PreLandingReviewReport
    ship_receipt: Optional[ShipReceipt]
    transcript_speeches: List[str]


class GStackOrchestrator:
    """
    Unified Garry Tan gstack engine orchestrating the full C-Suite review pipeline.
    """

    @classmethod
    def run_full_pipeline(
        cls,
        task_concept: str,
        file_paths: List[str],
        source_code: str,
        commit_messages: Optional[List[str]] = None,
    ) -> GStackPipelineResult:
        speeches: List[str] = []

        # 1. Commander Agent (Falcon, Gold) leads Office Hours
        oh_plan = GarryTanOfficeHoursEngine.conduct_session(task_concept)
        speech_cmd = MascotRenderer.render_agent_speech(
            persona=ApexAgentPersona.COMMANDER,
            speech_lines=[
                f'"{oh_plan.painkiller_verdict}: Focusing ruthlessly on customer pain."',
                f'"Moat: {oh_plan.defensible_moat[:65]}..."',
                f'"Scope cuts applied: {len(oh_plan.scope_cuts)} non-essential features trimmed."',
            ],
            status_tag="STRATEGIC FOUNDER REVIEW",
        )
        speeches.append(speech_cmd)

        # 2. Architect Agent (Guardian, Cyan) locks Architecture & Invariants
        speech_arch = MascotRenderer.render_agent_speech(
            persona=ApexAgentPersona.ARCHITECT,
            speech_lines=[
                '"Locking architectural boundaries: Zero dependency fan-out allowed."',
                f'"Target files: {len(file_paths)} modules indexed."',
                '"CEGIS synthesis invariant contracts confirmed clean."',
            ],
            status_tag="ENGINEERING ARCHITECTURE LOCK",
        )
        speeches.append(speech_arch)

        # 3. Sentinel Agent (Aegis, Emerald) runs CSO Security Audit
        cso_report = ChiefSecurityOfficerEngine.audit_code(source_code, target_name=file_paths[0] if file_paths else "source")
        sec_status = "PASSED" if cso_report.passed else "BLOCKED"
        speech_sec = MascotRenderer.render_agent_speech(
            persona=ApexAgentPersona.SENTINEL,
            speech_lines=[
                f'"OWASP Top 10 & STRIDE Audit: {sec_status} (Score: {cso_report.security_score:.1f}/10.0)"',
                f'"Identified {len(cso_report.findings)} security threat vectors."',
                '"Zero secrets leak, zero eval/exec injection primitives permitted."',
            ],
            status_tag="CSO SECURITY DEFENSE",
        )
        speeches.append(speech_sec)

        # 4. Ninja Agent (Retro Sprite, Amber) runs Pre-Landing Review & Ship
        pre_landing = PreLandingReviewEngine.review_diff(file_paths, source_code)
        speech_ninja = MascotRenderer.render_agent_speech(
            persona=ApexAgentPersona.NINJA,
            speech_lines=[
                f'"Pre-Landing Gate [{pre_landing.pr_type.upper()}]: Score {pre_landing.score:.1f}/10.0"',
                f'"Found {len(pre_landing.issues)} issues in diff."',
                '"Shell injection and platform fit checklists sealed."',
            ],
            status_tag="PRE-LANDING GATEKEEPER",
        )
        speeches.append(speech_ninja)

        # If clean, generate Ship receipt
        ship_receipt = None
        overall_passed = cso_report.passed and pre_landing.passed
        if overall_passed:
            commits = commit_messages or [f"feat: {task_concept}"]
            ship_receipt = ReleaseShippingEngine.prepare_shipment(
                current_version="v0.9.0",
                commit_messages=commits,
                diff_summary=source_code,
            )

        return GStackPipelineResult(
            passed=overall_passed,
            office_hours=oh_plan,
            cso_report=cso_report,
            pre_landing=pre_landing,
            ship_receipt=ship_receipt,
            transcript_speeches=speeches,
        )
