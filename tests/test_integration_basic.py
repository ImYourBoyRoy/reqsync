# tests/test_integration_basic.py

from pathlib import Path
from reqsync._types import Options
from reqsync.core import sync
# FIX: Import the module where the functions are USED
from reqsync import core as core_mod

def test_end_to_end_write_backup_and_idempotence(tmp_path, monkeypatch):
    req = tmp_path / "requirements.txt"
    req.write_text("requests\n# trailing comment\n", encoding="utf-8")

    # FIX: Patch the functions in the 'core' module where they are used
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