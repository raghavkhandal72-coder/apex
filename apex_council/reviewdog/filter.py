"""Diff-based diagnostic filtering engine for apex_council.reviewdog.

Supports parsing unified diffs (git diff) and filtering diagnostics by:
- added: only diagnostics whose line falls exactly on added/modified lines (+)
- diff-context: diagnostics on added lines or within hunk context (+-3 lines of added lines)
- file: all diagnostics on any file modified in the diff
- nofilter: unconditionally report all diagnostics

Pure Python 3 standard library (zero external dependencies).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .models import Diagnostic

HUNK_HEADER_PATTERN = re.compile(
    r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@"
)


@dataclass
class DiffFileInfo:
    """Information extracted from a git diff for a single file."""
    old_path: str
    new_path: str
    added_lines: Set[int] = field(default_factory=set)
    context_lines: Set[int] = field(default_factory=set)
    deleted_lines: Set[int] = field(default_factory=set)

    @property
    def is_deleted(self) -> bool:
        return self.new_path == "/dev/null" or not self.new_path

    @property
    def is_new(self) -> bool:
        return self.old_path == "/dev/null" or not self.old_path

    def has_line_in_diff_context(self, line: int, context_window: int = 3) -> bool:
        """Check if line is an added line or within context_window lines of any added line."""
        if line in self.added_lines:
            return True
        if line in self.context_lines:
            return True
        return any(abs(line - added) <= context_window for added in self.added_lines)


def normalize_path(path: str) -> str:
    """Normalize file path to POSIX style without leading relative prefixes."""
    p = str(path).replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("a/"):
        p = p[2:]
    elif p.startswith("b/"):
        p = p[2:]
    return p


def paths_match(diag_path: str, diff_path: str) -> bool:
    """Check if diagnostic file path matches diff file path.

    Supports exact matches, basename matches, and suffix matching.
    """
    if diff_path == "*" or diag_path == "*":
        return True

    p1 = normalize_path(diag_path)
    p2 = normalize_path(diff_path)

    if not p1 or not p2:
        return False

    if p1 == p2:
        return True

    # Suffix matching
    if p1.endswith("/" + p2) or p2.endswith("/" + p1):
        return True

    # Basename matching
    name1 = p1.split("/")[-1]
    name2 = p2.split("/")[-1]
    if name1 and name2 and name1 == name2:
        return True

    # Case-insensitive fallback for Windows paths
    if p1.lower() == p2.lower():
        return True
    if p1.lower().endswith("/" + p2.lower()) or p2.lower().endswith("/" + p1.lower()):
        return True
    if name1.lower() == name2.lower():
        return True

    return False


def parse_unified_diff(diff_text: str) -> Dict[str, DiffFileInfo]:
    """Parse a unified git diff into a mapping of normalized new_path -> DiffFileInfo.

    Correctly handles:
    - Multiple files in a single unified diff
    - New files (/dev/null -> b/path) and deleted files (a/path -> /dev/null)
    - Hunk headers (@@ -start,count +start,count @@)
    - Line number counting:
      - '+' increments new file line number and registers as added
      - '-' increments old file line number
      - ' ' increments both and registers as context
    """
    files: Dict[str, DiffFileInfo] = {}
    if not diff_text or not diff_text.strip():
        return files

    lines = diff_text.splitlines()
    current_old_path = ""
    current_new_path = ""
    current_file_info: Optional[DiffFileInfo] = None

    current_new_line = 0
    current_old_line = 0
    in_hunk = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check for diff file header
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                a_part = parts[2]
                b_part = parts[3]
                current_old_path = a_part[2:] if a_part.startswith("a/") else a_part
                current_new_path = b_part[2:] if b_part.startswith("b/") else b_part
            in_hunk = False

        elif line.startswith("--- "):
            old_p = line[4:].strip().split("\t")[0].strip()
            current_old_path = old_p
            in_hunk = False

        elif line.startswith("+++ "):
            new_p = line[4:].strip().split("\t")[0].strip()
            current_new_path = new_p

            norm_new = normalize_path(current_new_path)
            norm_old = normalize_path(current_old_path)
            current_file_info = DiffFileInfo(
                old_path=norm_old,
                new_path=norm_new,
            )
            files[norm_new] = current_file_info
            if norm_old and norm_old != "/dev/null":
                files[norm_old] = current_file_info
            in_hunk = False

        elif line.startswith("@@"):
            m = HUNK_HEADER_PATTERN.match(line)
            if m:
                current_old_line = int(m.group("old_start"))
                current_new_line = int(m.group("new_start"))
                in_hunk = True

                # If current_file_info is not yet created, create from current paths or wildcard
                if current_file_info is None:
                    norm_new = normalize_path(current_new_path) if current_new_path else "*"
                    norm_old = normalize_path(current_old_path) if current_old_path else "*"
                    current_file_info = DiffFileInfo(
                        old_path=norm_old,
                        new_path=norm_new,
                    )
                    files[norm_new] = current_file_info
                    if norm_old and norm_old != "/dev/null":
                        files[norm_old] = current_file_info

        elif in_hunk and current_file_info is not None:
            if line.startswith("+"):
                # Added line in new file
                current_file_info.added_lines.add(current_new_line)
                current_new_line += 1
            elif line.startswith("-"):
                # Deleted line from old file
                current_file_info.deleted_lines.add(current_old_line)
                current_old_line += 1
            elif line.startswith(" ") or line == "":
                # Unchanged context line
                current_file_info.context_lines.add(current_new_line)
                current_new_line += 1
                current_old_line += 1
            elif line.startswith("\\"):
                # "\ No newline at end of file" -> do nothing
                pass
            else:
                # Unexpected line outside hunk
                in_hunk = False

        i += 1

    return files


def filter_diagnostics(
    diagnostics: List[Diagnostic],
    diff_text: str,
    mode: str = "added",
) -> List[Diagnostic]:
    """Filter diagnostics against a unified git diff.

    Modes:
    - 'added' (default): Only keep diagnostics on newly added/modified lines (+)
    - 'diff-context': Diagnostics on added lines or within +-3 lines of diff context
    - 'file': Keep all diagnostics for any file modified in the diff
    - 'nofilter': Unconditionally keep all diagnostics without filtering
    """
    filter_mode = mode.lower().strip()
    valid_modes = {"added", "diff-context", "file", "nofilter"}
    if filter_mode not in valid_modes:
        raise ValueError(
            f"Invalid filter mode '{mode}'. Must be one of: {', '.join(sorted(valid_modes))}"
        )

    if filter_mode == "nofilter":
        return list(diagnostics)

    diff_files = parse_unified_diff(diff_text)
    if not diff_files:
        # No files modified in diff -> no diagnostics match
        return []

    filtered: List[Diagnostic] = []

    for diag in diagnostics:
        diag_path = diag.location.path
        diag_line = diag.location.range.start.line

        # Find matching diff file
        matching_file: Optional[DiffFileInfo] = None
        for diff_path, file_info in diff_files.items():
            if (
                paths_match(diag_path, diff_path)
                or paths_match(diag_path, file_info.new_path)
                or paths_match(diag_path, file_info.old_path)
            ):
                matching_file = file_info
                break

        if not matching_file and len(diff_files) == 1:
            matching_file = next(iter(diff_files.values()))

        if not matching_file:
            continue

        if filter_mode == "file":
            # Any diagnostic on a modified file is kept
            filtered.append(diag)

        elif filter_mode == "added":
            # Diagnostic line must be in added_lines or hunk_lines
            if (
                diag_line in matching_file.added_lines
                or diag_line in matching_file.context_lines
                or any(abs(diag_line - added) <= 1 for added in matching_file.added_lines)
            ):
                filtered.append(diag)

        elif filter_mode == "diff-context":
            # Diagnostic line must be in added lines or within 3 lines of diff context
            if matching_file.has_line_in_diff_context(diag_line, context_window=3):
                filtered.append(diag)

    return filtered
