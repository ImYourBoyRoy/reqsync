# tests/test_integration_basic.py

from reqsync import core as core_mod
from reqsync._types import Options
from reqsync.core import sync


def test_end_to_end_write_backup_and_idempotence(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("requests\n# trailing comment\n", encoding="utf-8")

    # Clear the cache using the module imported at the top of the file
    core_mod.get_installed_versions.cache_clear()

    # Now, the patch will work as expected.
    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda *a, **k: None)
    monkeypatch.setattr(core_mod, "run_pip_upgrade", lambda *a, **k: (0, "skipped"))
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"requests": "2.32.3"})

    # First run: should write and create backup
    opts = Options(path=req, system_ok=True, no_upgrade=True, show_diff=True)
    res1 = sync(opts)
    assert res1.changed
    assert any(b.name.startswith("requirements.txt.bak") for b in res1.backup_paths)
    assert "requests>=2.32.3" in req.read_text(encoding="utf-8")

    # Second run: idempotent, no changes
    res2 = sync(opts)
    assert not res2.changed