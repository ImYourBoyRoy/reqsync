# ./tests/test_includes.py
"""Include and constraint graph behavior tests.

Confirms recursive include traversal works and constraint-linked files are skipped
unless explicitly enabled for updates.
"""

from __future__ import annotations

from pathlib import Path

from reqsync import core as core_mod
from reqsync._types import Options
from reqsync.core import sync


def test_follow_includes_and_skip_constraints(tmp_path: Path, monkeypatch) -> None:
    base = tmp_path / "base.txt"
    other = tmp_path / "other.txt"
    constraints = tmp_path / "constraints.txt"

    base.write_text("-r other.txt\n-c constraints.txt\npydantic\n", encoding="utf-8")
    other.write_text("pandas\n", encoding="utf-8")
    constraints_original = "pandas<2.0\n"
    constraints.write_text(constraints_original, encoding="utf-8")

    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "ensure_git_clean_or_exit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(core_mod, "run_pip_upgrade", lambda *_args, **_kwargs: (0, "skipped"))
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"pydantic": "2.7.0", "pandas": "2.2.2"})

    result = sync(
        Options(
            path=base,
            follow_includes=True,
            update_constraints=False,
            system_ok=True,
            no_upgrade=True,
            show_diff=True,
        )
    )

    other_result = next(item for item in result.files if item.file.name == "other.txt")
    base_result = next(item for item in result.files if item.file.name == "base.txt")
    constraints_result = next(item for item in result.files if item.file.name == "constraints.txt")

    assert "pandas>=2.2.2" in other_result.new_text
    assert "pydantic>=2.7.0" in base_result.new_text
    assert constraints_result.role == "constraint"
    assert constraints_result.new_text.replace("\r\n", "\n") == constraints_original
    assert constraints.read_text(encoding="utf-8").replace("\r\n", "\n") == constraints_original
