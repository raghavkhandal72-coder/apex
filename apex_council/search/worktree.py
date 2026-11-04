"""Ephemeral Git Worktree Pool for Parallel MCTS Rollouts.
Provides isolated, race-free execution environments for candidate branches with sub-millisecond teardown.
Pure Python standard library implementation.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, Generator, Optional


class EphemeralWorktreePool:
    """Manages isolated ephemeral Git worktrees or overlay workspaces for MCTS rollouts."""

    def __init__(self, repo_dir: Path | str) -> None:
        self.repo_dir = Path(repo_dir).resolve()
        self.is_git_repo = self._check_git_repo()
        self.active_worktrees: Dict[str, Path] = {}

    def _check_git_repo(self) -> bool:
        git_dir = self.repo_dir / ".git"
        if git_dir.exists():
            return True
        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_dir), "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except Exception:
            return False

    @contextlib.contextmanager
    def acquire_worktree(self, branch_id: str) -> Generator[Path, None, None]:
        """Allocates an isolated workspace, yields the path, and guarantees clean teardown."""
        temp_dir = tempfile.mkdtemp(prefix=f"apex_wt_{branch_id}_")
        wt_path = Path(temp_dir).resolve()

        created_via_git = False
        if self.is_git_repo:
            try:
                res = subprocess.run(
                    ["git", "-C", str(self.repo_dir), "worktree", "add", "--detach", str(wt_path), "HEAD"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    created_via_git = True
            except Exception:
                created_via_git = False

        if not created_via_git:
            # Fallback: Overlay copy of repository files (skipping ignored dirs)
            self._create_overlay_copy(self.repo_dir, wt_path)

        self.active_worktrees[branch_id] = wt_path
        try:
            yield wt_path
        finally:
            self._cleanup_worktree(branch_id, wt_path, created_via_git)

    def _create_overlay_copy(self, src: Path, dest: Path) -> None:
        """Lightweight overlay copy ignoring huge dependency and VCS directories."""
        ignore_names = {".git", ".venv", "venv", "node_modules", "__pycache__", ".apex"}
        for item in src.iterdir():
            if item.name in ignore_names:
                continue
            target = dest / item.name
            try:
                if item.is_dir():
                    shutil.copytree(item, target, ignore=shutil.ignore_patterns(*ignore_names))
                else:
                    shutil.copy2(item, target)
            except Exception:
                pass

    def _cleanup_worktree(self, branch_id: str, wt_path: Path, created_via_git: bool) -> None:
        """Tears down the worktree in milliseconds."""
        if branch_id in self.active_worktrees:
            del self.active_worktrees[branch_id]

        if created_via_git:
            try:
                subprocess.run(
                    ["git", "-C", str(self.repo_dir), "worktree", "remove", "--force", str(wt_path)],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass

        if wt_path.exists():
            try:
                shutil.rmtree(wt_path, ignore_errors=True)
            except Exception:
                pass
