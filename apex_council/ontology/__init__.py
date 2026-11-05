"""
Apex-Sovereign: Semantic Code Ontology & Graph Reasoning Engine
Inspired by NVIDIA/auto-ontology
100% Pure Python Standard Library | Zero Dependencies
"""

from .code_ontology import (
    CodeOntologyEngine,
    OntologyEntity,
    OntologyRelation,
    OntologyRule,
    OntologyViolation,
)

__all__ = [
    "CodeOntologyEngine",
    "OntologyEntity",
    "OntologyRelation",
    "OntologyRule",
    "OntologyViolation",
]
