# ./examples/api_minimal.py
"""Minimal reqsync API usage example.

Run with: `python examples/api_minimal.py`
Inputs: local requirements file, installed environment packages.
Outputs: prints changed flag and optional diff preview; performs no writes.
"""

from __future__ import annotations

from pathlib import Path

from reqsync._types import Options
from reqsync.core import sync


def main() -> None:
    options = Options(
        path=Path("requirements.txt"),
        follow_includes=True,
        policy="lower-bound",
        dry_run=True,
        show_diff=True,
        no_upgrade=True,
    )
    result = sync(options)
    print("Changed:", result.changed)
    if result.diff:
        print(result.diff)


if __name__ == "__main__":
    main()
