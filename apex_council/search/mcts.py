"""Monte Carlo Tree Search (MCTS) Test-Time Compute Engine with PUCT and Transposition Table.
Features: PUCT selection, Progressive Widening, Transposition Table, Trace Reward Shaping, and MDL Tie-Breaker.
Pure Python standard library implementation with zero external dependencies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from apex_council.search.transposition import ASTTranspositionTable
from apex_council.security.ast_shield import ASTShield
from apex_council.security.sandbox import HermeticExecutionSandbox


@dataclass
class MCTSNode:
    state: str  # Code content
    parent: Optional[MCTSNode] = None
    action_description: str = "root"
    children: List[MCTSNode] = field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0
    eval_score: float = 0.0
    eval_details: Dict[str, Any] = field(default_factory=dict)
    prior: float = 1.0
    is_terminal: bool = False

    @property
    def average_value(self) -> float:
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def puct(self, c_puct: float = 1.414) -> float:
        """PUCT Selection metric: Q(s,a) + c_puct * P(s,a) * sqrt(N(s)) / (1 + N(s,a))."""
        if not self.parent or self.parent.visits == 0:
            return self.average_value
        exploration = c_puct * self.prior * (math.sqrt(self.parent.visits) / (1 + self.visits))
        return self.average_value + exploration

    def ucb1(self, exploration_constant: float = 1.414) -> float:
        """Backward-compatible UCB1 alias using PUCT."""
        return self.puct(c_puct=exploration_constant)


@dataclass
class MCTSResult:
    best_code: str
    best_score: float
    total_nodes_explored: int
    pruned_branches: int
    transposition_hits: int
    winning_trajectory: List[str]
    is_verified_passing: bool


class MCTSEngine:
    """Orchestrates test-time compute tree search to discover provably passing patches."""

    def __init__(
        self,
        task_prompt: str,
        test_code: str,
        generator_fn: Callable[[str, str], List[str]],
        exploration_constant: float = 1.414,
        max_depth: int = 3,
        iterations: int = 6,
        progressive_widening_c: float = 2.0,
        progressive_widening_alpha: float = 0.5,
    ) -> None:
        self.task_prompt = task_prompt
        self.test_code = test_code
        self.generator_fn = generator_fn
        self.exploration_constant = exploration_constant
        self.max_depth = max_depth
        self.default_iterations = iterations
        self.pw_c = progressive_widening_c
        self.pw_alpha = progressive_widening_alpha
        self.transposition_table = ASTTranspositionTable()
        self.pruned_count = 0

    def evaluate_candidate(self, code: str) -> Tuple[float, Dict[str, Any]]:
        """Evaluates code safety and test correctness with Transposition Table caching."""
        # 1. Transposition Table Check
        cached = self.transposition_table.lookup(code)
        if cached is not None:
            return cached

        # 2. AST Safety Pre-Check
        try:
            is_safe = ASTShield.inspect_ast_safety(code)
            if not is_safe:
                res = -1.0, {"error": "SyntaxError in candidate code"}
                self.transposition_table.store(code, res[0], res[1])
                return res
        except Exception as ex:
            res = -2.0, {"error": f"AST Bomb or Malicious Pattern Detected: {str(ex)}"}
            self.transposition_table.store(code, res[0], res[1])
            return res

        # 3. Hermetic Sandbox Test Execution
        combined_script = f"{code}\n\n# --- TEST HARNESS ---\n{self.test_code}"
        passed, duration_ms, output = HermeticExecutionSandbox.execute_isolated(combined_script, timeout_sec=4.0)

        if "Sandbox Timeout" in output:
            res = -1.0, {"error": "Execution timed out", "details": output}
        elif passed:
            res = 1.0, {"stdout": output, "status": "ALL_TESTS_PASS", "duration_ms": duration_ms}
        else:
            if "SyntaxError" in output:
                res = -1.0, {"error": "SyntaxError", "stderr": output}
            else:
                res = -0.5, {"error": "AssertionError", "stderr": output}

        self.transposition_table.store(code, res[0], res[1])
        return res

    def search(self, initial_code: str, iterations: Optional[int] = None) -> MCTSResult:
        """Executes MCTS exploration, rollout, and backpropagation with PUCT and Progressive Widening."""
        num_iters = iterations if iterations is not None else self.default_iterations
        root = MCTSNode(state=initial_code, action_description="Initial Code")
        score, details = self.evaluate_candidate(initial_code)
        root.eval_score = score
        root.eval_details = details
        root.visits = 1
        root.total_value = score

        if score >= 1.0:
            return MCTSResult(
                best_code=initial_code,
                best_score=score,
                total_nodes_explored=1,
                pruned_branches=0,
                transposition_hits=self.transposition_table.hits,
                winning_trajectory=["Initial Code (Pass)"],
                is_verified_passing=True,
            )

        all_nodes = [root]

        for iter_num in range(num_iters):
            # 1. Selection (PUCT)
            curr = root
            depth = 0
            while curr.children and depth < self.max_depth:
                active_children = [c for c in curr.children if c.eval_score > -1.8]
                if not active_children:
                    break
                # Progressive Widening check: do we expand or descend?
                max_allowed = max(2, int(self.pw_c * (curr.visits ** self.pw_alpha)))
                if len(curr.children) < max_allowed and not curr.is_terminal:
                    break  # Expand more siblings at curr
                curr = max(active_children, key=lambda c: c.puct(self.exploration_constant))
                depth += 1

            # 2. Expansion
            if not curr.is_terminal and depth < self.max_depth:
                action_prompt = (
                    f"Fix error: {curr.eval_details.get('error', 'tests failed')}. "
                    f"Stderr: {curr.eval_details.get('stderr', '')[:120]}"
                )
                candidates = self.generator_fn(curr.state, action_prompt)

                for idx, cand_code in enumerate(candidates, start=1):
                    child = MCTSNode(
                        state=cand_code,
                        parent=curr,
                        action_description=f"Branch #{iter_num+1}.{idx}: {action_prompt[:40]}",
                    )
                    # 3. Simulation / Rollout
                    c_score, c_details = self.evaluate_candidate(cand_code)
                    child.eval_score = c_score
                    child.eval_details = c_details
                    child.visits = 1
                    child.total_value = c_score

                    if c_score <= -1.8:
                        self.pruned_count += 1
                    if c_score >= 1.0:
                        child.is_terminal = True

                    curr.children.append(child)
                    all_nodes.append(child)

                    # 4. Backpropagation
                    back_node: Optional[MCTSNode] = curr
                    while back_node is not None:
                        back_node.visits += 1
                        back_node.total_value += c_score
                        back_node = back_node.parent

            # If passing solution discovered, terminate tree search
            if any(n.eval_score >= 1.0 for n in all_nodes):
                break

        # 5. MDL (Minimum Description Length) Tie-Breaker
        passing_nodes = [n for n in all_nodes if n.eval_score >= 1.0]
        if passing_nodes:
            # Pick node with lowest complexity (shortest clean code)
            best_node = min(passing_nodes, key=lambda n: len(n.state))
        else:
            valid_nodes = [n for n in all_nodes if n.eval_score > -1.8]
            best_node = max(valid_nodes, key=lambda n: (n.eval_score, n.visits)) if valid_nodes else root

        # Reconstruct trajectory
        trajectory: List[str] = []
        node_ptr: Optional[MCTSNode] = best_node
        while node_ptr is not None:
            trajectory.append(f"{node_ptr.action_description} (Score: {node_ptr.eval_score:.2f})")
            node_ptr = node_ptr.parent
        trajectory.reverse()

        return MCTSResult(
            best_code=best_node.state,
            best_score=best_node.eval_score,
            total_nodes_explored=len(all_nodes),
            pruned_branches=self.pruned_count,
            transposition_hits=self.transposition_table.hits,
            winning_trajectory=trajectory,
            is_verified_passing=(best_node.eval_score >= 1.0),
        )
