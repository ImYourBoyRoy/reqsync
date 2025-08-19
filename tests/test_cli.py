# tests/test_cli.py

import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

# Import the module where the functions are USED
from reqsync import core as core_mod
from reqsync._types import ExitCode
from reqsync.cli import app

runner = CliRunner()


def write(p: Path, content: str) -> Path:
    """Helper to write dedented content to a file."""
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8", newline="\n")
    return p


def test_cli_missing_file_returns_clear_exit_code(tmp_path: Path):
    missing = tmp_path / "nope.txt"
    res = runner.invoke(app, ["--path", str(missing), "--system-ok", "--no-upgrade", "--no-use-config"])
    assert res.exit_code == ExitCode.MISSING_FILE, (
        f"Expected exit {ExitCode.MISSING_FILE}, got {res.exit_code}\nOUTPUT:\n{res.output}"
    )


def test_cli_refuses_hashed_requirements_with_helpful_message(tmp_path: Path):
    req = write(
        tmp_path / "requirements.txt",
        """
        requests==2.32.3 \\
            --hash=sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
        """,
    )
    res = runner.invoke(app, ["--path", str(req), "--system-ok", "--no-upgrade", "--no-use-config"])
    assert res.exit_code == ExitCode.HASHES_PRESENT, f"Expected exit {ExitCode.HASHES_PRESENT} for hashed file"
    assert "hash" in res.output.lower(), f"Expected a helpful message mentioning 'hash'. Output:\n{res.output}"


def test_cli_dry_run_and_check_exit_codes(tmp_path: Path, monkeypatch):
    req = write(tmp_path / "requirements.txt", "pandas>=1.0.0\n")

    # FIX: Patch the functions in the 'core' module where they are imported and used.
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"pandas": "2.2.2"})
    # Also patch the venv check to simplify the test command.
    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda system_ok: None)

    res = runner.invoke(
        app,
        # We can now remove --system-ok because the check is fully mocked.
        ["--path", str(req), "--no-upgrade", "--dry-run", "--show-diff", "--no-use-config"],
    )
    assert res.exit_code == ExitCode.OK, f"Dry-run should not fail. Output:\n{res.output}"
    assert "pandas>=2.2.2" in res.output, "Output should include the diff or helpful text"

    res2 = runner.invoke(
        app,
        ["--path", str(req), "--no-upgrade", "--check", "--show-diff", "--no-use-config"],
    )
    assert res2.exit_code == ExitCode.CHANGES_WOULD_BE_MADE, "Check mode must signal changes via exit 11"
    assert "pandas>=2.2.2" in res2.output, "Output should still include the diff or helpful text"
