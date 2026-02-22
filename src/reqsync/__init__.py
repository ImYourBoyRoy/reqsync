# ./src/reqsync/__init__.py
"""Public reqsync package API.

Provides stable exports for CLI users, Python integrations, and AI tooling.
Import `sync` for direct orchestration or `run_sync_payload` for JSON-style
automation flows.
"""

from __future__ import annotations

from .api import options_from_mapping, run_sync_payload
from .core import sync

__all__ = ["__version__", "options_from_mapping", "run_sync_payload", "sync"]

try:
    from importlib.metadata import PackageNotFoundError, version
except Exception:  # pragma: no cover - optional fallback for rare environments
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

try:
    __version__ = version("reqsync")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
