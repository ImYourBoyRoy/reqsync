# ./src/reqsync/api.py
"""Programmatic integration helpers for local AI tools and automation.

Use this module when embedding reqsync into agents, MCP tools, or CI wrappers.
It converts loose dictionaries into strongly typed options and returns JSON-safe
result payloads without requiring subprocess parsing.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ._types import JsonResult, Options
from .config import merge_options
from .core import sync
from .report import result_to_json


def options_from_mapping(payload: Mapping[str, Any], *, default_path: Path | None = None) -> Options:
    """Create validated Options from arbitrary mapping input."""

    base = Options(path=default_path or Path("requirements.txt"))
    return merge_options(base, dict(payload))


def run_sync_payload(payload: Mapping[str, Any], *, default_path: Path | None = None) -> JsonResult:
    """Execute reqsync using a dictionary payload and return JSON-safe output."""

    options = options_from_mapping(payload, default_path=default_path)
    result = sync(options)
    return result_to_json(result)


__all__ = ["options_from_mapping", "run_sync_payload"]
