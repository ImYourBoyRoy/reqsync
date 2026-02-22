# ./src/reqsync/_logging.py
"""Logging setup utilities for reqsync CLI and programmatic runners.

Configures concise console logs by default, optional debug verbosity, and an
optional structured file sink for troubleshooting long-running sync jobs.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(verbosity: int, quiet: bool, log_file: Path | None) -> None:
    """Configure root logging based on CLI verbosity flags."""

    if quiet:
        level = logging.WARNING
    elif verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        root.addHandler(file_handler)


__all__ = ["setup_logging"]
