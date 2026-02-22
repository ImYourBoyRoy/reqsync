# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [SemVer](https://semver.org/). Versions are derived from Git tags via `hatch-vcs` (`vX.Y.Z`).

## [Unreleased]

### Added
- Root `--version` / `-V` CLI option for quick version checks.
- Built-in MCP server (`reqsync mcp`, `reqsync-mcp`) with `reqsync_sync` tool outputting structured JSON.
- New programmatic integration helpers in `reqsync.api` (`options_from_mapping`, `run_sync_payload`).
- Advisory lock timeout support via `lock_timeout_sec` / `--lock-timeout-sec`.
- Automatic backup pruning via `backup_keep_last` / `--backup-keep-last` (default keeps 5 timestamped backups per file).
- Git cleanliness guard wiring for `--allow-dirty` behavior.
- Test bootstrap `tests/conftest.py` to scrub `__pycache__` and ensure src importability.

### Changed
- Core sync engine rewritten for clearer include/constraint graph handling and deterministic processing.
- `--check` mode now correctly reports real drift state (no forced true-positive).
- Hash guard now applies to all processed files (root + includes), not only the root file.
- CLI updated with `--stdout-json` for direct agent/toolchain ingestion.
- Documentation fully aligned to current command model (`reqsync run [OPTIONS]`, `reqsync mcp ...`).

### Fixed
- Removed brittle CLI error-code string matching in favor of typed exceptions.
- Corrected metadata author email and aligned runtime dependencies with actual runtime features.

---

## [v0.1.0] — 2025-08-18

Initial public release.

---

[Unreleased]: https://github.com/ImYourBoyRoy/reqsync/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/ImYourBoyRoy/reqsync/releases/tag/v0.1.0
