# ./tests/test_integration_basic.py
"""Core integration tests for write flow and idempotence.

Exercises backup creation, rewrite application, and subsequent no-op behavior on
already synchronized files.
"""

from __future__ import annotations

from reqsync import core as core_mod
from reqsync._types import Options
from reqsync.core import sync


def test_end_to_end_write_backup_and_idempotence(tmp_path, monkeypatch) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("requests\n# trailing comment\n", encoding="utf-8")

    core_mod.get_installed_versions.cache_clear()

    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "ensure_git_clean_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "run_pip_upgrade", lambda *_args, **_kwargs: (0, "skipped"))
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"requests": "2.32.3"})

    options = Options(path=req, system_ok=True, no_upgrade=True, show_diff=True)

    first = sync(options)
    assert first.changed
    assert any(path.name.startswith("requirements.txt.bak") for path in first.backup_paths)
    assert "requests>=2.32.3" in req.read_text(encoding="utf-8")

    second = sync(options)
    assert not second.changed
