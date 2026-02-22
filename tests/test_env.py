# ./tests/test_env.py
"""Environment helper tests for reqsync.

Validates virtualenv safety checks and pip-arg filtering behavior used by the
core orchestration layer.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from reqsync import core as core_mod
from reqsync import env as env_mod
from reqsync._types import ExitCode
from reqsync.cli import app

runner = CliRunner()


def test_venv_guard_blocks_without_system_ok(tmp_path: Path, monkeypatch) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("pandas\n", encoding="utf-8")

    monkeypatch.setattr(env_mod, "is_venv_active", lambda: False)

    result = runner.invoke(app, ["run", "--path", str(req), "--no-upgrade", "--no-use-config"])
    assert result.exit_code == int(ExitCode.SYSTEM_PYTHON_BLOCKED)
    assert "virtualenv" in result.output.lower()


def test_run_pip_upgrade_filters_disallowed_args(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(*args, **kwargs):
        captured["cmd"] = args[0]

        class Response:
            returncode = 0
            stdout = "ok"

        return Response()

    monkeypatch.setattr(subprocess, "run", fake_run)

    code, out = core_mod.run_pip_upgrade(
        str(tmp_path / "requirements.txt"),
        timeout_sec=5,
        extra_args="--index-url https://simple --bogus-flag --trusted-host pypi.org",
    )

    assert code == 0 and out == "ok"
    sent = " ".join(captured["cmd"])
    assert "--index-url" in sent and "--trusted-host" in sent
    assert "--bogus-flag" not in sent


def test_git_dirty_detects_when_status_has_output(monkeypatch, tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir(parents=True)

    class FakeProc:
        returncode = 0
        stdout = " M README.md\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeProc())

    assert env_mod.is_git_dirty(tmp_path) is True
