# ./src/reqsync/core.py
"""Reqsync orchestration engine.

Coordinates environment safety checks, include-graph resolution, policy-based
rewrites, atomic backups/writes, and structured reporting for CLI/API callers.
"""

from __future__ import annotations

import fnmatch
import logging
import shutil
from pathlib import Path

from packaging.utils import canonicalize_name

from . import env as env_mod
from . import report as report_mod
from ._types import Change, FileChange, FileRole, Options, ResolvedFile, Result
from .errors import MissingRequirementsFileError, PipUpgradeFailedError, WriteRollbackError
from .io import advisory_lock, backup_file, read_text_preserve, write_text_preserve
from .parse import find_file_links, guard_hashes, parse_line
from .policy import CapStrategy, apply_policy


def _match(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _should_skip_pkg(pkg_name: str, only: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    if only and not _match(pkg_name, only):
        return True
    if exclude and _match(pkg_name, exclude):
        return True
    return False


def _merge_role(current: FileRole, discovered: FileRole) -> FileRole:
    if current == "root" or discovered == "root":
        return "root"
    if current == "requirement" or discovered == "requirement":
        return "requirement"
    return "constraint"


def _resolve_files(root: Path, follow: bool) -> list[ResolvedFile]:
    """Resolve root + linked requirement/constraint files in deterministic order."""

    root_resolved = root.resolve()
    roles: dict[Path, FileRole] = {root_resolved: "root"}
    order: list[Path] = [root_resolved]

    if not follow:
        return [ResolvedFile(path=root_resolved, role="root")]

    queue: list[Path] = [root_resolved]
    while queue:
        current = queue.pop(0)
        text, _newline, _bom = read_text_preserve(current)
        for ref in find_file_links(text.splitlines()):
            candidate = (current.parent / ref.path).resolve()
            if not candidate.exists():
                logging.warning("Linked requirements file not found (kept directive): %s", candidate)
                continue

            discovered_role: FileRole = "constraint" if ref.kind == "constraint" else "requirement"
            existing_role = roles.get(candidate)
            if existing_role is None:
                roles[candidate] = discovered_role
                order.append(candidate)
                queue.append(candidate)
                continue

            merged = _merge_role(existing_role, discovered_role)
            if merged != existing_role:
                roles[candidate] = merged

    return [ResolvedFile(path=file_path, role=roles[file_path]) for file_path in order]


def _collect_last_occurrence_positions(
    text_by_path: dict[Path, str],
    ordered_files: list[ResolvedFile],
) -> set[tuple[Path, int]]:
    """Return positions for the last package occurrence per canonicalized name."""

    last_positions: dict[str, tuple[Path, int]] = {}
    for resolved in ordered_files:
        lines = text_by_path[resolved.path].splitlines(keepends=True)
        for line_index, line in enumerate(lines):
            parsed = parse_line(line)
            if parsed.kind != "package" or not parsed.requirement:
                continue
            canonical = canonicalize_name(parsed.requirement.name)
            last_positions[canonical] = (resolved.path, line_index)

    return set(last_positions.values())


def _rewrite_text(
    path: Path,
    text: str,
    installed: dict[str, str],
    options: Options,
    cap: CapStrategy | None,
    writable_positions: set[tuple[Path, int]] | None,
) -> tuple[str, list[Change]]:
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    changes: list[Change] = []

    for line_index, line in enumerate(lines):
        parsed = parse_line(line)

        if parsed.kind != "package" or not parsed.requirement:
            out_lines.append(line)
            continue

        base_name = canonicalize_name(parsed.requirement.name)

        if writable_positions is not None and (path, line_index) not in writable_positions:
            out_lines.append(line)
            continue

        if _should_skip_pkg(base_name, tuple(options.only), tuple(options.exclude)):
            out_lines.append(line)
            continue

        installed_version = installed.get(base_name)
        if installed_version is None:
            logging.warning("Not installed after upgrade: %s (kept)", parsed.requirement.name)
            out_lines.append(line)
            continue

        rewritten = apply_policy(
            req=parsed.requirement,
            installed_version=installed_version,
            policy=options.policy,
            allow_prerelease=options.allow_prerelease,
            keep_local=options.keep_local,
            cap_strategy=cap,
        )

        if rewritten is None:
            out_lines.append(line)
            continue

        rewritten_line = f"{rewritten}{parsed.comment}{parsed.eol}"
        if rewritten_line != line:
            changes.append(
                Change(
                    package=parsed.requirement.name,
                    installed_version=installed_version,
                    old_line=line,
                    new_line=rewritten_line,
                    file=path,
                )
            )
            out_lines.append(rewritten_line)
            continue

        out_lines.append(line)

    return "".join(out_lines), changes


def _restore_backups(written_pairs: list[tuple[Path, Path]]) -> None:
    """Best-effort restore previously written files from backups."""

    for target, backup in written_pairs:
        try:
            shutil.copy2(backup, target)
        except Exception:
            continue


def sync(options: Options) -> Result:
    """Synchronize requirement files to current installed versions."""

    root = options.path.resolve()
    if not root.exists():
        raise MissingRequirementsFileError(str(root))

    ensure_venv_or_exit(options.system_ok)
    ensure_git_clean_or_exit(root.parent, options.allow_dirty)

    lock_path = root.with_name(f".{root.name}.reqsync.lock")
    with advisory_lock(lock_path, options.lock_timeout_sec):
        if not options.no_upgrade:
            logging.info("Upgrading environment via pip (may take a while)...")
            code, _output = run_pip_upgrade(str(root), timeout_sec=options.pip_timeout_sec, extra_args=options.pip_args)
            if code != 0:
                raise PipUpgradeFailedError()

            if hasattr(get_installed_versions, "cache_clear"):
                get_installed_versions.cache_clear()

        installed = get_installed_versions()
        resolved_files = _resolve_files(root, follow=options.follow_includes)

        text_by_path: dict[Path, str] = {}
        bom_by_path: dict[Path, bool] = {}
        role_by_path: dict[Path, FileRole] = {}

        for resolved in resolved_files:
            text, _newline, bom = read_text_preserve(resolved.path)
            guard_hashes(text.splitlines(), allow_hashes=options.allow_hashes)
            text_by_path[resolved.path] = text
            bom_by_path[resolved.path] = bom
            role_by_path[resolved.path] = resolved.role

        writable_positions: set[tuple[Path, int]] | None = None
        if options.last_wins:
            writable_positions = _collect_last_occurrence_positions(text_by_path, resolved_files)

        cap_strategy = CapStrategy(default="next-major")
        file_results: list[FileChange] = []

        for resolved in resolved_files:
            original_text = text_by_path[resolved.path]
            role = role_by_path[resolved.path]

            if role == "constraint" and not options.update_constraints:
                file_results.append(
                    FileChange(file=resolved.path, role=role, original_text=original_text, new_text=original_text)
                )
                continue

            new_text, changes = _rewrite_text(
                path=resolved.path,
                text=original_text,
                installed=installed,
                options=options,
                cap=cap_strategy,
                writable_positions=writable_positions,
            )
            file_results.append(
                FileChange(
                    file=resolved.path,
                    role=role,
                    original_text=original_text,
                    new_text=new_text,
                    changes=changes,
                )
            )

        changed = any(result.original_text != result.new_text for result in file_results)

        if options.check:
            diff = report_mod.make_diff(file_results) if changed and (options.show_diff or options.dry_run) else None
            return Result(changed=changed, files=file_results, diff=diff)

        if options.dry_run:
            diff = report_mod.make_diff(file_results) if changed and options.show_diff else None
            return Result(changed=changed, files=file_results, diff=diff)

        backup_paths: list[Path] = []
        written_pairs: list[tuple[Path, Path]] = []
        if changed:
            for file_result in file_results:
                if file_result.original_text == file_result.new_text:
                    continue

                backup = backup_file(
                    file_result.file,
                    options.backup_suffix,
                    options.timestamped_backups,
                    options.backup_keep_last,
                )
                backup_paths.append(backup)

                try:
                    write_text_preserve(file_result.file, file_result.new_text, bom=bom_by_path[file_result.file])
                    written_pairs.append((file_result.file, backup))
                except Exception as exc:
                    _restore_backups([*written_pairs, (file_result.file, backup)])
                    raise WriteRollbackError(str(exc)) from exc

        diff = report_mod.make_diff(file_results) if changed and options.show_diff else None
        return Result(changed=changed, files=file_results, diff=diff, backup_paths=backup_paths)


# --- Back-compat test shims ---------------------------------------------------
# Tests and external callers may monkeypatch these names directly on reqsync.core.
get_installed_versions = env_mod.get_installed_versions
ensure_git_clean_or_exit = env_mod.ensure_git_clean_or_exit
ensure_venv_or_exit = env_mod.ensure_venv_or_exit
is_git_dirty = env_mod.is_git_dirty
is_venv_active = env_mod.is_venv_active
run_pip_upgrade = env_mod.run_pip_upgrade


__all__ = ["sync"]
