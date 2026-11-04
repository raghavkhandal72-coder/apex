#!/usr/bin/env python3
"""
Apex-Sovereign: Bare-Metal Git Plumbing DAG Engine
100% Pure Python Standard Library | Zero Working-Tree Pollution | Zero Mocks
"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple


class GitPlumbingError(RuntimeError):
    """Raised when a low-level Git plumbing operation fails."""


@dataclasses.dataclass
class GitTreeEntry:
    mode: str
    obj_type: str = "blob"
    sha: str = ""
    path: str = ""
    object_type: Optional[str] = None

    def __post_init__(self) -> None:
        if self.object_type is not None:
            self.obj_type = self.object_type
        else:
            self.object_type = self.obj_type


class GitPlumbingEngine:
    """
    Operates directly on .git/objects using low-level plumbing commands:
    hash-object, read-tree, update-index --cacheinfo, write-tree, commit-tree,
    diff-tree, checkout-index, and update-ref.
    """

    def __init__(self, repo_path: str | pathlib.Path) -> None:
        self.repo_path = pathlib.Path(repo_path).resolve()
        self.repo_dir = self.repo_path
        if not (self.repo_path / ".git").exists():
            raise GitPlumbingError(f"Not a valid Git repository: {self.repo_path}")

    def _run_git(
        self,
        args: List[str],
        stdin_bytes: Optional[bytes] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> bytes:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        if extra_env:
            env.update(extra_env)

        proc = subprocess.run(
            ["git", *args],
            cwd=str(self.repo_path),
            input=stdin_bytes,
            capture_output=True,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            raise GitPlumbingError(f"git {' '.join(args)} failed: {err_msg}")
        return proc.stdout

    @classmethod
    def init_repo(cls, target_dir: str | pathlib.Path, default_branch: str = "main") -> "GitPlumbingEngine":
        """Initializes a fresh Git repository for testing or standalone edge workspaces."""
        path = pathlib.Path(target_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "-b", default_branch],
            cwd=str(path),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Apex-Sovereign Gatekeeper"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "gatekeeper@apex-sovereign.local"],
            cwd=str(path),
            capture_output=True,
            check=True,
        )
        return cls(path)

    def write_blob(self, content: str | bytes) -> str:
        """Writes raw bytes directly into .git/objects as a blob and returns its 40-char SHA."""
        raw = content.encode("utf-8") if isinstance(content, str) else content
        out = self._run_git(["hash-object", "-w", "--stdin"], stdin_bytes=raw)
        return out.decode("ascii").strip()

    def hash_object(self, content: str | bytes, write: bool = True) -> str:
        """Backwards compatible alias for write_blob."""
        if write:
            return self.write_blob(content)
        raw = content.encode("utf-8") if isinstance(content, str) else content
        out = self._run_git(["hash-object", "--stdin"], stdin_bytes=raw)
        return out.decode("ascii").strip()

    def read_blob(self, blob_sha: str) -> bytes:
        """Reads raw bytes of a blob SHA directly from .git/objects."""
        return self._run_git(["cat-file", "blob", blob_sha])

    def cat_file(self, sha: str, object_type: str = "-p") -> str:
        """Reads content of any Git object (blob, tree, commit) by SHA."""
        raw = self._run_git(["cat-file", object_type, sha])
        return raw.decode("utf-8", errors="replace")

    def get_head_commit(self) -> Optional[str]:
        """Returns current HEAD commit SHA, or None if the repository has no commits yet."""
        try:
            out = self._run_git(["rev-parse", "--verify", "HEAD"])
            return out.decode("ascii").strip()
        except GitPlumbingError:
            return None

    def get_commit_tree(self, commit_sha: str) -> str:
        """Resolves the root tree SHA associated with a given commit SHA."""
        out = self._run_git(["rev-parse", f"{commit_sha}^{{tree}}"])
        return out.decode("ascii").strip()

    def list_tree_recursive(self, tree_sha: str) -> List[GitTreeEntry]:
        """Lists all blobs recursively inside a Git tree SHA."""
        out = self._run_git(["ls-tree", "-r", "-z", tree_sha])
        entries: List[GitTreeEntry] = []
        for record in out.split(b"\x00"):
            if not record:
                continue
            meta_bytes, path_bytes = record.split(b"\t", 1)
            mode, obj_type, sha = meta_bytes.decode("ascii").split(" ")
            entries.append(
                GitTreeEntry(
                    mode=mode,
                    obj_type=obj_type,
                    sha=sha,
                    path=path_bytes.decode("utf-8"),
                )
            )
        return entries

    def list_tree(self, tree_sha: str) -> List[GitTreeEntry]:
        """Lists entries in a tree object via git ls-tree."""
        return self.list_tree_recursive(tree_sha)

    def make_tree(self, entries: List[GitTreeEntry]) -> str:
        """Builds a Git tree object from entries using git mktree."""
        lines = [f"{e.mode} {e.obj_type} {e.sha}\t{e.path}" for e in entries]
        payload = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        out = self._run_git(["mktree"], stdin_bytes=payload)
        return out.decode("ascii").strip()

    def create_ephemeral_tree(
        self,
        file_patches: Dict[str, str | bytes],
        base_tree_sha: Optional[str] = None,
        deleted_paths: Optional[List[str]] = None,
    ) -> str:
        """
        Constructs a new Git Tree SHA inside .git/objects from in-memory file patches
        using an isolated temporary GIT_INDEX_FILE.
        Never touches the user's working directory or real .git/index!
        """
        with tempfile.TemporaryDirectory(prefix="apex_git_idx_") as tmp_dir:
            temp_index_path = os.path.join(tmp_dir, "ephemeral.index")
            idx_env = {"GIT_INDEX_FILE": temp_index_path}

            if base_tree_sha:
                self._run_git(["read-tree", base_tree_sha], extra_env=idx_env)

            if deleted_paths:
                for del_path in deleted_paths:
                    norm_del = pathlib.PurePosixPath(pathlib.Path(del_path)).as_posix()
                    self._run_git(
                        ["update-index", "--force-remove", "--", norm_del],
                        extra_env=idx_env,
                    )

            for rel_path, content in file_patches.items():
                norm_path = pathlib.PurePosixPath(pathlib.Path(rel_path)).as_posix()
                blob_sha = self.write_blob(content)
                self._run_git(
                    [
                        "update-index",
                        "--add",
                        "--cacheinfo",
                        f"100644,{blob_sha},{norm_path}",
                    ],
                    extra_env=idx_env,
                )

            tree_out = self._run_git(["write-tree"], extra_env=idx_env)
            return tree_out.decode("ascii").strip()

    def create_snapshot_tree_with_patch(
        self,
        base_tree_sha: Optional[str],
        file_path_rel: str,
        new_file_content: str | bytes,
    ) -> str:
        """Helper to create a new tree applying a single file patch."""
        return self.create_ephemeral_tree(
            file_patches={file_path_rel: new_file_content},
            base_tree_sha=base_tree_sha,
        )

    def diff_trees(self, tree_sha_a: str, tree_sha_b: str) -> str:
        """Generates a unified diff between two in-memory Git Tree SHAs with zero disk checkout."""
        out = self._run_git(["diff-tree", "-p", "-r", tree_sha_a, tree_sha_b])
        return out.decode("utf-8", errors="replace")

    def materialize_tree_to_sandbox(self, tree_sha: str, target_dir: str | pathlib.Path) -> pathlib.Path:
        """
        Materializes any MCTS Git Tree SHA into an isolated sandbox directory in milliseconds
        using an ephemeral index and `git checkout-index`, leaving the main repo untouched.
        """
        dest = pathlib.Path(target_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        prefix = str(dest)
        if not prefix.endswith(os.sep):
            prefix += os.sep

        with tempfile.TemporaryDirectory(prefix="apex_materialize_") as tmp_dir:
            temp_index_path = os.path.join(tmp_dir, "sandbox.index")
            idx_env = {"GIT_INDEX_FILE": temp_index_path}
            self._run_git(["read-tree", tree_sha], extra_env=idx_env)
            self._run_git(
                ["checkout-index", "-a", "-f", f"--prefix={prefix}"],
                extra_env=idx_env,
            )
        return dest

    def commit_tree(
        self,
        tree_sha: str,
        message: str,
        parent_shas: Optional[List[str]] = None,
        parent_sha: Optional[str] = None,
        author_name: str = "Apex-Sovereign Gatekeeper",
        author_email: str = "gatekeeper@apex-sovereign.local",
    ) -> str:
        """
        Creates an immutable Git Commit object inside .git/objects via `git commit-tree`
        without moving HEAD or modifying the working directory.
        """
        parents = list(parent_shas or [])
        if parent_sha and parent_sha not in parents:
            parents.append(parent_sha)

        cmd: List[str] = ["commit-tree", tree_sha]
        for parent in parents:
            cmd.extend(["-p", parent])

        author_env = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
        out = self._run_git(cmd, stdin_bytes=message.encode("utf-8"), extra_env=author_env)
        return out.decode("ascii").strip()

    def promote_commit_to_ref(
        self,
        commit_sha: str,
        ref_name: str = "HEAD",
        sync_working_tree: bool = False,
    ) -> None:
        """
        Atomically advances a Git reference (e.g., HEAD or refs/heads/main) to the verified commit SHA.
        Optionally synchronizes the working directory once verification succeeds.
        """
        self._run_git(["update-ref", ref_name, commit_sha])
        if sync_working_tree:
            self._run_git(["read-tree", "-u", "--reset", commit_sha])
