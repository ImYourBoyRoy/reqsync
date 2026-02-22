# ./src/reqsync/_types.py
"""Core reqsync type contracts shared by CLI, API, and MCP integrations.

Used by all orchestration layers to keep sync options, change tracking, and
exit-code behavior consistent. Import these models when calling reqsync from
Python, CLI wrappers, or model-tool adapters.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Literal, TypedDict

Policy = Literal["lower-bound", "floor-only", "floor-and-cap", "update-in-place"]
FileRole = Literal["root", "requirement", "constraint"]


class ExitCode(IntEnum):
    """Stable process exit codes for CLI and MCP callers."""

    OK = 0
    GENERIC_ERROR = 1
    MISSING_FILE = 2
    HASHES_PRESENT = 3
    PIP_FAILED = 4
    PARSE_ERROR = 5
    CONSTRAINT_CONFLICT = 6
    SYSTEM_PYTHON_BLOCKED = 7
    DIRTY_REPO_BLOCKED = 8
    LOCK_TIMEOUT = 9
    WRITE_FAILED_ROLLED_BACK = 10
    CHANGES_WOULD_BE_MADE = 11


@dataclass(frozen=True)
class Options:
    """Runtime options for a single reqsync operation."""

    path: Path
    follow_includes: bool = True
    update_constraints: bool = False
    policy: Policy = "lower-bound"
    allow_prerelease: bool = False
    keep_local: bool = False
    no_upgrade: bool = False
    pip_timeout_sec: int = 900
    pip_args: str = ""
    only: Sequence[str] = ()
    exclude: Sequence[str] = ()
    check: bool = False
    dry_run: bool = False
    show_diff: bool = False
    json_report: Path | None = None
    backup_suffix: str = ".bak"
    timestamped_backups: bool = True
    backup_keep_last: int = 5
    lock_timeout_sec: int = 15
    log_file: Path | None = None
    verbosity: int = 0
    quiet: bool = False
    system_ok: bool = False
    allow_hashes: bool = False
    allow_dirty: bool = True
    last_wins: bool = False


@dataclass(frozen=True)
class Change:
    """A single package-line rewrite."""

    package: str
    installed_version: str
    old_line: str
    new_line: str
    file: Path


@dataclass
class FileChange:
    """All changes for one requirements file."""

    file: Path
    role: FileRole = "requirement"
    changes: list[Change] = field(default_factory=list)
    original_text: str = ""
    new_text: str = ""


@dataclass(frozen=True)
class ResolvedFile:
    """A discovered requirements file and how it was reached."""

    path: Path
    role: FileRole


@dataclass
class Result:
    """Structured outcome of a sync call."""

    changed: bool
    files: list[FileChange]
    diff: str | None = None
    backup_paths: list[Path] = field(default_factory=list)


class JsonChange(TypedDict):
    file: str
    package: str
    installed_version: str
    old_line: str
    new_line: str


class JsonFileResult(TypedDict):
    file: str
    role: FileRole
    changed: bool
    change_count: int


class JsonResult(TypedDict):
    changed: bool
    files: list[JsonFileResult]
    changes: list[JsonChange]
    backup_paths: list[str]
    diff: str | None


__all__ = [
    "Change",
    "ExitCode",
    "FileChange",
    "FileRole",
    "JsonChange",
    "JsonFileResult",
    "JsonResult",
    "Options",
    "Policy",
    "ResolvedFile",
    "Result",
]
