# ./src/reqsync/report.py
"""Reporting utilities for human and machine consumers.

Provides unified diffs, concise summaries, and JSON serialization helpers used
by the CLI, Python API, and MCP server integrations.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from ._types import Change, FileChange, JsonChange, JsonFileResult, JsonResult, Result


def make_diff(files: list[FileChange]) -> str:
    """Build a unified diff for files that actually changed."""

    chunks: list[str] = []
    for file_change in files:
        if file_change.original_text == file_change.new_text:
            continue
        diff = difflib.unified_diff(
            file_change.original_text.splitlines(keepends=True),
            file_change.new_text.splitlines(keepends=True),
            fromfile=f"{file_change.file} (old)",
            tofile=f"{file_change.file} (new)",
        )
        chunks.append("".join(diff))
    return "\n".join(chunk for chunk in chunks if chunk)


def summarize_changes(changes: list[Change]) -> str:
    """Produce a readable one-line-per-change summary."""

    if not changes:
        return "No changes."
    rows = [f"{change.package}: -> >= {change.installed_version} [{change.file.name}]" for change in changes]
    return "\n".join(rows)


def to_json_report(files: list[FileChange]) -> JsonResult:
    """Serialize file changes to a JSON-safe dictionary."""

    file_rows: list[JsonFileResult] = []
    change_rows: list[JsonChange] = []

    for file_change in files:
        file_rows.append(
            {
                "file": str(file_change.file),
                "role": file_change.role,
                "changed": file_change.original_text != file_change.new_text,
                "change_count": len(file_change.changes),
            }
        )
        for change in file_change.changes:
            change_rows.append(
                {
                    "file": str(change.file),
                    "package": change.package,
                    "installed_version": change.installed_version,
                    "old_line": change.old_line.rstrip("\n\r"),
                    "new_line": change.new_line.rstrip("\n\r"),
                }
            )

    return {
        "changed": any(row["changed"] for row in file_rows),
        "files": file_rows,
        "changes": change_rows,
        "backup_paths": [],
        "diff": None,
    }


def result_to_json(result: Result) -> JsonResult:
    """Serialize a full sync result including backups and optional diff."""

    report = to_json_report(result.files)
    report["changed"] = result.changed
    report["backup_paths"] = [str(path) for path in result.backup_paths]
    report["diff"] = result.diff
    return report


def write_json_report(report: JsonResult, path: str) -> Path:
    """Write JSON report to file path and return resolved output path."""

    target = Path(path)
    if target.exists() and target.is_dir():
        target = target / "reqsync-report.json"
    elif str(target).strip() in {"", "."}:
        target = Path("reqsync-report.json")

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    return target


__all__ = [
    "make_diff",
    "result_to_json",
    "summarize_changes",
    "to_json_report",
    "write_json_report",
]
