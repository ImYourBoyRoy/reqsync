# docs/USAGE.md

# reqsync — Usage

## Synopsis
Fast, safe way to upgrade a venv and rewrite requirements.txt so each top-level package is set to `>= installed_version`. Defaults are conservative. It refuses to run outside a venv unless you say otherwise.

## Quickstart
```bash
# 1) Activate your virtualenv (required by default)
source .venv/bin/activate

# 2) Preview changes (no writes)
reqsync run --path requirements.txt --dry-run --show-diff

# 3) Apply changes with backup
reqsync run --path requirements.txt --show-diff
````

## What it does

1. Validates you’re in a virtualenv (unless you pass `--system-ok`).
2. Runs `pip install -U -r <file>` by default to upgrade the env. Skip with `--no-upgrade`.
3. Reads installed package versions.
4. Rewrites each package line in your requirements files to set a lower bound `>=installed`, preserving extras, markers, inline comments, and file formatting.
5. Backs up before writing, then writes atomically.
6. Refuses to edit files that contain `--hash=` unless you opt in to skipping those stanzas.

## What it won’t do

* It won’t recompute or update `--hash=` values. Use pip-tools if you need hashed lockfiles.
* It won’t touch `constraints.txt` unless you ask it to.
* It won’t make your build deterministic. If you want full locks, pair with `constraints.txt`.

## CLI

```bash
reqsync run [OPTIONS]
```

### Key options

* `--path PATH` path to the primary `requirements.txt` (default: `requirements.txt`)
* `--follow-includes / --no-follow-includes` follow `-r other.txt` recursively (default: true)
* `--update-constraints` also modify constraint files (default: false)
* `--policy [lower-bound|floor-only|floor-and-cap]` default: `lower-bound`
* `--allow-prerelease` adopt pre/dev versions from your env (default: false)
* `--keep-local` keep local version suffixes like `+cpu` (default: false)
* `--no-upgrade` skip `pip install -U` and only rewrite from currently installed
* `--pip-args "..."` safe allowlisted pip args (indexes, proxies, constraints, etc.)
* `--only patterns` comma-separated globs to include (canonical package names)
* `--exclude patterns` comma-separated globs to exclude
* `--check` exit nonzero if changes would be made; don’t write
* `--dry-run` don’t write; with `--show-diff` to see a unified diff
* `--json-report FILE` write machine-readable change report
* `--backup-suffix S` default `.bak`
* `--timestamped-backups / --no-timestamped-backups` default: timestamped
* `--log-file FILE` optional file logging (console logging is on by default)
* `-v, -vv` increase verbosity; `-q` quiet
* `--system-ok` allow running outside a venv (not recommended)
* `--allow-hashes` skip hashed stanzas instead of refusing
* `--last-wins` when duplicate package appears across included files, use the last

### Policies explained

* `lower-bound` (default): set specifier to `>= installed`.
* `floor-only`: only raise an existing lower bound; do not add one if missing.
* `floor-and-cap`: set `>= installed,<next_major` (cap strategy defaults to next major).

### Includes and constraints

* Lines starting with `-r` or `--requirement` are followed if `--follow-includes` is true.
* `-c` / `--constraint` files are detected but not modified unless `--update-constraints` is set.

### Hashes

* If any line contains `--hash=`, reqsync refuses by default.
* Override with `--allow-hashes` to leave those stanzas untouched and continue.

### VCS/URLs/Editables/Directives

* `git+...`, `https://...`, local paths, and `-e/--editable` are preserved and skipped.
* Pip directives like `--index-url`, `--extra-index-url`, `--find-links`, `--trusted-host`, `--no-index` are preserved and skipped.

## Exit codes

| Code | Meaning                                                       |
| ---: | ------------------------------------------------------------- |
|    0 | Success (changes written or nothing to do)                    |
|    1 | Generic error                                                 |
|    2 | Requirements file not found                                   |
|    3 | Hashes present without `--allow-hashes`                       |
|    4 | Pip upgrade failed                                            |
|    5 | Parse error                                                   |
|    6 | Constraint conflict detected                                  |
|    7 | Refused to run outside venv without `--system-ok`             |
|    8 | Repo dirty and guard blocked (only if you enable that policy) |
|    9 | Lock acquisition timeout                                      |
|   10 | Write failed; backup restored                                 |
|   11 | `--check` mode and changes would be made                      |

## Practical examples

Raise floors but don’t cap:

```bash
reqsync run --path requirements.txt
```

Skip upgrade, only sync file to current env:

```bash
reqsync run --no-upgrade --show-diff
```

Adopt pre-releases and keep local suffixes:

```bash
reqsync run --allow-prerelease --keep-local
```

Process a monorepo with nested includes:

```bash
reqsync run --path requirements/base.txt --follow-includes
```

CI check only:

```bash
reqsync run --check --no-upgrade --path requirements.txt
```

Emit JSON report for tooling:

```bash
reqsync run --json-report .artifacts/reqsync.json --dry-run
```

## Troubleshooting

* “Refusing to run outside a virtualenv”: activate your venv or pass `--system-ok`.
* “Hashes present”: either run with `--allow-hashes` to skip or regenerate with pip-compile.
* “pip failed”: pass mirrors/proxies via `--pip-args`, or check network constraints.
* “Windows CRLF changed to LF”: reqsync preserves line endings; if you see churn, your editor is changing them.