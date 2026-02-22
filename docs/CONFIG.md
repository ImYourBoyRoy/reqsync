# reqsync — Configuration

## Synopsis
Configuration is optional. CLI flags always override config values.

## Resolution order
1. CLI flags
2. `reqsync.toml`
3. `[tool.reqsync]` in `pyproject.toml`
4. `reqsync.json`
5. Defaults

## `reqsync.toml` example

```toml
path = "requirements.txt"
follow_includes = true
update_constraints = false
policy = "lower-bound"
allow_prerelease = false
keep_local = false
no_upgrade = false
pip_timeout_sec = 900
pip_args = ""
only = []
exclude = []
check = false
dry_run = false
show_diff = false
json_report = ""
backup_suffix = ".bak"
timestamped_backups = true
backup_keep_last = 5
lock_timeout_sec = 15
log_file = ""
verbosity = 0
quiet = false
system_ok = false
allow_hashes = false
allow_dirty = true
last_wins = false
```

## `pyproject.toml` example

```toml
[tool.reqsync]
path = "requirements.txt"
policy = "floor-and-cap"
no_upgrade = true
show_diff = true
```

## `reqsync.json` example

```json
{
  "path": "requirements/base.txt",
  "policy": "update-in-place",
  "dry_run": true,
  "show_diff": true
}
```

## Field notes

- `policy`: `lower-bound`, `floor-only`, `floor-and-cap`, `update-in-place`
- `pip_args`: allowlisted options only (`--index-url`, `--extra-index-url`, `--trusted-host`, `--find-links`, `--proxy`, `--retries`, `--timeout`, `-r`, `--requirement`, `-c`, `--constraint`, `--no-deps`)
- `only` / `exclude`: package globs (comma string or list)
- `backup_keep_last`: max timestamped backups to retain per file (`0` disables pruning)
- `lock_timeout_sec`: lock wait timeout before exiting code `9`

## Security note

Avoid storing secrets directly in project config. Prefer environment variables or pip config for credentials.
