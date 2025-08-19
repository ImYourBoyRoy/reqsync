# src/reqsync/_logging.py

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(verbosity: int, quiet: bool, log_file: Path | None) -> None:
    """
    Configure root logger with console and optional file sink.
    Verbosity: 0 WARNING, 1 INFO, 2+ DEBUG. Quiet forces WARNING.
    """
    if quiet:
        level = logging.WARNING
    elif verbosity >= 2:
        level = logging.DEBUG
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level)

    # FIX: Use a simpler format for the console to make status messages clean.
    console_formatter = logging.Formatter("%(message)s")
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(level)
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)  # Log everything to the file
        fh.setFormatter(file_formatter)
        logger.addHandler(fh)
