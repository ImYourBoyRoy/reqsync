# reqsync — Integration Guide

## Synopsis
`reqsync` supports direct Python embedding, CLI automation, and a built-in MCP server for local AI model clients.

## Python API

```python
from reqsync.api import run_sync_payload

payload = {
    "path": "requirements.txt",
    "dry_run": True,
    "no_upgrade": True,
    "show_diff": True,
    "policy": "lower-bound",
}
result = run_sync_payload(payload)
print(result["changed"])
```

Returned keys:

- `changed: bool`
- `files: list[{file, role, changed, change_count}]`
- `changes: list[{file, package, installed_version, old_line, new_line}]`
- `backup_paths: list[str]`
- `diff: str | null`

## CLI as subprocess

```bash
reqsync run --no-upgrade --dry-run --json-report .artifacts/reqsync.json --show-diff
```

## MCP server

### Start server

```bash
# stdio transport (default)
reqsync mcp

# alternate transport
reqsync mcp --transport sse
```

### Exposed tool

- `reqsync_sync`
  - Input params: `path`, `dry_run`, `check`, `show_diff`, `no_upgrade`, `policy`, `follow_includes`, `update_constraints`, `allow_prerelease`, `keep_local`, `allow_hashes`, `system_ok`, `allow_dirty`, `pip_args`, `pip_timeout_sec`
  - Return shape: `{ "ok": bool, "exit_code": int, "error": str|null, "result": JsonResult|null }`

## CI patterns

### Drift check

```bash
reqsync run --check --no-upgrade --path requirements.txt
```

### Suggested pipeline steps

1. `ruff check .`
2. `ruff format --check .`
3. `mypy src/reqsync`
4. `pytest -q`
5. `python -m build`
6. `python -m twine check dist/*`

## Operational tips

- Prefer `--no-upgrade` in CI for deterministic speed.
- Use `--stdout-json` or `--json-report` for agent orchestration.
- Keep `--allow-hashes` disabled unless you intentionally want hash lines skipped.
