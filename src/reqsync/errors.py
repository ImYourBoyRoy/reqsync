# ./src/reqsync/errors.py
"""Custom exceptions carrying stable reqsync exit-code intent.

The core engine raises these typed errors so CLI and MCP layers can map failures
without brittle string parsing. Import for explicit error handling in automation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._types import ExitCode


@dataclass
class ReqsyncError(RuntimeError):
    """Base reqsync exception with a stable exit code."""

    message: str
    exit_code: ExitCode = ExitCode.GENERIC_ERROR

    def __str__(self) -> str:
        return self.message


class MissingRequirementsFileError(ReqsyncError):
    def __init__(self, path: str) -> None:
        super().__init__(f"Requirements file not found: {path}", ExitCode.MISSING_FILE)


class HashPinsPresentError(ReqsyncError):
    def __init__(self) -> None:
        super().__init__(
            "requirements contains --hash pins. Re-run with --allow-hashes to skip hashed lines.",
            ExitCode.HASHES_PRESENT,
        )


class PipUpgradeFailedError(ReqsyncError):
    def __init__(self) -> None:
        super().__init__("pip install -U failed. See logs.", ExitCode.PIP_FAILED)


class VenvBlockedError(ReqsyncError):
    def __init__(self) -> None:
        super().__init__(
            "Refusing to run outside a virtualenv. Re-run with --system-ok if you really know what you're doing.",
            ExitCode.SYSTEM_PYTHON_BLOCKED,
        )


class DirtyRepoBlockedError(ReqsyncError):
    def __init__(self) -> None:
        super().__init__(
            "Repository has uncommitted changes. Re-run with --allow-dirty to override.",
            ExitCode.DIRTY_REPO_BLOCKED,
        )


class LockAcquireTimeoutError(ReqsyncError):
    def __init__(self, lock_path: str, timeout_sec: int) -> None:
        super().__init__(
            f"Unable to acquire reqsync lock at {lock_path} within {timeout_sec}s.",
            ExitCode.LOCK_TIMEOUT,
        )


class WriteRollbackError(ReqsyncError):
    def __init__(self, detail: str) -> None:
        super().__init__(f"Write failed and backups restored: {detail}", ExitCode.WRITE_FAILED_ROLLED_BACK)


__all__ = [
    "DirtyRepoBlockedError",
    "HashPinsPresentError",
    "LockAcquireTimeoutError",
    "MissingRequirementsFileError",
    "PipUpgradeFailedError",
    "ReqsyncError",
    "VenvBlockedError",
    "WriteRollbackError",
]
