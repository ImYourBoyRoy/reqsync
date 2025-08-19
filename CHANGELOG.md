# CHANGELOG.md

# Changelog
All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [SemVer](https://semver.org/).
Version numbers are derived from Git tags via `hatch-vcs` (tags must be `vX.Y.Z`).

## [Unreleased]
### Planned
- Per-package cap strategies (next-minor, calendar-based) via config.
- Git cleanliness guard (block writes on dirty repo unless `--allow-dirty`).
- Optional pretty console output using `rich`.

---

## [v0.1.0] — 2025-08-18
### Added
- Core command `reqsync run` to:
  - Upgrade the active environment with `pip install -U -r <file>` (skippable with `--no-upgrade`).
  - Rewrite requirement lines to **lower-bound** floors (`>= installed_version`) while preserving:
    - extras (`pkg[extra1,extra2]`)
    - markers (`; sys_platform == "win32"`)
    - inline comments and spacing
    - file encoding (BOM) and newline style (LF/CRLF)
  - Backup existing files and perform atomic writes with rollback on failure.
- **Venv guard**: refuses to run outside a virtualenv by default; override with `--system-ok`.
- **Safety gates**:
  - Abort if any line contains `--hash=` unless `--allow-hashes` is set (then hashed stanzas are skipped, never edited).
  - Skip VCS/URL/local paths and editables (`-e/--editable`) and all pip directives (`-r`, `-c`, `--index-url`, etc.).
  - File locking with `portalocker` to prevent concurrent edits.
- **Policy engine**:
  - `lower-bound` (default), `floor-only`, and `floor-and-cap` (cap defaults to next major).
  - Controls for pre/dev and local versions: `--allow-prerelease`, `--keep-local`.
- **Includes and constraints**:
  - Recursive processing of `-r` includes (on by default).
  - Detect but don’t modify constraint files unless `--update-constraints` is set.
  - Option `--last-wins` to resolve duplicates across included files.
- **UX & CI**:
  - `--dry-run` with optional `--show-diff` unified diff.
  - `--check` mode exits nonzero if changes would be made (no writes).
  - `--json-report` to emit a machine-readable change log for tooling.
  - Allowlisted `--pip-args` passthrough for indexes/proxies (safe subset only).
  - `--only`/`--exclude` globs to scope which packages are updated.
  - Verbosity flags (`-v`, `-vv`) and optional file logging with secret redaction.
- **APIs & docs**:
  - Clean Python API: `reqsync.core.sync(Options)` returning a structured `Result`.
  - Docs: USAGE, CONFIG, INTEGRATION. Examples: config presets and minimal API usage.
- **Tooling & release**:
  - `pyproject.toml` with `hatchling` + `hatch-vcs` dynamic versioning.
  - CI workflow (lint, type-check, test, build, twine check, wheel smoke test).
  - PyPI Trusted Publishing workflow via OIDC (no secrets).

### Fixed
- N/A. First release.

### Security
- Redacts common token shapes from logs (index credentials, tokens) by default.

### Known limitations (by design)
- Does not recompute or update `--hash` lines. Use `pip-compile` if you need hashed lockfiles.
- Does not manage transitive dependency locks. Pair with a `constraints.txt` if you need determinism.
- Assumes the active interpreter’s environment is the source of truth.

---

[Unreleased]: https://github.com/ImYourBoyRoy/reqsync/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/ImYourBoyRoy/reqsync/releases/tag/v0.1.0
