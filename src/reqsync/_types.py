# src/reqsync/_types.py

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

Policy = Literal["lower-bound", "floor-only", "floor-and-cap"]


class ExitCode:
    OK = 0
    GENERIC_ERROR = 1
    MISSING_FILE = 2
    HASHES_PRESENT = 3
    PIP_FAILED = 4
    PARSE_ERROR = 5
    CONSTRAINT_CONFLICT = 6
    SYSTEM_PYTHON_BLOCKED = 7
    DIRTY_REPO_BLOCKED = 8
    WRITE_FAILED_ROLLED_BACK = 10
    CHANGES_WOULD_BE_MADE = 11


@dataclass
class Options:
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
    log_file: Path | None = None
    verbosity: int = 0
    quiet: bool = False
    system_ok: bool = False
    allow_hashes: bool = False
    allow_dirty: bool = True
    last_wins: bool = False


@dataclass
class Change:
    package: str
    installed_version: str
    old_line: str
    new_line: str
    file: Path


@dataclass
class FileChange:
    file: Path
    changes: list[Change] = field(default_factory=list)
    original_text: str = ""
    new_text: str = ""


@dataclass
class Result:
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


class JsonReport(TypedDict):
    files: list[str]
    changes: list[JsonChange]


__all__ = [
    "Change",
    "ExitCode",
    "FileChange",
    "JsonChange",
    "JsonReport",
    "Options",
    "Policy",
    "Result",
]
