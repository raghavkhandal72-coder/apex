"""Apex-Council Autonomous SWE Swarm Subsystem.
5-Role Swarm, Zero-SDK LLM Router, AST Contracts, Fuzzy Patching, and Autonomous Issue Solver.
"""

from apex_council.swarm.contracts import (
    ContractReport,
    ContractSpecification,
    ContractVerifier,
)
from apex_council.swarm.coordinator import (
    BlindPeerReviewer,
    BrierCalibrationTracker,
    DebateBus,
    DebateRound,
    PeerReviewVote,
    SwarmCoordinator,
)
from apex_council.swarm.fuzzy_patch import (
    AutoImportFixer,
    FuzzyPatchApplier,
    PatchHunk,
    PatchResult,
)
from apex_council.swarm.llm_router import (
    DeterministicMockLLM,
    LLMResponse,
    LLMRouter,
)
from apex_council.swarm.roles import (
    ArchitecturalBlueprint,
    RedTeamBreaker,
    ReproductionSuite,
    SovereignGatekeeper,
    StaffArchitect,
    SwarmSolution,
    TestFirstSpeculator,
)
from apex_council.swarm.solver import AutonomousIssueSolver, SolveReport

__all__ = [
    "SwarmCoordinator",
    "StaffArchitect",
    "TestFirstSpeculator",
    "RedTeamBreaker",
    "SovereignGatekeeper",
    "ArchitecturalBlueprint",
    "ReproductionSuite",
    "SwarmSolution",
    "AutonomousIssueSolver",
    "SolveReport",
    "LLMRouter",
    "LLMResponse",
    "DeterministicMockLLM",
    "ContractSpecification",
    "ContractVerifier",
    "ContractReport",
    "FuzzyPatchApplier",
    "PatchHunk",
    "PatchResult",
    "AutoImportFixer",
    "BlindPeerReviewer",
    "PeerReviewVote",
    "DebateBus",
    "DebateRound",
    "BrierCalibrationTracker",
]
