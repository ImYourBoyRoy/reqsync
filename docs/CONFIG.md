# docs/CONFIG.md

# reqsync — Configuration

## Synopsis
Config is optional. Command-line flags always win. If you use config, keep it small and explicit.

## Where config is read from
Resolution order (earlier wins):
1. CLI flags
2. `reqsync.toml` at project root
3. `[tool.reqsync]` in `pyproject.toml`
4. `reqsync.json` at project root
5. Built-in defaults

## reqsync.toml example
```toml
# reqsync.toml
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
log_file = ""
verbosity = 0
quiet = false
system_ok = false
allow_hashes = false
allow_dirty = true
last_wins = false
````

## pyproject.toml example

```toml
[tool.reqsync]
path = "requirements.txt"
policy = "lower-bound"
allow_prerelease = false
```

## JSON example

```json
{
  "path": "requirements.in",
  "policy": "floor-and-cap",
  "allow_prerelease": true,
  "only": ["langchain*", "crewai"]
}
```

## Field reference

* `path` string. Primary requirements file.
* `follow_includes` bool. Follow `-r` includes recursively.
* `update_constraints` bool. Allow modifying constraint files. Off by default.
* `policy` string. `lower-bound` | `floor-only` | `floor-and-cap`.
* `allow_prerelease` bool. Adopt pre/dev versions from env.
* `keep_local` bool. Keep local suffix `+tag`.
* `no_upgrade` bool. Skip `pip install -U`.
* `pip_timeout_sec` int. Timeout for pip upgrade.
* `pip_args` string. Allowlisted args only (`--index-url`, `--extra-index-url`, `--find-links`, `--trusted-host`, `--proxy`, `--retries`, `--timeout`, `-r`, `-c`).
* `only` array of globs. Limit which packages are updated.
* `exclude` array of globs. Exclude packages from updating.
* `check` bool. Don’t write; exit 11 if changes would be made.
* `dry_run` bool. Don’t write. With `show_diff` for preview.
* `show_diff` bool. Print unified diff for changed files.
* `json_report` string. Output file for machine-readable changes.
* `backup_suffix` string. Suffix for backup file.
* `timestamped_backups` bool. Timestamp your backups.
* `log_file` string. Optional file log. Empty disables.
* `verbosity` int. 0 warn, 1 info, 2 debug (CLI `-v` `-vv` overrides).
* `quiet` bool. Suppress info/debug to console.
* `system_ok` bool. Allow running outside a venv.
* `allow_hashes` bool. Skip `--hash` stanzas instead of refusing.
* `allow_dirty` bool. If you add a git-guard later, this toggles it.
* `last_wins` bool. Resolve duplicates across includes with last occurrence.

## Precedence rules

* CLI overrides config. Example: `--allow-prerelease` beats config false.
* Empty strings in config are treated as unset. Arrays are used verbatim.

## Hard truths

* Don’t put secrets in config. If you’re passing index URLs with creds, prefer `PIP_INDEX_URL` env vars or a pip config file. If you must use `--pip-args`, logs redact common token shapes, but don’t rely on that as security.