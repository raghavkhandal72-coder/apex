"""Apex-Council Autonomous SWE Swarm Subsystem.
5-Role Swarm and end-to-end Issue Resolution Coordinator.
"""

from apex_council.swarm.coordinator import SwarmCoordinator
from apex_council.swarm.roles import (
    ArchitecturalBlueprint,
    RedTeamBreaker,
    ReproductionSuite,
    SovereignGatekeeper,
    StaffArchitect,
    SwarmSolution,
    TestFirstSpeculator,
)

__all__ = [
    "SwarmCoordinator",
    "StaffArchitect",
    "TestFirstSpeculator",
    "RedTeamBreaker",
    "SovereignGatekeeper",
    "ArchitecturalBlueprint",
    "ReproductionSuite",
    "SwarmSolution",
]
