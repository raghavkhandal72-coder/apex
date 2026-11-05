#!/usr/bin/env python3
"""
Apex-Sovereign: Semantic Code Ontology & Architectural Graph Reasoning
Inspired by NVIDIA/auto-ontology
100% Pure Python Standard Library | Zero Dependencies

Constructs a formal semantic knowledge graph over codebases to enable deterministic
architectural reasoning, layer boundary enforcement, and explainable AI impact analysis.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import pathlib
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class OntologyEntity:
    id: str  # qualified name e.g. "auth.models.User"
    name: str
    kind: str  # "class", "function", "method", "model", "endpoint"
    layer: str  # "presentation", "application", "domain", "data_access", "infrastructure"
    file_path: str
    lineno: int
    docstring: Optional[str] = None
    is_state_mutator: bool = False


@dataclasses.dataclass(frozen=True)
class OntologyRelation:
    source_id: str
    target_id: str
    predicate: str  # "CALLS", "INHERITS", "MUTATES", "DEPENDS_ON", "WRITES_TO"
    lineno: int = 0


@dataclasses.dataclass(frozen=True)
class OntologyViolation:
    rule_id: str
    severity: str  # "CRITICAL", "WARNING", "INFO"
    source_id: str
    target_id: str
    message: str
    recommendation: str


@dataclasses.dataclass(frozen=True)
class OntologyRule:
    rule_id: str
    name: str
    description: str
    check_fn: Callable[[OntologyEntity, OntologyEntity, OntologyRelation], Optional[OntologyViolation]]


class CodeOntologyEngine:
    """
    Builds and analyzes a semantic ontology graph of the codebase.
    Enforces architectural boundary invariants and calculates transitive dependency cones.
    """

    # Domain Layer Heuristics
    LAYER_HEURISTICS = {
        "presentation": re.compile(r"(cli|ui|view|controller|web|route|endpoint|handler)", re.I),
        "data_access": re.compile(r"(db|database|sql|repo|repository|store|table|model|dao)", re.I),
        "infrastructure": re.compile(r"(adapter|client|http|socket|transport|cloud|filesystem)", re.I),
        "application": re.compile(r"(service|workflow|pipeline|orchestrator|manager|engine)", re.I),
        "domain": re.compile(r"(core|entity|domain|logic|algorithm|rules|model)", re.I),
    }

    def __init__(self) -> None:
        self.entities: Dict[str, OntologyEntity] = {}
        self.relations: List[OntologyRelation] = []
        self._adj_out: Dict[str, List[OntologyRelation]] = {}
        self._adj_in: Dict[str, List[OntologyRelation]] = {}
        self.rules: List[OntologyRule] = []
        self._init_standard_rules()

    def _init_standard_rules(self) -> None:
        # Rule 1: Clean Architecture Layer Barrier (Presentation must not bypass to Data Access)
        def check_clean_arch(src: OntologyEntity, dst: OntologyEntity, rel: OntologyRelation) -> Optional[OntologyViolation]:
            if src.layer == "presentation" and dst.layer == "data_access" and rel.predicate in {"CALLS", "MUTATES"}:
                return OntologyViolation(
                    rule_id="ARCH-001",
                    severity="CRITICAL",
                    source_id=src.id,
                    target_id=dst.id,
                    message=f"Layer Bypass: Presentation entity '{src.id}' directly accesses Data Access entity '{dst.id}'",
                    recommendation="Route through an Application Service or Domain Gateway to preserve inversion of control.",
                )
            return None

        # Rule 2: Unsafe State Mutation (Mutating function directly calling external infrastructure)
        def check_mutation_safety(src: OntologyEntity, dst: OntologyEntity, rel: OntologyRelation) -> Optional[OntologyViolation]:
            if src.is_state_mutator and dst.layer == "infrastructure" and rel.predicate == "CALLS":
                if not any(w in src.name.lower() for w in ["commit", "flush", "save", "sync"]):
                    return OntologyViolation(
                        rule_id="ARCH-002",
                        severity="WARNING",
                        source_id=src.id,
                        target_id=dst.id,
                        message=f"Side-Effect Hazard: Mutator '{src.id}' executes unbuffered Infrastructure call '{dst.id}'",
                        recommendation="Encapsulate infrastructure calls behind atomic transaction or retry handler.",
                    )
            return None

        self.rules.append(OntologyRule("ARCH-001", "Clean Architecture Barrier", "Enforces layered isolation", check_clean_arch))
        self.rules.append(OntologyRule("ARCH-002", "Side-Effect Isolation", "Restricts unbuffered mutations", check_mutation_safety))

    def infer_layer(self, file_path: str, symbol_name: str) -> str:
        """Heuristically infers the architectural layer of an entity."""
        path_lower = file_path.replace("\\", "/").lower()
        sym_lower = symbol_name.lower()

        if self.LAYER_HEURISTICS["presentation"].search(path_lower) or self.LAYER_HEURISTICS["presentation"].search(sym_lower):
            return "presentation"
        if self.LAYER_HEURISTICS["data_access"].search(path_lower) or self.LAYER_HEURISTICS["data_access"].search(sym_lower):
            return "data_access"
        if self.LAYER_HEURISTICS["infrastructure"].search(path_lower):
            return "infrastructure"
        if self.LAYER_HEURISTICS["application"].search(path_lower):
            return "application"
        return "domain"

    def index_source(self, file_path: str, source_code: str) -> None:
        """Extracts ontological entities and relationships from Python code."""
        norm_path = file_path.replace("\\", "/")
        try:
            tree = ast.parse(source_code, filename=norm_path)
        except SyntaxError:
            return

        module_name = os.path.splitext(os.path.basename(norm_path))[0]

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                layer = self.infer_layer(norm_path, node.name)
                class_id = f"{module_name}.{node.name}"
                entity = OntologyEntity(
                    id=class_id,
                    name=node.name,
                    kind="class",
                    layer=layer,
                    file_path=norm_path,
                    lineno=node.lineno,
                    docstring=ast.get_docstring(node),
                )
                self.add_entity(entity)

                # Inheritance relations
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        self.add_relation(OntologyRelation(class_id, f"{module_name}.{base.id}", "INHERITS", node.lineno))

                # Process methods
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_id = f"{class_id}.{item.name}"
                        is_mutator = any(w in item.name.lower() for w in ["set", "update", "delete", "write", "save", "add", "remove"])
                        m_entity = OntologyEntity(
                            id=method_id,
                            name=item.name,
                            kind="method",
                            layer=layer,
                            file_path=norm_path,
                            lineno=item.lineno,
                            docstring=ast.get_docstring(item),
                            is_state_mutator=is_mutator,
                        )
                        self.add_entity(m_entity)
                        self.add_relation(OntologyRelation(class_id, method_id, "CONTAINS", item.lineno))
                        self._extract_calls(item, method_id, module_name)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                layer = self.infer_layer(norm_path, node.name)
                func_id = f"{module_name}.{node.name}"
                is_mutator = any(w in node.name.lower() for w in ["set", "update", "delete", "write", "save", "add", "remove"])
                f_entity = OntologyEntity(
                    id=func_id,
                    name=node.name,
                    kind="function",
                    layer=layer,
                    file_path=norm_path,
                    lineno=node.lineno,
                    docstring=ast.get_docstring(node),
                    is_state_mutator=is_mutator,
                )
                self.add_entity(f_entity)
                self._extract_calls(node, func_id, module_name)

    def _extract_calls(self, func_node: ast.AST, caller_id: str, module_name: str) -> None:
        for sub in ast.walk(func_node):
            if isinstance(sub, ast.Call):
                target_name = None
                owner_name = None
                if isinstance(sub.func, ast.Name):
                    target_name = sub.func.id
                elif isinstance(sub.func, ast.Attribute):
                    target_name = sub.func.attr
                    if isinstance(sub.func.value, ast.Name):
                        owner_name = sub.func.value.id

                if owner_name and target_name:
                    self.add_relation(OntologyRelation(caller_id, f"{owner_name}.{target_name}", "CALLS", sub.lineno))
                    self.add_relation(OntologyRelation(caller_id, owner_name, "CALLS", sub.lineno))
                elif target_name:
                    self.add_relation(OntologyRelation(caller_id, f"{module_name}.{target_name}", "CALLS", sub.lineno))
                    self.add_relation(OntologyRelation(caller_id, target_name, "CALLS", sub.lineno))

    def resolve_entity(self, target_id: str) -> Optional[OntologyEntity]:
        """Resolves an entity by exact ID or matching qualified suffix."""
        if target_id in self.entities:
            return self.entities[target_id]
        target_suffix = f".{target_id}"
        for k, v in self.entities.items():
            if k == target_id or k.endswith(target_suffix):
                return v
        return None

    def add_entity(self, entity: OntologyEntity) -> None:
        self.entities[entity.id] = entity
        self._adj_out.setdefault(entity.id, [])
        self._adj_in.setdefault(entity.id, [])

    def add_relation(self, rel: OntologyRelation) -> None:
        self.relations.append(rel)
        self._adj_out.setdefault(rel.source_id, []).append(rel)
        self._adj_in.setdefault(rel.target_id, []).append(rel)

    def check_invariants(self) -> List[OntologyViolation]:
        """Validates all architectural rules across the semantic ontology graph."""
        violations: List[OntologyViolation] = []
        for rel in self.relations:
            src = self.resolve_entity(rel.source_id)
            dst = self.resolve_entity(rel.target_id)
            if not src or not dst:
                continue
            for rule in self.rules:
                v = rule.check_fn(src, dst, rel)
                if v and v not in violations:
                    violations.append(v)
        return violations

    def explain_impact(self, entity_id: str) -> Dict[str, Any]:
        """
        Calculates transitive downstream impact of modifying an entity.
        Returns all callers, dependents, and impacted architectural layers.
        """
        visited: Set[str] = set()
        queue: List[str] = [entity_id]
        impacted_layers: Set[str] = set()

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            ent = self.entities.get(curr)
            if ent:
                impacted_layers.add(ent.layer)

            # Inbound edges: who calls or depends on this entity?
            for in_rel in self._adj_in.get(curr, []):
                if in_rel.source_id not in visited:
                    queue.append(in_rel.source_id)

        downstream_callers = sorted(list(visited - {entity_id}))
        return {
            "target_entity": entity_id,
            "transitive_impact_count": len(downstream_callers),
            "impacted_entities": downstream_callers,
            "impacted_layers": sorted(list(impacted_layers)),
            "is_high_blast_radius": len(downstream_callers) > 5,
        }
