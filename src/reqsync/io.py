# ./src/reqsync/io.py
"""File I/O helpers for safe requirements rewriting.

This module preserves file encoding/newlines, performs atomic writes, creates
backups, and optionally acquires a cross-process advisory lock.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import LockAcquireTimeoutError

portalocker: Any
try:
    import portalocker
except Exception:  # pragma: no cover - optional runtime dependency fallback
    portalocker = None


def read_text_preserve(path: Path) -> tuple[str, str, bool]:
    """Return decoded text, dominant newline style, and BOM presence."""

    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace")
    if "\r\n" in text:
        newline = "\r\n"
    elif "\r" in text:
        newline = "\r"
    else:
        newline = "\n"
    return text, newline, has_bom


def write_text_preserve(path: Path, content: str, bom: bool) -> None:
    """Write UTF-8 content while preserving optional BOM behavior."""

    payload = content.encode("utf-8")
    if bom:
        payload = b"\xef\xbb\xbf" + payload
    write_atomic_bytes(path, payload)


def write_atomic_bytes(path: Path, data: bytes) -> None:
    """Atomically replace file content with a temp-file swap."""

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="reqsync-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "wb") as stream:
            stream.write(data)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def _prune_old_backups(path: Path, suffix: str, keep_last: int) -> None:
    """Keep only the most recent timestamped backups for one file."""

    if keep_last <= 0:
        return

    pattern = f"{path.name}{suffix}.*"
    backups = sorted(path.parent.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    for stale in backups[keep_last:]:
        try:
            stale.unlink()
        except OSError:
            logging.warning("Unable to prune old backup: %s", stale)


def _build_unique_timestamped_backup_path(path: Path, suffix: str) -> Path:
    """Return a collision-safe timestamped backup path for one source file."""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    base_name = f"{path.name}{suffix}.{stamp}"
    backup = path.with_name(base_name)

    counter = 1
    while backup.exists():
        backup = path.with_name(f"{base_name}-{counter:02d}")
        counter += 1

    return backup


def backup_file(path: Path, suffix: str, timestamped: bool, keep_last: int) -> Path:
    """Create a backup copy and return its path."""

    if not path.exists():
        raise FileNotFoundError(f"Cannot back up missing file: {path}")

    if timestamped:
        backup = _build_unique_timestamped_backup_path(path=path, suffix=suffix)
    else:
        backup = path.with_name(f"{path.name}{suffix}")

    shutil.copy2(path, backup)
    if timestamped:
        _prune_old_backups(path=path, suffix=suffix, keep_last=keep_last)
    logging.info("Backed up to: %s", backup)
    return backup


@contextmanager
def advisory_lock(lock_path: Path, timeout_sec: int):
    """Acquire an advisory file lock when portalocker is available."""

    if portalocker is None:
        yield
        return

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_error = getattr(getattr(portalocker, "exceptions", None), "LockException", Exception)

    try:
        with portalocker.Lock(str(lock_path), mode="a+", timeout=timeout_sec):
            yield
    except lock_error as exc:  # pragma: no cover - backend-specific lock errors
        raise LockAcquireTimeoutError(str(lock_path), timeout_sec) from exc


__all__ = [
    "advisory_lock",
    "backup_file",
    "read_text_preserve",
    "write_atomic_bytes",
    "write_text_preserve",
]
