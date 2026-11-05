#!/usr/bin/env python3
"""
Apex-Sovereign: OmO Task DAG Compilation & Wave Graph Engine
Inspired by code-yeongyu/oh-my-openagent (packages/senpi-task/src/dag/graph.ts)
100% Pure Python Standard Library | Zero Dependencies
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass(frozen=True)
class DagRoute:
    kind: str  # "category" | "agent"
    value: str  # e.g., "quick", "planning", or "claude-code"
    model: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DagNodeInput:
    id: str
    prompt: str
    label: Optional[str] = None
    category: Optional[str] = None
    subagent_type: Optional[str] = "quick"
    model: Optional[str] = "gpt-5-astra-high"
    depends_on: List[str] = dataclasses.field(default_factory=list)
    task_summary: Optional[str] = None
    description: Optional[str] = None


@dataclasses.dataclass
class DagNode:
    id: str
    prompt: str
    route: DagRoute
    depends_on: List[str]
    state: str = "pending"  # pending, running, completed, failed
    label: Optional[str] = None
    attempt: int = 0
    duration_s: float = 0.0
    turns: int = 1
    tools_count: int = 1
    result_summary: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DagEdge:
    from_node: str
    to_node: str


@dataclasses.dataclass(frozen=True)
class DagWave:
    index: int
    node_ids: List[str]


@dataclasses.dataclass(frozen=True)
class DagCompileResult:
    ok: bool
    nodes: List[DagNode]
    edges: List[DagEdge]
    waves: List[DagWave]
    critical_path: List[str]
    bottlenecks: List[str]
    errors: List[str]


class DagCompiler:
    """
    Mathematical DAG compiler implementing topological sorting,
    cycle discovery, wave partitioning, and critical path analysis.
    """

    MAX_NODES_PER_RUN = 128
    MAX_PROMPT_BYTES = 100_000

    @classmethod
    def compile(cls, nodes_input: List[DagNodeInput]) -> DagCompileResult:
        errors: List[str] = []

        if not nodes_input:
            return DagCompileResult(
                ok=False, nodes=[], edges=[], waves=[], critical_path=[], bottlenecks=[], errors=["DAG has no nodes"]
            )

        if len(nodes_input) > cls.MAX_NODES_PER_RUN:
            errors.append(f"Node count {len(nodes_input)} exceeds max {cls.MAX_NODES_PER_RUN}")

        seen_ids: Set[str] = set()
        duplicates: List[str] = []
        for inp in nodes_input:
            if not inp.id or any(c in inp.id for c in "/\\: \x00"):
                errors.append(f"Invalid node id segment: '{inp.id}'")
            if inp.id in seen_ids and inp.id not in duplicates:
                duplicates.append(inp.id)
            seen_ids.add(inp.id)

        for dup in duplicates:
            errors.append(f"Duplicate node id detected: '{dup}'")

        # Check dependencies
        for inp in nodes_input:
            for dep in inp.depends_on:
                if dep == inp.id:
                    errors.append(f"Self-dependency detected on node '{inp.id}'")
                elif dep not in seen_ids:
                    errors.append(f"Node '{inp.id}' depends on unknown node '{dep}'")

        # Dependency map
        dep_map: Dict[str, List[str]] = {
            inp.id: [d for d in inp.depends_on if d in seen_ids and d != inp.id] for inp in nodes_input
        }

        # Cycle detection
        cycles = cls._find_cycles(list(seen_ids), dep_map)
        for cyc in cycles:
            errors.append(f"Dependency cycle detected: {' -> '.join(cyc)}")

        if errors:
            return DagCompileResult(
                ok=False, nodes=[], edges=[], waves=[], critical_path=[], bottlenecks=[], errors=errors
            )

        # Build DagNodes
        nodes: List[DagNode] = []
        for inp in nodes_input:
            if inp.category:
                route = DagRoute(kind="category", value=inp.category, model=inp.model)
            else:
                route = DagRoute(kind="agent", value=inp.subagent_type or "quick", model=inp.model)
            nodes.append(
                DagNode(
                    id=inp.id,
                    prompt=inp.prompt,
                    route=route,
                    depends_on=dep_map[inp.id],
                    label=inp.label or inp.id,
                )
            )

        # Build Edges
        edges: List[DagEdge] = []
        for n in nodes:
            for d in n.depends_on:
                edges.append(DagEdge(from_node=d, to_node=n.id))

        # Compute depths and waves
        depth_map: Dict[str, int] = {}

        def get_depth(node_id: str) -> int:
            if node_id in depth_map:
                return depth_map[node_id]
            deps = dep_map.get(node_id, [])
            if not deps:
                d = 0
            else:
                d = 1 + max(get_depth(x) for x in deps)
            depth_map[node_id] = d
            return d

        for inp in nodes_input:
            get_depth(inp.id)

        max_wave = max(depth_map.values()) if depth_map else 0
        waves: List[DagWave] = []
        for w_idx in range(max_wave + 1):
            w_nodes = [nid for nid, d in depth_map.items() if d == w_idx]
            waves.append(DagWave(index=w_idx, node_ids=sorted(w_nodes)))

        # Compute critical path (longest path through DAG)
        dependents: Dict[str, List[str]] = {nid: [] for nid in seen_ids}
        for edge in edges:
            dependents[edge.from_node].append(edge.to_node)

        longest_memo: Dict[str, List[str]] = {}

        def resolve_longest(nid: str) -> List[str]:
            if nid in longest_memo:
                return longest_memo[nid]
            succs = sorted(dependents.get(nid, []))
            best_sub: List[str] = []
            for s in succs:
                cand = resolve_longest(s)
                if len(cand) > len(best_sub):
                    best_sub = cand
            res = [nid] + best_sub
            longest_memo[nid] = res
            return res

        critical_path: List[str] = []
        for nid in sorted(seen_ids):
            cand = resolve_longest(nid)
            if len(cand) > len(critical_path):
                critical_path = cand

        # Identify bottlenecks (nodes with high fan-in or high fan-out)
        bottlenecks: List[str] = []
        for nid in seen_ids:
            fan_in = len(dep_map.get(nid, []))
            fan_out = len(dependents.get(nid, []))
            if fan_in >= 2 and fan_out >= 1:
                bottlenecks.append(nid)

        return DagCompileResult(
            ok=True,
            nodes=nodes,
            edges=edges,
            waves=waves,
            critical_path=critical_path,
            bottlenecks=sorted(bottlenecks),
            errors=[],
        )

    @classmethod
    def _find_cycles(cls, all_ids: List[str], dep_map: Dict[str, List[str]]) -> List[List[str]]:
        """Finds any dependency cycles using DFS cycle discovery."""
        visited: Dict[str, int] = {}  # 0: unvisited, 1: visiting, 2: visited
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(node: str):
            visited[node] = 1
            path.append(node)
            for nxt in dep_map.get(node, []):
                if visited.get(nxt, 0) == 1:
                    cycle_start = path.index(nxt)
                    cyc = path[cycle_start:] + [nxt]
                    cycles.append(cyc)
                elif visited.get(nxt, 0) == 0:
                    dfs(nxt)
            path.pop()
            visited[node] = 2

        for nid in sorted(all_ids):
            if visited.get(nid, 0) == 0:
                dfs(nid)

        return cycles
