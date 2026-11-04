"""Apex-Sovereign Autonomous Specialist Engineering Swarm.
100% Pure Python Standard Library | Zero Dependencies | FAANG-Grade Autonomous Roles.

Roles:
1. PerformanceOptimizer: Latency, Opcode & Memory Profiler + AST Loop Optimizer
2. ChaosResilienceEngineer: Fault Injection SRE (Sockets, Disks, OOM, Network Jitter)
3. AppSecPenetrationTester: AST Taint Propagation Analyzer + Secure Auto-Remediator
4. DatabaseArchitect: N+1 Detection, SQLite WAL/Timeout Tuner, Index Synthesizer
5. CodebaseModernizer: AST Codemodder (Pathlib, Type Unions, Pattern Matching)
6. ReleaseCaptain: API Surface Differ, SemVer Bumper, and Changelog Chronicler
"""

from apex_council.swarm.specialists.appsec_engineer import (
    AppSecAuditReport,
    AppSecPenetrationTester,
    TaintFlow,
)
from apex_council.swarm.specialists.chaos_engineer import (
    ChaosExperimentResult,
    ChaosReport,
    ChaosResilienceEngineer,
)
from apex_council.swarm.specialists.codebase_modernizer import (
    CodebaseModernizer,
    ModernizationReport,
)
from apex_council.swarm.specialists.database_architect import (
    DatabaseArchitect,
    DatabaseArchitectureReport,
    QueryAntipattern,
)
from apex_council.swarm.specialists.performance_engineer import (
    PerformanceOptimizer,
    PerformanceReport,
)
from apex_council.swarm.specialists.release_captain import (
    APISymbolDelta,
    ReleaseCaptain,
    ReleaseReport,
)

__all__ = [
    "PerformanceOptimizer",
    "PerformanceReport",
    "ChaosResilienceEngineer",
    "ChaosReport",
    "ChaosExperimentResult",
    "AppSecPenetrationTester",
    "AppSecAuditReport",
    "TaintFlow",
    "DatabaseArchitect",
    "DatabaseArchitectureReport",
    "QueryAntipattern",
    "CodebaseModernizer",
    "ModernizationReport",
    "ReleaseCaptain",
    "ReleaseReport",
    "APISymbolDelta",
]
