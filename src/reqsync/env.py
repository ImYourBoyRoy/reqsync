# ./src/reqsync/env.py
"""Environment and subprocess helpers for reqsync runtime decisions.

This module validates safety preconditions (virtualenv and git dirtiness), runs
pip upgrades with an allowlisted argument filter, and inspects installed package
versions for rewrite decisions.
"""

from __future__ import annotations

import json
import logging
import shlex
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from packaging.utils import canonicalize_name

from .errors import DirtyRepoBlockedError, VenvBlockedError

_ALLOWED_PIP_FLAGS: dict[str, bool] = {
    "--index-url": True,
    "--extra-index-url": True,
    "--trusted-host": True,
    "--find-links": True,
    "--proxy": True,
    "--retries": True,
    "--timeout": True,
    "--constraint": True,
    "-c": True,
    "--requirement": True,
    "-r": True,
    "--no-deps": False,
}


def is_venv_active() -> bool:
    """Return True when running inside virtualenv/venv."""

    return hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)


def ensure_venv_or_exit(system_ok: bool) -> None:
    """Enforce the default virtualenv safety guard."""

    if not system_ok and not is_venv_active():
        raise VenvBlockedError()


def is_git_dirty(repo_root: Path) -> bool:
    """Return True when the provided repo has tracked or untracked changes."""

    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return False
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def ensure_git_clean_or_exit(repo_root: Path, allow_dirty: bool) -> None:
    """Optionally block writes when the repository has local changes."""

    if not allow_dirty and is_git_dirty(repo_root):
        raise DirtyRepoBlockedError()


def _allowlisted_pip_args(extra_args: str) -> list[str]:
    """Filter arbitrary pip args down to a conservative allowlist."""

    if not extra_args.strip():
        return []

    tokens = shlex.split(extra_args)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        option, eq, _value = token.partition("=")

        expects_value = _ALLOWED_PIP_FLAGS.get(option)
        if expects_value is None:
            if option.startswith("-") and not eq and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                i += 1
            i += 1
            continue

        out.append(token)
        if expects_value and not eq and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            out.append(tokens[i + 1])
            i += 1

        i += 1

    return out


def run_pip_upgrade(requirements_path: str, timeout_sec: int, extra_args: str) -> tuple[int, str]:
    """Run pip install upgrade using the current interpreter."""

    cmd = [sys.executable, "-m", "pip", "install", "-U", "-r", requirements_path]
    extras = _allowlisted_pip_args(extra_args)
    if extras:
        cmd.extend(extras)

    logging.info("Running: %s", " ".join(shlex.quote(c) for c in cmd))
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    logging.info("pip output:\n%s", proc.stdout)
    return proc.returncode, proc.stdout


@lru_cache(maxsize=1)
def get_installed_versions() -> dict[str, str]:
    """Map canonicalized project name -> installed version from the current env."""

    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            text=True,
        )
        data = json.loads(out)
        versions: dict[str, str] = {}
        for entry in data:
            name = entry.get("name")
            version = entry.get("version")
            if not name or not version:
                continue
            versions[canonicalize_name(str(name))] = str(version)
        return versions
    except Exception:
        try:
            import importlib.metadata as importlib_metadata
        except Exception:  # pragma: no cover - fallback for rare legacy setups
            import importlib_metadata as importlib_metadata  # type: ignore

        fallback: dict[str, str] = {}
        for dist in importlib_metadata.distributions():
            metadata = getattr(dist, "metadata", None)
            raw_name: str | None = None

            if metadata is not None and hasattr(metadata, "get"):
                try:
                    raw_name = metadata.get("Name")
                except Exception:
                    raw_name = None

            if not raw_name:
                raw_name = getattr(dist, "name", None) or getattr(dist, "project_name", None)

            if not raw_name:
                continue

            fallback[canonicalize_name(raw_name)] = dist.version

        return fallback


__all__ = [
    "ensure_git_clean_or_exit",
    "ensure_venv_or_exit",
    "get_installed_versions",
    "is_git_dirty",
    "is_venv_active",
    "run_pip_upgrade",
]
