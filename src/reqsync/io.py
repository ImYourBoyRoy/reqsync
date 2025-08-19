# src/reqsync/io.py

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def read_text_preserve(path: Path) -> tuple[str, str, bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig", errors="replace")
    if "\r\n" in text:
        nl = "\r\n"
    elif "\r" in text:
        nl = "\r"
    else:
        nl = "\n"
    return text, nl, has_bom


def write_text_preserve(path: Path, content: str, bom: bool) -> None:
    b = content.encode("utf-8")
    if bom:
        b = b"\xef\xbb\xbf" + b
    write_atomic_bytes(path, b)


def write_atomic_bytes(path: Path, data: bytes) -> None:
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="reqsync-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise


def backup_file(path: Path, suffix: str, timestamped: bool) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Cannot back up missing file: {path}")
    if timestamped:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}{suffix}.{stamp}")
    else:
        backup = path.with_name(f"{path.name}{suffix}")
    shutil.copy2(path, backup)
    logging.info("Backed up to: %s", backup)
    return backup