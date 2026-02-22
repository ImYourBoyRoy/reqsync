# ./tests/conftest.py
"""Pytest session setup for reqsync.

Ensures the local `src/` package is importable during test runs and scrubs
`__pycache__` directories before collection so tests always execute fresh code.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _scrub_pycache(root: Path) -> None:
    for cache_dir in root.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

_scrub_pycache(PROJECT_ROOT)
