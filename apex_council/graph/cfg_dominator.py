"""Apex-Sovereign: Control Flow Graph (CFG) & Lengauer-Tarjan Dominator Tree Engine.
100% Pure Python Standard Library | Zero Dependencies | Algorithmic Rigor.

Mathematical Foundations:
1. Control Flow Graph: G = (V, E, entry, exit) with basic blocks and branching edges.
2. Dominance: Node d dominates n (d dom n) iff every path from entry to n passes through d.
3. Lengauer-Tarjan Algorithm (ACM TOPLAS, 1979):
   Computes immediate dominators idom(w) in O(V^2) / O(E * alpha(V, E)) via depth-first numbering,
   semidominators sdom(w), and union-find with path compression:
     sdom(w) = min_{v in pred(w)} {
       v if dfnum(v) < dfnum(w) else sdom(eval(v))
     }
4. Dominance Frontiers (Cytron et al., 1991):
   DF(x) = { y in V | exists p in pred(y) s.t. x dom p and not (x sdom y) }
5. Natural Loop Detection:
   Identifies back-edges (u -> v) where v dom u; loop body = { v } U { w | w can reach u without passing through v }.
"""

from __future__ import annotations

import ast
import dataclasses
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class BasicBlock:
    block_id: int
    statements: List[ast.stmt] = dataclasses.field(default_factory=list)
    predecessors: Set[int] = dataclasses.field(default_factory=set)
    successors: Set[int] = dataclasses.field(default_factory=set)
    is_entry: bool = False
    is_exit: bool = False

    @property
    def label(self) -> str:
        if self.is_entry:
            return f"B{self.block_id} [ENTRY]"
        if self.is_exit:
            return f"B{self.block_id} [EXIT]"
        first_stmt = self.statements[0] if self.statements else None
        kind = type(first_stmt).__name__ if first_stmt else "Empty"
        ln = getattr(first_stmt, "lineno", "?") if first_stmt else "?"
        return f"B{self.block_id} ({kind}:L{ln})"


@dataclasses.dataclass(frozen=True)
class NaturalLoop:
    header: int
    back_edge_source: int
    body_blocks: FrozenSet[int]
    loop_depth: int


@dataclasses.dataclass(frozen=True)
class CFGAnalysisReport:
    total_blocks: int
    total_edges: int
    immediate_dominators: Dict[int, Optional[int]]
    dominance_frontiers: Dict[int, Set[int]]
    natural_loops: List[NaturalLoop]
    cyclomatic_complexity: int
    reducible: bool


class ControlFlowGraphBuilder:
    """Builds basic-block Control Flow Graphs from Python function or module ASTs."""

    def __init__(self) -> None:
        self.blocks: Dict[int, BasicBlock] = {}
        self._next_id = 0

    def _new_block(self, is_entry: bool = False, is_exit: bool = False) -> BasicBlock:
        b_id = self._next_id
        self._next_id += 1
        block = BasicBlock(block_id=b_id, is_entry=is_entry, is_exit=is_exit)
        self.blocks[b_id] = block
        return block

    def _add_edge(self, from_id: int, to_id: int) -> None:
        self.blocks[from_id].successors.add(to_id)
        self.blocks[to_id].predecessors.add(from_id)

    def build_cfg(self, statements: List[ast.stmt]) -> Tuple[Dict[int, BasicBlock], int, int]:
        """
        Translates a sequential AST statement list into a CFG.
        Returns (blocks_dict, entry_block_id, exit_block_id).
        """
        self.blocks.clear()
        self._next_id = 0

        entry = self._new_block(is_entry=True)
        exit_block = self._new_block(is_exit=True)

        current = self._new_block()
        self._add_edge(entry.block_id, current.block_id)

        current = self._process_statement_list(statements, current, exit_block)
        if current is not None:
            self._add_edge(current.block_id, exit_block.block_id)

        # Eliminate unreachable blocks from entry
        reachable = self._find_reachable(entry.block_id)
        filtered_blocks = {
            b_id: b for b_id, b in self.blocks.items() if b_id in reachable
        }
        for b in filtered_blocks.values():
            b.predecessors.intersection_update(reachable)
            b.successors.intersection_update(reachable)

        return filtered_blocks, entry.block_id, exit_block.block_id

    def _find_reachable(self, entry_id: int) -> Set[int]:
        visited: Set[int] = set()
        queue = deque([entry_id])
        while queue:
            curr = queue.popleft()
            if curr not in visited:
                visited.add(curr)
                for succ in self.blocks[curr].successors:
                    if succ not in visited:
                        queue.append(succ)
        return visited

    def _process_statement_list(
        self,
        stmts: List[ast.stmt],
        current: BasicBlock,
        exit_block: BasicBlock,
    ) -> Optional[BasicBlock]:
        for stmt in stmts:
            if current is None:
                break

            if isinstance(stmt, ast.Return):
                current.statements.append(stmt)
                self._add_edge(current.block_id, exit_block.block_id)
                current = None

            elif isinstance(stmt, ast.If):
                # Branch condition block
                current.statements.append(stmt)
                then_block = self._new_block()
                else_block = self._new_block()
                self._add_edge(current.block_id, then_block.block_id)
                self._add_edge(current.block_id, else_block.block_id)

                after_block = self._new_block()

                then_end = self._process_statement_list(stmt.body, then_block, exit_block)
                if then_end is not None:
                    self._add_edge(then_end.block_id, after_block.block_id)

                else_end = self._process_statement_list(stmt.orelse, else_block, exit_block)
                if else_end is not None:
                    self._add_edge(else_end.block_id, after_block.block_id)

                # If both branches terminate, after_block is unreachable
                if then_end is None and else_end is None:
                    current = None
                else:
                    current = after_block

            elif isinstance(stmt, (ast.While, ast.For)):
                # Loop header block
                header_block = self._new_block()
                header_block.statements.append(stmt)
                self._add_edge(current.block_id, header_block.block_id)

                body_block = self._new_block()
                after_block = self._new_block()

                self._add_edge(header_block.block_id, body_block.block_id)
                self._add_edge(header_block.block_id, after_block.block_id)

                body_end = self._process_statement_list(stmt.body, body_block, exit_block)
                if body_end is not None:
                    # Loop back-edge
                    self._add_edge(body_end.block_id, header_block.block_id)

                current = after_block

            else:
                current.statements.append(stmt)

        return current


class LengauerTarjanDominatorEngine:
    """
    Computes immediate dominators, dominance frontiers, and natural loops
    using the Lengauer-Tarjan algorithm.
    """

    def __init__(self, blocks: Dict[int, BasicBlock], entry_id: int) -> None:
        self.blocks = blocks
        self.entry_id = entry_id

    def analyze(self) -> CFGAnalysisReport:
        nodes = list(self.blocks.keys())
        if self.entry_id not in self.blocks:
            return CFGAnalysisReport(
                total_blocks=len(nodes),
                total_edges=0,
                immediate_dominators={},
                dominance_frontiers={},
                natural_loops=[],
                cyclomatic_complexity=1,
                reducible=True,
            )

        # 1. Depth-First Search Numbering
        dfnum: Dict[int, int] = {}
        vertex: List[int] = []
        parent: Dict[int, int] = {}
        semi: Dict[int, int] = {}
        idom: Dict[int, Optional[int]] = {}
        ancestor: Dict[int, Optional[int]] = {}
        best: Dict[int, int] = {}
        bucket: Dict[int, Set[int]] = defaultdict(set)

        n = 0

        def dfs(v: int) -> None:
            nonlocal n
            n += 1
            dfnum[v] = n
            semi[v] = n
            vertex.append(v)
            best[v] = v
            ancestor[v] = None

            for w in self.blocks[v].successors:
                if w not in dfnum:
                    parent[w] = v
                    dfs(w)

        dfs(self.entry_id)

        # Union-Find with Path Compression
        def link(v: int, w: int) -> None:
            ancestor[w] = v

        def eval_node(v: int) -> int:
            if ancestor[v] is None:
                return v
            compress(v)
            return best[v]

        def compress(v: int) -> None:
            anc = ancestor[v]
            if anc is not None and ancestor[anc] is not None:
                compress(anc)
                if semi[best[anc]] < semi[best[v]]:
                    best[v] = best[anc]
                ancestor[v] = ancestor[anc]

        # 2. Compute Semidominators and Immediate Dominators bottom-up
        for i in range(len(vertex) - 1, 0, -1):
            w = vertex[i]

            # Step 2: Compute semidominator of w
            for v in self.blocks[w].predecessors:
                if v in dfnum:
                    u = eval_node(v)
                    if semi[u] < semi[w]:
                        semi[w] = semi[u]

            bucket[vertex[semi[w] - 1]].add(w)
            p = parent[w]
            link(p, w)

            # Step 3: Compute idom for nodes in bucket of parent
            for v in list(bucket[p]):
                u = eval_node(v)
                idom[v] = u if semi[u] < semi[v] else p
            bucket[p].clear()

        # Step 4: Finalize idom
        for i in range(1, len(vertex)):
            w = vertex[i]
            if idom.get(w) != vertex[semi[w] - 1]:
                idom[w] = idom.get(idom[w])

        idom[self.entry_id] = None

        # Build Dominance Tree Children Map
        dom_children: Dict[int, Set[int]] = defaultdict(set)
        for node, d in idom.items():
            if d is not None:
                dom_children[d].add(node)

        def dominates(a: int, b: int) -> bool:
            curr: Optional[int] = b
            while curr is not None:
                if curr == a:
                    return True
                curr = idom.get(curr)
            return False

        # 3. Dominance Frontiers Calculation
        df: Dict[int, Set[int]] = {node: set() for node in nodes}
        for y in nodes:
            preds = self.blocks[y].predecessors
            if len(preds) >= 2:
                for p in preds:
                    runner: Optional[int] = p
                    while runner is not None and runner != idom.get(y):
                        df[runner].add(y)
                        runner = idom.get(runner)

        # 4. Natural Loop Detection (Back-edges where target dominates source)
        natural_loops: List[NaturalLoop] = []
        for src in nodes:
            for tgt in self.blocks[src].successors:
                if dominates(tgt, src):
                    # Natural loop detected with header tgt and back-edge src -> tgt
                    loop_body: Set[int] = {tgt, src}
                    stack = [src]
                    while stack:
                        curr = stack.pop()
                        for p in self.blocks[curr].predecessors:
                            if p not in loop_body and dominates(tgt, p):
                                loop_body.add(p)
                                stack.append(p)

                    natural_loops.append(
                        NaturalLoop(
                            header=tgt,
                            back_edge_source=src,
                            body_blocks=frozenset(loop_body),
                            loop_depth=1,
                        )
                    )

        # 5. Cyclomatic Complexity M = E - N + 2P
        total_edges = sum(len(b.successors) for b in self.blocks.values())
        num_blocks = len(self.blocks)
        mccabe = max(1, total_edges - num_blocks + 2)

        return CFGAnalysisReport(
            total_blocks=num_blocks,
            total_edges=total_edges,
            immediate_dominators=idom,
            dominance_frontiers=df,
            natural_loops=natural_loops,
            cyclomatic_complexity=mccabe,
            reducible=True,
        )


class CFGDominatorEngine:
    """Facade for building and analyzing AST Control Flow Graphs with Dominator Trees."""

    @classmethod
    def analyze_source(cls, source_code: str) -> CFGAnalysisReport:
        tree = ast.parse(source_code)
        stmts = tree.body
        if len(stmts) == 1 and isinstance(stmts[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
            stmts = stmts[0].body
        builder = ControlFlowGraphBuilder()
        blocks, entry, _ = builder.build_cfg(stmts)
        analyzer = LengauerTarjanDominatorEngine(blocks, entry)
        return analyzer.analyze()
