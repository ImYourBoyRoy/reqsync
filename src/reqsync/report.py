# src/reqsync/report.py

from __future__ import annotations

import difflib
import json
from pathlib import Path

from ._types import Change, FileChange, JsonChange, JsonReport


def make_diff(files: list[FileChange]) -> str:
    chunks: list[str] = []
    for fc in files:
        diff = difflib.unified_diff(
            fc.original_text.splitlines(keepends=True),
            fc.new_text.splitlines(keepends=True),
            fromfile=f"{fc.file} (old)",
            tofile=f"{fc.file} (new)",
        )
        chunks.append("".join(diff))
    return "\n".join(chunks)


def summarize_changes(changes: list[Change]) -> str:
    if not changes:
        return "No changes."
    rows = [f"{c.package}: -> >= {c.installed_version} [{c.file.name}]" for c in changes]
    return "\n".join(rows)


def to_json_report(files: list[FileChange]) -> JsonReport:
    file_list = [str(f.file) for f in files]
    changes: list[JsonChange] = []
    for fc in files:
        for ch in fc.changes:
            changes.append(
                {
                    "file": str(ch.file),
                    "package": ch.package,
                    "installed_version": ch.installed_version,
                    "old_line": ch.old_line.rstrip("\n"),
                    "new_line": ch.new_line.rstrip("\n"),
                }
            )
    return {"files": file_list, "changes": changes}


def write_json_report(report: JsonReport, path: str) -> None:
    # If a directory was provided, write a sensible default filename
    p = Path(path)
    if p.exists() and p.is_dir():
        p = p / "reqsync-report.json"
    elif str(p) in {"", "."}:
        p = Path("reqsync-report.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
