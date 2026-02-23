# ./tests/test_cli.py
"""CLI-level behavior tests for reqsync.

Covers user-facing exit codes and output behavior for common sync scenarios,
including missing files, hash safety blocks, and check-mode signaling.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from reqsync import cli as cli_mod
from reqsync import core as core_mod
from reqsync._types import ExitCode
from reqsync.cli import app

runner = CliRunner()


def _write(path: Path, content: str) -> Path:
    text = textwrap.dedent(content).lstrip("\n")
    path.write_text(text, encoding="utf-8")
    return path


def test_cli_missing_file_returns_clear_exit_code(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    result = runner.invoke(app, ["run", "--path", str(missing), "--system-ok", "--no-upgrade", "--no-use-config"])
    assert result.exit_code == int(ExitCode.MISSING_FILE)


def test_cli_refuses_hashed_requirements_with_helpful_message(tmp_path: Path) -> None:
    req = _write(
        tmp_path / "requirements.txt",
        """
        requests==2.32.3 \\
            --hash=sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
        """,
    )
    result = runner.invoke(app, ["run", "--path", str(req), "--system-ok", "--no-upgrade", "--no-use-config"])
    assert result.exit_code == int(ExitCode.HASHES_PRESENT)
    assert "hash" in result.output.lower()


def test_cli_dry_run_and_check_exit_codes(tmp_path: Path, monkeypatch) -> None:
    req = _write(tmp_path / "requirements.txt", "pandas>=1.0.0\n")

    core_mod.get_installed_versions.cache_clear()
    monkeypatch.setattr(core_mod, "get_installed_versions", lambda: {"pandas": "2.2.2"})
    monkeypatch.setattr(core_mod, "ensure_venv_or_exit", lambda _system_ok: None)
    monkeypatch.setattr(core_mod, "ensure_git_clean_or_exit", lambda _repo_root, _allow_dirty: None)

    dry_result = runner.invoke(
        app,
        ["run", "--path", str(req), "--no-upgrade", "--dry-run", "--show-diff", "--no-use-config"],
    )
    assert dry_result.exit_code == int(ExitCode.OK)
    assert "pandas>=2.2.2" in dry_result.output

    check_result = runner.invoke(
        app,
        ["run", "--path", str(req), "--no-upgrade", "--check", "--show-diff", "--no-use-config"],
    )
    assert check_result.exit_code == int(ExitCode.CHANGES_WOULD_BE_MADE)
    assert "pandas>=2.2.2" in check_result.output


def test_subcommand_help_lists_other_available_commands() -> None:
    for command in ("run", "version", "mcp"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
        normalized = " ".join(result.output.split())
        assert "Other reqsync commands:" in normalized
        assert "reqsync run [OPTIONS]" in normalized
        assert "reqsync help" in normalized
        assert "reqsync version" in normalized
        assert "reqsync mcp" in normalized


def test_help_command_includes_discoverability_guidance() -> None:
    result = runner.invoke(app, ["help", "all"])
    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "reqsync run --help" in normalized
    assert "reqsync mcp --help" in normalized
    assert "reqsync help [all|run|version|mcp]" in normalized


def test_cli_version_option_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.startswith("reqsync ")


def test_cli_annotations_avoid_pep604_runtime_union_for_py39_typer_compatibility() -> None:
    callbacks = [
        cli_mod.app_callback,
        cli_mod.run_command,
        cli_mod.help_command,
        cli_mod.version_command,
        cli_mod.mcp_server,
    ]

    for callback in callbacks:
        for annotation in callback.__annotations__.values():
            normalized = annotation if isinstance(annotation, str) else repr(annotation)
            assert "|" not in normalized, f"PEP 604 union found in {callback.__name__}: {normalized}"

        inspect.signature(callback)
