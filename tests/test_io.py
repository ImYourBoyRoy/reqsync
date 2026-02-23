# ./tests/test_io.py
"""Encoding and newline preservation tests.

Ensures reqsync keeps UTF-8 BOM and original line-ending style during rewrites
and direct read/write round-trips.
"""

from __future__ import annotations

from reqsync import core as core_mod
from reqsync import io as io_mod
from reqsync._types import Options
from reqsync.core import sync
from reqsync.io import backup_file, read_text_preserve, write_text_preserve


def test_preserve_bom_and_newlines_on_write(tmp_path, monkeypatch) -> None:
    target = tmp_path / "requirements.txt"
    raw = "\ufeffpandas\n".encode()
    target.write_bytes(raw.replace(b"\n", b"\r\n"))

    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "ensure_git_clean_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "run_pip_upgrade", lambda *_args, **_kwargs: (0, "skipped"))
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"pandas": "2.2.2"})

    result = sync(Options(path=target, system_ok=True, no_upgrade=True))
    assert result.changed

    data = target.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")


def test_read_write_roundtrip_preserves_format(tmp_path) -> None:
    path = tmp_path / "x.txt"
    path.write_bytes(b"\xef\xbb\xbfline1\r\nline2\r\n")

    text, newline, bom = read_text_preserve(path)
    assert newline == "\r\n" and bom is True

    write_text_preserve(path, text, bom)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_timestamped_backup_pruning_keeps_recent_files(tmp_path) -> None:
    target = tmp_path / "requirements.txt"
    target.write_text("requests>=2.0\n", encoding="utf-8")

    for i in range(6):
        target.write_text(f"requests>={i}.0\n", encoding="utf-8")
        backup_file(target, suffix=".bak", timestamped=True, keep_last=3)

    backups = sorted(tmp_path.glob("requirements.txt.bak.*"))
    assert len(backups) == 3


def test_timestamped_backup_pruning_can_be_disabled(tmp_path) -> None:
    target = tmp_path / "requirements.txt"
    target.write_text("requests>=2.0\n", encoding="utf-8")

    for i in range(4):
        target.write_text(f"requests>={i}.0\n", encoding="utf-8")
        backup_file(target, suffix=".bak", timestamped=True, keep_last=0)

    backups = sorted(tmp_path.glob("requirements.txt.bak.*"))
    assert len(backups) == 4


def test_timestamped_backup_naming_avoids_collisions(tmp_path, monkeypatch) -> None:
    target = tmp_path / "requirements.txt"
    target.write_text("requests>=2.0\n", encoding="utf-8")

    class _FixedNow:
        @staticmethod
        def strftime(_fmt: str) -> str:
            return "20260223-000000-000000"

    class _FixedDateTime:
        @staticmethod
        def now() -> _FixedNow:
            return _FixedNow()

    monkeypatch.setattr(io_mod, "datetime", _FixedDateTime)

    for i in range(3):
        target.write_text(f"requests>={i}.0\n", encoding="utf-8")
        backup_file(target, suffix=".bak", timestamped=True, keep_last=0)

    backups = sorted(tmp_path.glob("requirements.txt.bak.*"))
    assert len(backups) == 3
    assert len({backup.name for backup in backups}) == 3
