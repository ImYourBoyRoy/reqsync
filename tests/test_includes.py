# tests/test_includes.py

from pathlib import Path

# Import the module where the functions are USED
from reqsync import core as core_mod
from reqsync._types import Options
from reqsync.core import sync


def test_follow_includes_and_skip_constraints(tmp_path: Path, monkeypatch):
    base = tmp_path / "base.txt"
    other = tmp_path / "other.txt"
    constraints = tmp_path / "constraints.txt"

    base.write_text("-r other.txt\n-c constraints.txt\npydantic\n", encoding="utf-8")
    other.write_text("pandas\n", encoding="utf-8")
    constraints_original = "pandas<2.0\n"
    constraints.write_text(constraints_original, encoding="utf-8")

    # Patch the functions in the 'core' module where they are used
    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda *a, **k: None)
    monkeypatch.setattr(core_mod, "run_pip_upgrade", lambda *a, **k: (0, "skipped"))
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"pydantic": "2.7.0", "pandas": "2.2.2"})

    opts = Options(
        path=base,
        follow_includes=True,
        update_constraints=False,  # constraints should not be modified
        system_ok=True,
        no_upgrade=True,
        show_diff=True,
    )
    result = sync(opts)

    # Find the FileChange object for the 'other.txt' file to make the assert more robust
    other_file_result = next((f for f in result.files if f.file.name == "other.txt"), None)
    assert other_file_result is not None, "Result for included file 'other.txt' not found"
    assert "pandas>=2.2.2" in other_file_result.new_text, "Included file should be rewritten"

    base_file_result = next((f for f in result.files if f.file.name == "base.txt"), None)
    assert base_file_result is not None, "Result for base file 'base.txt' not found"
    assert "pydantic>=2.7.0" in base_file_result.new_text, "Base file should be rewritten"

    # FIX: Verify that the constraint file on disk was not touched,
    # as it should not be part of the processed files.
    assert constraints.read_text(encoding="utf-8") == constraints_original, "Constraint file must not be modified"
    constraint_file_in_result = next((f for f in result.files if f.file.name == "constraints.txt"), None)
    assert constraint_file_in_result is None, "Constraint file should not be in the result set"
