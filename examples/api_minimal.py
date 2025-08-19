# examples/api_minimal.py

from pathlib import Path
from reqsync._types import Options
from reqsync.core import sync


def main() -> None:
    opts = Options(
        path=Path("requirements.txt"),
        follow_includes=True,
        policy="lower-bound",
        dry_run=True,
        show_diff=True,
        no_upgrade=True,  # read-only check against current env
    )
    result = sync(opts)
    print("Changed:", result.changed)
    if result.diff:
        print(result.diff)


if __name__ == "__main__":
    main()
