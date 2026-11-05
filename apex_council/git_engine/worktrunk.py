#!/usr/bin/env python3
"""
Apex-Sovereign: Parallel Agent Git Worktree Manager
Inspired by max-sixty/worktrunk (Rust CLI for Git worktrees)
100% Pure Python Standard Library | Zero Dependencies

Allocates, tracks, and cleans up isolated Git worktrees for parallel agent swarms.
Allows multi-agent rollouts to run tests and mutations simultaneously with zero index contention.
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess
import time
from typing import Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class WorktreeSession:
    agent_id: str
    branch_name: str
    worktree_path: pathlib.Path
    created_at: float


class WorktrunkEngine:
    """
    Manages isolated Git worktrees under `.git/apex_worktrees/` for parallel agent swarms.
    """

    def __init__(self, repo_path: str | pathlib.Path = ".") -> None:
        self.repo_path = pathlib.Path(repo_path).resolve()
        self.worktree_base = self.repo_path / ".git" / "apex_worktrees"
        self._sessions: Dict[str, WorktreeSession] = {}

    def _run_git(self, args: List[str]) -> Tuple[bool, str, str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        return (proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip())

    def allocate_worktree(
        self,
        agent_id: str,
        base_ref: str = "HEAD",
    ) -> WorktreeSession:
        """
        Creates an isolated ephemeral worktree for a specialized agent.
        """
        self.worktree_base.mkdir(parents=True, exist_ok=True)
        safe_agent = agent_id.replace("/", "_").replace(" ", "_").lower()
        branch = f"apex-trunk/{safe_agent}-{int(time.time())}"
        target_dir = self.worktree_base / safe_agent

        # Prune existing if present
        if target_dir.exists():
            self.prune_worktree(agent_id, force=True)

        # git worktree add -b <branch> <path> <base_ref>
        ok, out, err = self._run_git(["worktree", "add", "-b", branch, str(target_dir), base_ref])
        if not ok:
            # Fallback if branch already exists: force reuse or checkout
            ok2, out2, err2 = self._run_git(["worktree", "add", str(target_dir), base_ref])
            if not ok2:
                raise RuntimeError(f"Failed to allocate worktree for '{agent_id}': {err or err2}")

        session = WorktreeSession(
            agent_id=agent_id,
            branch_name=branch,
            worktree_path=target_dir,
            created_at=time.time(),
        )
        self._sessions[agent_id] = session
        return session

    def list_active_worktrees(self) -> List[WorktreeSession]:
        """Returns all currently registered worktree sessions."""
        return list(self._sessions.values())

    def prune_worktree(self, agent_id: str, force: bool = True) -> bool:
        """
        Safely removes a worktree and deletes its temporary branch.
        """
        session = self._sessions.get(agent_id)
        target_dir = session.worktree_path if session else (self.worktree_base / agent_id)

        if target_dir.exists():
            cmd = ["worktree", "remove", str(target_dir)]
            if force:
                cmd.append("--force")
            self._run_git(cmd)

        self._run_git(["worktree", "prune"])

        if session and session.branch_name:
            self._run_git(["branch", "-D", session.branch_name])
            self._sessions.pop(agent_id, None)

        return True

    def cleanup_all(self) -> int:
        """Removes all ephemeral agent worktrees and prunes state."""
        count = len(self._sessions)
        for agent_id in list(self._sessions.keys()):
            self.prune_worktree(agent_id, force=True)

        self._run_git(["worktree", "prune"])
        return count
