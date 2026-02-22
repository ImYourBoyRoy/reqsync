# reqsync — Usage

## Synopsis
`reqsync` synchronizes requirement lines to installed versions with atomic writes, backups, include traversal, hash safety guards, and machine-readable output modes.

## Quickstart

```bash
# 1) Activate your virtualenv (required by default)
source .venv/bin/activate

# 2) Preview changes
reqsync run --path requirements.txt --no-upgrade --dry-run --show-diff

# 3) Apply changes
reqsync run --path requirements.txt --show-diff
```

## Command forms

```bash
reqsync run [OPTIONS]
reqsync help [all|run|version|mcp]
reqsync --version
reqsync version
reqsync mcp [--transport stdio|sse|streamable-http]
```

Discoverability tip:

```bash
reqsync help all
reqsync run --help
```

## Key options

- `--path PATH`
- `--follow-includes / --no-follow-includes`
- `--update-constraints`
- `--policy [lower-bound|floor-only|floor-and-cap|update-in-place]`
- `--allow-prerelease`
- `--keep-local`
- `--no-upgrade`
- `--pip-timeout-sec INT`
- `--pip-args "..."`
- `--only "pkg1,pkg2"`
- `--exclude "pkgA,pkgB"`
- `--check`
- `--dry-run`
- `--show-diff`
- `--output [human|json|both]`
- `--json-report PATH`
- `--backup-suffix TEXT`
- `--timestamped-backups / --no-timestamped-backups`
- `--backup-keep-last INT` (default `5`, `0` disables pruning)
- `--lock-timeout-sec INT`
- `--log-file PATH`
- `-v / -vv`
- `-q / --quiet`
- `--system-ok`
- `--allow-hashes`
- `--allow-dirty`
- `--last-wins`
- `--use-config / --no-use-config`

## Practical examples

```bash
# Standard sync
reqsync run --path requirements.txt

# CI drift gate (no writes)
reqsync run --check --no-upgrade --path requirements.txt

# JSON for tooling
reqsync run --dry-run --no-upgrade --output json

# Process include graph rooted at file
reqsync run --path requirements/base.txt --follow-includes

# Also rewrite files reached via -c/--constraint
reqsync run --update-constraints --path requirements/base.txt
```

## Safety behavior

- Refuses outside virtualenv unless `--system-ok`.
- Refuses hash-pinned files unless `--allow-hashes`.
- Can block dirty repos when `--allow-dirty` is disabled.
- Uses advisory lock + atomic write + backups for resilient writes.

## Exit codes

| Code | Meaning |
| ---: | ------- |
| 0 | Success |
| 1 | Generic error |
| 2 | Requirements file not found |
| 3 | Hashes present without `--allow-hashes` |
| 4 | pip upgrade failed |
| 7 | Refused outside virtualenv |
| 8 | Dirty repo blocked |
| 9 | Lock acquisition timeout |
| 10 | Write failed; backups restored |
| 11 | `--check` detected drift |
