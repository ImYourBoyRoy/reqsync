# docs/INTEGRATION.md

# reqsync — Integration Guide

## Synopsis
Use the Python API for automation and agents. It returns a structured `Result` with file diffs and changes. Keep the runtime dependencies small so it’s easy to embed.

## Python API
```python
# Minimal example
from pathlib import Path
from reqsync._types import Options
from reqsync.core import sync

opts = Options(
    path=Path("requirements.txt"),
    allow_prerelease=False,
    follow_includes=True,
    policy="lower-bound",
    dry_run=True,
    show_diff=True,
)
result = sync(opts)
print("Changed:", result.changed)
print(result.diff or "")
````

### Result object

* `changed: bool` whether any file would change
* `files: List[FileChange]` for each processed file:

  * `file: Path`
  * `original_text: str`
  * `new_text: str`
  * `changes: List[Change]` with `package`, `installed_version`, `old_line`, `new_line`
* `diff: Optional[str]` unified diff if requested
* `backup_paths: List[Path]` written when changes are applied

## Using as a subprocess (shell)

```bash
# Preview and get JSON changes for tooling
reqsync run --dry-run --json-report .artifacts/reqsync.json --show-diff
```

## CrewAI/AG2 tool adapter

Keep it dead simple: pass options and parse JSON.

```python
# tools/reqsync_tool.py
from pathlib import Path
import json
import subprocess, sys

def run_reqsync(path="requirements.txt", dry_run=True, show_diff=True, allow_prerelease=False):
    cmd = [
        sys.executable, "-m", "reqsync.cli", "run",
        "--path", path,
        "--dry-run" if dry_run else "",
        "--show-diff" if show_diff else "",
        "--allow-prerelease" if allow_prerelease else "",
        "--json-report", ".artifacts/reqsync.json",
    ]
    cmd = [c for c in cmd if c != ""]
    subprocess.run(cmd, check=True)
    with open(".artifacts/reqsync.json", "r", encoding="utf-8") as f:
        return json.load(f)
```

Use in an agent step to assert the repo is clean or to propose changes.

## Minimal MCP tool concept

Expose one command that accepts a JSON options payload and returns the JSON report plus a diff preview.

Request schema (example):

```json
{
  "path": "requirements.txt",
  "dry_run": true,
  "check": false,
  "allow_prerelease": false,
  "policy": "lower-bound"
}
```

Response structure:

```json
{
  "changed": true,
  "diff": "@@ ...",
  "changes": [
    {"file": "requirements.txt", "package": "pandas", "installed_version": "2.2.2", "old_line": "pandas>=2.0.0", "new_line": "pandas>=2.2.2"}
  ]
}
```

Implementation notes:

* Call the Python API directly (`sync(Options(...))`) for in-process serving.
* Or invoke the CLI with `--json-report` and read the file.
* Timebox runs if you allow `--no-upgrade=false` to avoid long resolver waits.

## CI integration

### GitHub Actions gate (already provided)

Use `--check --no-upgrade` to enforce the file is in sync without modifying anything:

```yaml
- name: Enforce reqsync
  run: |
    reqsync run --check --no-upgrade --path requirements.txt
```

### Pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.7
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: local
    hooks:
      - id: reqsync
        name: reqsync (sync floors)
        entry: reqsync run --no-upgrade
        language: system
        pass_filenames: false
```

## Safety reminders for integrators

* Default refuses to run outside a venv. Use `system_ok=True` only if you know what you’re doing.
* Hashed files are blocked by default. If you enable `--allow-hashes`, reqsync will skip those stanzas, not fix them.
* Atomic writes with backups mean you can run in CI safely. If a write fails, reqsync rolls back and returns a nonzero exit.

## Performance tips

* For large envs, prefer `--no-upgrade` in read-only checks.
* If you must pass pip mirrors, use `--pip-args` with allowlisted flags only.
* Avoid scanning massive include trees unless you need to; set `--no-follow-includes` for single-file speed.