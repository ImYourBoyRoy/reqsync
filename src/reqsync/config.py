# ./src/reqsync/config.py
"""Configuration loading and option-merging for reqsync.

Supports optional project config from reqsync.toml, pyproject.toml, and
reqsync.json. CLI values remain highest priority, followed by config values,
then built-in dataclass defaults.
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any, cast

from ._types import Options, Policy


def _import_toml_like() -> Any:
    """Load tomllib (3.11+) or tomli fallback when available."""

    try:
        return importlib.import_module("tomllib")
    except Exception:
        try:
            return importlib.import_module("tomli")
        except Exception:
            return None


toml = _import_toml_like()


def _load_toml(path: Path) -> dict[str, Any]:
    if not toml:
        return {}
    try:
        with path.open("rb") as stream:
            data = toml.load(stream)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_project_config(start_dir: Path) -> dict[str, Any]:
    """Load merged reqsync config from known project files."""

    config: dict[str, Any] = {}

    reqsync_toml = start_dir / "reqsync.toml"
    if reqsync_toml.exists():
        config.update(_load_toml(reqsync_toml))

    pyproject = start_dir / "pyproject.toml"
    if pyproject.exists():
        data = _load_toml(pyproject)
        tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
        section = tool.get("reqsync") if isinstance(tool, dict) else {}
        if isinstance(section, dict):
            config.update(section)

    reqsync_json = start_dir / "reqsync.json"
    if reqsync_json.exists():
        try:
            payload = json.loads(reqsync_json.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                config.update(payload)
        except Exception as exc:
            logging.warning("Failed to parse reqsync.json: %s", exc)

    return config


def _to_path(value: Any) -> Path | None:
    if value in (None, "", "."):
        return None
    try:
        return Path(str(value))
    except Exception:
        return None


def _to_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return tuple(item for item in (part.strip() for part in value.split(",")) if item)
    return ()


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_policy(value: Any, default: Policy) -> Policy:
    if value is None:
        return default

    raw = getattr(value, "value", value)
    allowed: set[str] = {"lower-bound", "floor-only", "floor-and-cap", "update-in-place"}
    if isinstance(raw, str) and raw in allowed:
        return cast(Policy, raw)

    return default


def merge_options(base: Options, overrides: dict[str, Any]) -> Options:
    """Return a new options object after applying overrides to base values."""

    config_path = _to_path(overrides.get("path"))
    if config_path and base.path == Path("requirements.txt"):
        effective_path = config_path
    else:
        effective_path = base.path

    return Options(
        path=effective_path,
        follow_includes=_to_bool(overrides.get("follow_includes"), base.follow_includes),
        update_constraints=_to_bool(overrides.get("update_constraints"), base.update_constraints),
        policy=_to_policy(overrides.get("policy"), base.policy),
        allow_prerelease=_to_bool(overrides.get("allow_prerelease"), base.allow_prerelease),
        keep_local=_to_bool(overrides.get("keep_local"), base.keep_local),
        no_upgrade=_to_bool(overrides.get("no_upgrade"), base.no_upgrade),
        pip_timeout_sec=_to_int(overrides.get("pip_timeout_sec"), base.pip_timeout_sec),
        pip_args=str(overrides.get("pip_args", base.pip_args)),
        only=_to_tuple(overrides.get("only")) or base.only,
        exclude=_to_tuple(overrides.get("exclude")) or base.exclude,
        check=_to_bool(overrides.get("check"), base.check),
        dry_run=_to_bool(overrides.get("dry_run"), base.dry_run),
        show_diff=_to_bool(overrides.get("show_diff"), base.show_diff),
        json_report=_to_path(overrides.get("json_report")) or base.json_report,
        backup_suffix=str(overrides.get("backup_suffix", base.backup_suffix)),
        timestamped_backups=_to_bool(overrides.get("timestamped_backups"), base.timestamped_backups),
        backup_keep_last=max(0, _to_int(overrides.get("backup_keep_last"), base.backup_keep_last)),
        lock_timeout_sec=_to_int(overrides.get("lock_timeout_sec"), base.lock_timeout_sec),
        log_file=_to_path(overrides.get("log_file")) or base.log_file,
        verbosity=_to_int(overrides.get("verbosity"), base.verbosity),
        quiet=_to_bool(overrides.get("quiet"), base.quiet),
        system_ok=_to_bool(overrides.get("system_ok"), base.system_ok),
        allow_hashes=_to_bool(overrides.get("allow_hashes"), base.allow_hashes),
        allow_dirty=_to_bool(overrides.get("allow_dirty"), base.allow_dirty),
        last_wins=_to_bool(overrides.get("last_wins"), base.last_wins),
    )


__all__ = ["load_project_config", "merge_options"]
