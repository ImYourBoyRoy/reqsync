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


def write(p: Path, content: str) -> Path:
    """Helper to write dedented content to a file."""
    text = textwrap.dedent(content).lstrip("\n")
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def test_venv_guard_blocks_without_system_ok(tmp_path: Path, monkeypatch):
    req = write(tmp_path / "requirements.txt", "pandas\n")

    monkeypatch.setattr(env_mod, "is_venv_active", lambda: False)

    # FIX: Remove the "run" command from the invoke call.
    res = runner.invoke(app, ["--path", str(req), "--no-upgrade", "--no-use-config"])

    assert res.exit_code == ExitCode.SYSTEM_PYTHON_BLOCKED, (
        f"Expected venv guard to block with exit {ExitCode.SYSTEM_PYTHON_BLOCKED}, but got {res.exit_code}.\n"
        f"Output:\n{res.output}"
    )
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
    code, out = core_mod.run_pip_upgrade(
        str(tmp_path / "requirements.txt"),
        timeout_sec=5,
        extra_args="--index-url https://simple --bogus-flag --trusted-host pypi.org",
    )
    assert code == 0 and out == "ok"
    sent = " ".join(captured["cmd"])
    assert "--index-url" in sent and "--trusted-host" in sent
    assert "--bogus-flag" not in sent
