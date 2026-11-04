"""Monte Carlo Tree Search (MCTS) Test-Time Compute Engine.
Explores multiple solution paths, performs sandbox rollouts, and prunes broken branches.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    is_terminal: bool = False

    @property
    def average_value(self) -> float:
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def ucb1(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float("inf")
        if not self.parent or self.parent.visits == 0:
            return self.average_value
        return self.average_value + exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )


@dataclass
class MCTSResult:
    best_code: str
    best_score: float
    total_nodes_explored: int
    pruned_branches: int
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
    ) -> None:
        self.task_prompt = task_prompt
        self.test_code = test_code
        self.generator_fn = generator_fn
        self.exploration_constant = exploration_constant
        self.max_depth = max_depth
        self.default_iterations = iterations
        self.pruned_count = 0

    def evaluate_candidate(self, code: str) -> Tuple[float, Dict[str, Any]]:
        """Evaluates code safety via ASTShield and runtime test execution via HermeticSandbox."""
        # 1. AST Safety Pre-Check
        try:
            is_safe = ASTShield.inspect_ast_safety(code)
            if not is_safe:
                return -1.0, {"error": "SyntaxError in candidate code"}
        except Exception as ex:
            return -2.0, {"error": f"AST Bomb or Malicious Pattern Detected: {str(ex)}"}

        # 2. Hermetic Sandbox Test Execution
        combined_script = f"{code}\n\n# --- TEST HARNESS ---\n{self.test_code}"
        passed, duration_ms, output = HermeticExecutionSandbox.execute_isolated(combined_script, timeout_sec=4.0)

        if "Sandbox Timeout" in output:
            return -1.0, {"error": "Execution timed out (possible infinite loop)", "details": output}

        if passed:
            # Reward clean passing solution
            return 1.0, {"stdout": output, "status": "ALL_TESTS_PASS", "duration_ms": duration_ms}
        else:
            # Differentiate syntax error from test assertion failure
            if "SyntaxError" in output:
                return -1.0, {"error": "SyntaxError", "stderr": output}
            else:
                return -0.5, {"error": "AssertionError", "stderr": output}

    def search(self, initial_code: str, iterations: Optional[int] = None) -> MCTSResult:
        """Executes MCTS exploration, rollout, and backpropagation."""
        num_iters = iterations if iterations is not None else self.default_iterations
        root = MCTSNode(state=initial_code, action_description="Initial Code")
        score, details = self.evaluate_candidate(initial_code)
        root.eval_score = score
        root.eval_details = details
        root.visits = 1
        root.total_value = score

        # If initial code already passes cleanly with 1.0, return immediately
        if score == 1.0:
            return MCTSResult(
                best_code=initial_code,
                best_score=1.0,
                total_nodes_explored=1,
                pruned_branches=0,
                winning_trajectory=["Initial Code (Pass)"],
                is_verified_passing=True,
            )

        all_nodes = [root]

        for iter_num in range(num_iters):
            # 1. Selection
            curr = root
            depth = 0
            while curr.children and depth < self.max_depth:
                # Filter out severely broken/pruned children
                active_children = [c for c in curr.children if c.eval_score > -1.8]
                if not active_children:
                    break
                curr = max(active_children, key=lambda c: c.ucb1(self.exploration_constant))
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
                    if c_score == 1.0:
                        child.is_terminal = True

                    curr.children.append(child)
                    all_nodes.append(child)

                    # 4. Backpropagation
                    back_node: Optional[MCTSNode] = curr
                    while back_node is not None:
                        back_node.visits += 1
                        back_node.total_value += c_score
                        back_node = back_node.parent

                    if c_score == 1.0:
                        break  # Found passing solution

        # Select best node (highest score, highest visits)
        valid_nodes = [n for n in all_nodes if n.eval_score > -1.8]
        best_node = max(valid_nodes, key=lambda n: (n.eval_score, n.visits))

        # Reconstruct winning trajectory
        trajectory: List[str] = []
        node_ptr: Optional[MCTSNode] = best_node
        while node_ptr is not None:
            trajectory.append(f"{node_ptr.action_description} (Score: {node_ptr.eval_score:.1f})")
            node_ptr = node_ptr.parent
        trajectory.reverse()

        return MCTSResult(
            best_code=best_node.state,
            best_score=best_node.eval_score,
            total_nodes_explored=len(all_nodes),
            pruned_branches=self.pruned_count,
            winning_trajectory=trajectory,
            is_verified_passing=(best_node.eval_score == 1.0),
        )
