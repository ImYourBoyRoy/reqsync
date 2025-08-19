# src/reqsync/config.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ._types import Options

try:
    import tomllib as toml
except Exception:
    try:
        import tomli as toml  # type: ignore[no-redef]
    except Exception:
        toml = None  # type: ignore[assignment]


def _load_toml(path: Path) -> dict[str, Any]:
    if not toml:
        return {}
    try:
        with open(path, "rb") as f:
            data = toml.load(f)
            # toml.load returns Any; ensure we hand back a dict
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_project_config(start_dir: Path) -> dict[str, Any]:
    cfg: dict[str, Any] = {}

    # reqsync.toml
    rs = start_dir / "reqsync.toml"
    if rs.exists():
        cfg.update(_load_toml(rs))

    # pyproject [tool.reqsync]
    pyproj = start_dir / "pyproject.toml"
    if pyproj.exists():
        data = _load_toml(pyproj)
        tool = data.get("tool") or {}
        section = tool.get("reqsync") or {}
        if isinstance(section, dict):
            cfg.update(section)

    # JSON fallback
    rj = start_dir / "reqsync.json"
    if rj.exists():
        try:
            cfg.update(json.loads(rj.read_text(encoding="utf-8")))
        except Exception as e:
            logging.warning("Failed to parse reqsync.json: %s", e)

    return cfg


def _to_path(v: Any) -> Path | None:
    if v in (None, "", "."):
        return None
    try:
        return Path(str(v))
    except Exception:
        return None


def _to_tuple(v: Any) -> tuple[str, ...]:
    if v is None:
        return ()
    if isinstance(v, list | tuple):
        return tuple(str(x).strip() for x in v if str(x).strip())
    if isinstance(v, str):
        return tuple(p for p in (s.strip() for s in v.split(",")) if p)
    return ()


def merge_options(base: Options, overrides: dict[str, Any]) -> Options:
    return Options(
        path=_to_path(overrides.get("path")) or base.path,
        follow_includes=overrides.get("follow_includes", base.follow_includes),
        update_constraints=overrides.get("update_constraints", base.update_constraints),
        policy=overrides.get("policy", base.policy),
        allow_prerelease=overrides.get("allow_prerelease", base.allow_prerelease),
        keep_local=overrides.get("keep_local", base.keep_local),
        no_upgrade=overrides.get("no_upgrade", base.no_upgrade),
        pip_timeout_sec=int(overrides.get("pip_timeout_sec", base.pip_timeout_sec)),
        pip_args=str(overrides.get("pip_args", base.pip_args)),
        only=_to_tuple(overrides.get("only")) or base.only,
        exclude=_to_tuple(overrides.get("exclude")) or base.exclude,
        check=overrides.get("check", base.check),
        dry_run=overrides.get("dry_run", base.dry_run),
        show_diff=overrides.get("show_diff", base.show_diff),
        json_report=_to_path(overrides.get("json_report")) or base.json_report,
        backup_suffix=str(overrides.get("backup_suffix", base.backup_suffix)),
        timestamped_backups=overrides.get("timestamped_backups", base.timestamped_backups),
        log_file=_to_path(overrides.get("log_file")) or base.log_file,
        verbosity=int(overrides.get("verbosity", base.verbosity)),
        quiet=overrides.get("quiet", base.quiet),
        system_ok=overrides.get("system_ok", base.system_ok),
        allow_hashes=overrides.get("allow_hashes", base.allow_hashes),
        allow_dirty=overrides.get("allow_dirty", base.allow_dirty),
        last_wins=overrides.get("last_wins", base.last_wins),
    )
