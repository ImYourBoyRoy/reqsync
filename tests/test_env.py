# tests/test_env.py

import subprocess
import textwrap
from pathlib import Path

from typer.testing import CliRunner

from reqsync import core as core_mod
from reqsync import env as env_mod
from reqsync._types import ExitCode
from reqsync.cli import app

runner = CliRunner()


# Add the write helper for consistency
def write(p: Path, content: str) -> Path:
    p.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8", newline="\n")
    return p


def test_venv_guard_blocks_without_system_ok(tmp_path: Path, monkeypatch):
    req = write(tmp_path / "requirements.txt", "pandas\n")

    # Patch 'is_venv_active' in the 'env' module, which is the correct scope.
    monkeypatch.setattr(env_mod, "is_venv_active", lambda: False)

    # Invoke the app without the "run" command.
    res = runner.invoke(app, ["--path", str(req), "--no-upgrade", "--no-use-config"])

    # FIX: Split the long f-string to conform to the line length limit.
    assert res.exit_code == ExitCode.SYSTEM_PYTHON_BLOCKED, (
        f"Expected exit {ExitCode.SYSTEM_PYTHON_BLOCKED}, got {res.exit_code}.\nOutput:\n{res.output}"
    )
    # The error message from Typer goes to the output stream
    assert "virtualenv" in res.output.lower(), "Message should clearly explain the venv requirement"


def test_run_pip_upgrade_filters_disallowed_args(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["cmd"] = args[0]

        class R:
            returncode = 0
            stdout = "ok"

        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    # This patch on core_mod is correct because sync() calls the alias directly
    code, out = core_mod.run_pip_upgrade(
        str(tmp_path / "requirements.txt"),
        timeout_sec=5,
        extra_args="--index-url https://simple --bogus-flag --trusted-host pypi.org",
    )
    assert code == 0 and out == "ok"
    sent = " ".join(captured["cmd"])
    assert "--index-url" in sent and "--trusted-host" in sent
    assert "--bogus-flag" not in sent
