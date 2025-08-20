# src/reqsync/core.py

from __future__ import annotations

import fnmatch
import logging
import shutil
from pathlib import Path

from packaging.utils import canonicalize_name

from . import env as env_mod
from . import report as report_mod
from ._types import Change, FileChange, Options, Result
from .io import backup_file, read_text_preserve, write_text_preserve
from .parse import find_constraints, find_includes, guard_hashes, parse_line
from .policy import CapStrategy, apply_policy


def _match(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def _resolve_includes(root: Path, follow: bool) -> list[Path]:
    files: list[Path] = [root]
    if not follow or not root.exists():
        return files
    seen = {root.resolve()}
    queue = [root]
    while queue:
        cur = queue.pop()
        text, _, _ = read_text_preserve(cur)
        for rel in find_includes(text.splitlines()):
            inc = (cur.parent / rel).resolve()
            if inc.exists() and inc not in seen:
                seen.add(inc)
                files.append(inc)
                queue.append(inc)
    return files


def _should_skip_pkg(pkg_name: str, only: list[str], exclude: list[str]) -> bool:
    if only and not _match(pkg_name, only):
        return True
    if exclude and _match(pkg_name, exclude):
        return True
    return False


def _rewrite_text(
    path: Path,
    text: str,
    installed: dict[str, str],
    options: Options,
    cap: CapStrategy | None,
) -> tuple[str, list[Change]]:
    lines = text.splitlines(keepends=True)
    out_lines: list[str] = []
    changes: list[Change] = []
    for line in lines:
        parsed = parse_line(line)
        kind = parsed.kind

        if kind != "package":
            out_lines.append(line)
            continue

        req = parsed.requirement
        if not req:
            out_lines.append(line)
            continue

        base = canonicalize_name(req.name)
        if _should_skip_pkg(base, list(options.only), list(options.exclude)):
            out_lines.append(line)
            continue

        if base not in installed:
            logging.warning("Not installed after upgrade: %s (kept)", req.name)
            out_lines.append(line)
            continue

        new_content = apply_policy(
            req=req,
            installed_version=installed[base],
            policy=options.policy,
            allow_prerelease=options.allow_prerelease,
            keep_local=options.keep_local,
            cap_strategy=cap,
        )

        if new_content is None:
            out_lines.append(line)
            continue

        # FIX: Use the original end-of-line characters instead of hardcoding "\n"
        new_line = new_content + parsed.comment + parsed.eol
        if new_line != line:
            changes.append(
                Change(
                    package=req.name,
                    installed_version=installed[base],
                    old_line=line,
                    new_line=new_line,
                    file=path,
                )
            )
            out_lines.append(new_line)
        else:
            out_lines.append(line)

    return "".join(out_lines), changes


def sync(options: Options) -> Result:
    """
    Orchestrate upgrade and rewrite.
    Raises RuntimeError with clear messages for fatal conditions.
    """
    logging.info("Starting reqsync")
    ensure_venv_or_exit(options.system_ok)
    root = options.path
    logging.info("Reading %s", root)

    root = options.path
    if not root.exists():
        raise FileNotFoundError(str(root))

    # The file_lock context manager has been removed.
    # The logic is now at the top level of the function.
    logging.info("Reading and parsing requirements files...")
    root_text, _, _ = read_text_preserve(root)
    try:
        guard_hashes(root_text.splitlines(), allow_hashes=options.allow_hashes)
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    if not options.no_upgrade:
        logging.info("Upgrading environment via pip (may take a while)...")
        code, _ = run_pip_upgrade(str(root), timeout_sec=options.pip_timeout_sec, extra_args=options.pip_args)
        if code != 0:
            raise RuntimeError("pip install -U failed. See logs.")
        logging.info("Environment upgrade complete.")

    logging.info("Inspecting installed packages...")
    installed = get_installed_versions()

    files = _resolve_includes(root, follow=options.follow_includes)
    logging.info("Resolved %d file(s) (follow_includes=%s)", len(files), options.follow_includes)
    file_results: list[FileChange] = []
    aggregate_changes: list[Change] = []
    cap = CapStrategy(default="next-major")
    file_properties: dict[Path, tuple[bool]] = {}

    for f in files:
        text, _, bom = read_text_preserve(f)
        file_properties[f] = (bom,)
        constraints = find_constraints(text.splitlines())
        if constraints and not options.update_constraints and f != root:
            file_results.append(FileChange(file=f, original_text=text, new_text=text, changes=[]))
            continue

        new_text, changes = _rewrite_text(f, text, installed, options, cap)
        if changes:
            aggregate_changes.extend(changes)
        file_results.append(FileChange(file=f, original_text=text, new_text=new_text, changes=changes))

    changed = any(fr.original_text != fr.new_text for fr in file_results)

    if options.check:
        diff = report_mod.make_diff(file_results) if changed and (options.show_diff or options.dry_run) else None
        logging.info("Check complete. Changes detected: %s", changed)
        return Result(changed=True, files=file_results, diff=diff)

    if options.dry_run:
        diff = report_mod.make_diff(file_results) if changed and options.show_diff else None
        logging.info("Dry run complete. Changes detected: %s", changed)
        return Result(changed=changed, files=file_results, diff=diff)

    backups: list[Path] = []
    if changed:
        logging.info("Writing %d change(s) to disk...", len(aggregate_changes))
        for fr in file_results:
            if fr.original_text == fr.new_text:
                continue
            backup = backup_file(fr.file, options.backup_suffix, options.timestamped_backups)
            backups.append(backup)
            try:
                bom = file_properties.get(fr.file, (False,))[0]
                write_text_preserve(fr.file, fr.new_text, bom)
            except Exception as e:
                for b in backups:
                    orig = b
                    target = Path(str(b).rsplit(options.backup_suffix, 1)[0])
                    try:
                        shutil.copy2(orig, target)
                    except Exception:
                        pass
                raise RuntimeError(f"Write failed and backups restored: {e}") from e

    diff = report_mod.make_diff(file_results) if changed and options.show_diff else None
    logging.info("Reqsync process finished.")
    return Result(changed=changed, files=file_results, diff=diff, backup_paths=backups)


# --- Back-compat test shims ---------------------------------------------------
# Tests (and possibly external callers) patch these names on the core module.
# Keep them as aliases to the env module so monkeypatching still works.
get_installed_versions = env_mod.get_installed_versions
ensure_venv_or_exit = env_mod.ensure_venv_or_exit
run_pip_upgrade = env_mod.run_pip_upgrade
