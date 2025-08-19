# src/reqsync/env.py
from __future__ import annotations

import json
import logging
import shlex
import subprocess
import sys
from functools import lru_cache

from packaging.utils import canonicalize_name

_ALLOWED_PIP_FLAGS = {
    "--index-url",
    "--extra-index-url",
    "--trusted-host",
    "--find-links",
    "--no-deps",
}



def is_venv_active() -> bool:
    # True when inside virtualenv or venv
    return hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

def ensure_venv_or_exit(system_ok: bool) -> None:
    if not system_ok and not is_venv_active():
        raise RuntimeError(
            "Refusing to run outside a virtualenv. Re-run with --system-ok if you really know what you're doing."
        )

def _allowlisted_pip_args(extra_args: str) -> list[str]:
    if not extra_args.strip():
        return []
    tokens = shlex.split(extra_args)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        name, eq, val = t.partition("=")
        if name in _ALLOWED_PIP_FLAGS:
            if name in {"--index-url", "--extra-index-url", "--trusted-host", "--find-links"}:
                if eq:
                    out.append(t)  # --flag=value
                else:
                    out.append(t)  # --flag value
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        out.append(tokens[i + 1])
                        i += 1
            else:
                out.append(t)  # switches like --no-deps
        else:
            # drop unknown flag and its value if provided separately
            if not eq and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                i += 1
        i += 1
    return out

def run_pip_upgrade(requirements_path: str, timeout_sec: int, extra_args: str) -> tuple[int, str]:
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
    )
    logging.info("pip output:\n%s", proc.stdout)
    return proc.returncode, proc.stdout

@lru_cache(maxsize=1)
def get_installed_versions() -> dict[str, str]:
    """
    Map canonicalized project name -> version from current environment.
    """
    try:
        out = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            text=True,
        )
        data = json.loads(out)
        versions: dict[str, str] = {}
        for d in data:
            versions[canonicalize_name(d["name"])] = d["version"]
        return versions
    except Exception:
        # Fallback to importlib.metadata when pip list not available
        try:
            import importlib.metadata as importlib_metadata  # py3.8+
        except Exception:
            import importlib_metadata as importlib_metadata  # type: ignore

        versions_fallback: dict[str, str] = {}
        for dist in importlib_metadata.distributions():
            # dist.metadata can be None or an email.message.Message-like object.
            md = getattr(dist, "metadata", None)

            raw_name: str | None = None
            if md is not None and hasattr(md, "get"):
                try:
                    # email.message.Message.get returns str | None
                    raw_name = md.get("Name")
                except Exception:
                    raw_name = None

            # Some impls expose .name (or project_name). Use as fallback.
            if not raw_name:
                raw_name = getattr(dist, "name", None) or getattr(dist, "project_name", None)

            if not raw_name:
                # If we still don't have a name, skip this dist safely
                continue

            name = canonicalize_name(raw_name)
            versions_fallback[name] = dist.version

        return versions_fallback

