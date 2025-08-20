# 🧩 reqsync

[![PyPI Version](https://img.shields.io/pypi/v/reqsync.svg)](https://pypi.org/project/reqsync/)
[![Python Versions](https://img.shields.io/pypi/pyversions/reqsync.svg)](https://pypi.org/project/reqsync/)
[![CI Status](https://github.com/ImYourBoyRoy/reqsync/actions/workflows/ci.yml/badge.svg)](https://github.com/ImYourBoyRoy/reqsync/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/reqsync.svg)](https://opensource.org/licenses/MIT)
[![Typing: PEP 561](https://img.shields.io/badge/Typing-PEP%20561-informational.svg)](https://peps.python.org/pep-0561/)

> Upgrade a venv and rewrite requirements to match installed versions, safely and atomically. Preserves operators (`==`, `>=`, `~=`), extras, markers, comments, encoding, and line endings.

---

## ✨ Design goals

* **Safety first**
  Refuse outside a venv by default. Abort on `--hash` unless you opt in to skipping those stanzas. Atomic writes with rollback.

* **Do one job well**
  Upgrade env, then floor top-level requirements to what’s actually installed. No lockfile management.

* **Zero ceremony**
  Works from the CLI without any config. Optional TOML/pyproject config if you want it.

* **Agent friendly**
  Clean Python API that returns a structured `Result` for tool-calling, MCP, CrewAI, AG2, etc.

---

## ⭐ Features

* Venv guard on by default; `--system-ok` to override.
* Preserves extras `[a,b]`, markers `; sys_platform != "win32"`, inline comments, encoding (BOM), and newline style (LF/CRLF).
* Includes recursion: follows `-r other.txt` by default.
* Constraints awareness: detects `-c constraints.txt` and skips modifying unless `--update-constraints`.
* Policy modes: `lower-bound` (default), `floor-only`, `floor-and-cap` (`< next major`).
* Pre/dev handling: `--allow-prerelease` to adopt, `--keep-local` to keep `+local` suffixes.
* Hash-aware: refuses by default if `--hash` is present; `--allow-hashes` skips those stanzas without editing.
* File locking with `portalocker`. Backup + atomic replace. Rollback on failure.
* UX for humans and CI: `--dry-run`, `--show-diff`, `--check`, `--json-report`, `--only/--exclude`.
* Minimal runtime deps.

---

## 🚀 Installation

```bash
pip install reqsync
```

> Requires Python 3.8+.

---

## 🧪 Quick start

```bash
# Activate your venv (required by default)
source .venv/bin/activate

# Preview
reqsync run --path requirements.txt --dry-run --show-diff

# Apply with backup
reqsync run --path requirements.txt --show-diff
```

Common variations:

```bash
# Read-only sync to current env (don’t run pip)
reqsync run --no-upgrade --show-diff

# CI gate: fail if changes would be made
reqsync run --check --no-upgrade --path requirements.txt
```

---

## 🛠️ CLI

```bash
reqsync run [OPTIONS]
```

Key options:

* `--path PATH` target requirements (default `requirements.txt`)
* `--follow-includes / --no-follow-includes` follow `-r` recursively (default true)
* `--update-constraints` allow modifying constraint files (default false)
* `--policy [lower-bound|floor-only|floor-and-cap]` default `lower-bound`
* `--allow-prerelease` adopt pre/dev; `--keep-local` keep `+local`
* `--no-upgrade` skip `pip install -U -r`
* `--pip-args "..."` allowlisted pip flags (indexes, proxies, `-r`, `-c`)
* `--only PATTERNS` and `--exclude PATTERNS` scope by canonical names
* `--check` no writes; exit 11 if changes would be made
* `--dry-run` no writes; pair with `--show-diff` for unified diff
* `--json-report FILE` machine-readable changes
* `--backup-suffix S` `.bak` by default; `--timestamped-backups/--no-timestamped-backups`
* `--system-ok` allow outside a venv (not recommended)
* `--allow-hashes` skip hashed stanzas instead of refusing

Full option details: see [docs/USAGE.md](docs/USAGE.md).

---

## ⚙️ Configuration

Config is optional. CLI flags always win.

Resolution order:

1. CLI flags
2. `reqsync.toml` at project root
3. `[tool.reqsync]` in `pyproject.toml`
4. `reqsync.json`
5. Built-in defaults

Examples: see [docs/CONFIG.md](docs/CONFIG.md) and `examples/`.

---

## 🧬 Policy modes

* **lower-bound**
  Always set `>= installed_version`.

* **floor-only**
  Only raise existing lower bounds. If none exists, leave it unchanged.

* **floor-and-cap**
  Set `>= installed_version,<next_major`. Useful guardrail in larger teams.

* **update-in-place**
  Preserve the original operator (`==`, `~=`, `>=`) and only update the version. Adds `>=` if no operator is present.

---

## 📁 Includes and constraints

* `-r` includes are followed (on by default) and processed with the same rules.
* `-c` constraints are detected but not modified unless you pass `--update-constraints`.

---

## 🧵 Preservation rules

* Lines that are comments, directives (`-r`, `-c`, `--index-url`, etc.), `-e/--editable`, VCS/URL/local paths are preserved and not edited.
* Inline comments are preserved. URLs containing `#` are handled safely.
* Encoding and newline style are preserved exactly.

---

## 🔒 Safety gates

* Refuses to run outside a venv unless `--system-ok`.
* Refuses to edit hashed files (`--hash=`) by default. Use `--allow-hashes` to skip those stanzas instead.
* File lock prevents concurrent edits. Atomic replace with backup and rollback.

---

## 🤖 Python API (for agents/tools)

```python
from pathlib import Path
from reqsync._types import Options
from reqsync.core import sync

opts = Options(
    path=Path("requirements.txt"),
    follow_includes=True,
    policy="lower-bound",
    dry_run=True,
    show_diff=True,
    no_upgrade=True,
)
result = sync(opts)
print("Changed:", result.changed)
print(result.diff or "")
```

More integration patterns: [docs/INTEGRATION.md](docs/INTEGRATION.md).

---

## 📊 Exit codes

| Code | Meaning                                           |
| ---: | ------------------------------------------------- |
|    0 | Success                                           |
|    1 | Generic error                                     |
|    2 | Requirements file not found                       |
|    3 | Hashes present without `--allow-hashes`           |
|    4 | Pip upgrade failed                                |
|    5 | Parse error                                       |
|    6 | Constraint conflict detected                      |
|    7 | Refused to run outside venv without `--system-ok` |
|    8 | Repo dirty and guard blocked (if enabled)         |
|    9 | Lock acquisition timeout                          |
|   10 | Write failed; backup restored                     |
|   11 | `--check` and changes would be made               |

---

## 🔄 How this compares

| Tool             | Primary goal               | Edits your file           | Hash-aware       | Lockfile |
| ---------------- | -------------------------- | ------------------------- | ---------------- | -------- |
| **reqsync**      | Sync to installed versions | Yes, preserves formatting | Refuses or skips | No       |
| pip-tools        | Deterministic pins         | Generates pinned file     | Yes              | Yes      |
| pip-upgrader/pur | Bump versions              | Rewrites pins (==)        | No               | No       |
| uv/poetry/pdm    | Env + lock mgmt            | Manage lockfiles          | Yes              | Yes      |

Use reqsync when you want your `requirements.txt` to reflect the versions you’re actually running, while keeping future installs flexible.

---

## 📦 Versioning & release

* Version is derived from Git tags via `hatch-vcs`. Tag format: `vX.Y.Z`.
* Repo: [https://github.com/ImYourBoyRoy/reqsync](https://github.com/ImYourBoyRoy/reqsync)
* CI: tests, lint, type-check, build, twine metadata check, wheel smoke test.
* Publishing: PyPI Trusted Publishing via OIDC on tags.

---

## 🧰 Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
pre-commit install

pre-commit run -a
pytest -q
ruff check .
ruff format --check .
mypy src/reqsync
```

Contributing guidelines: [CONTRIBUTING.md](CONTRIBUTING.md)
Changelog: [CHANGELOG.md](CHANGELOG.md)

---

## 📚 Docs

* Usage: [docs/USAGE.md](docs/USAGE.md)
* Config: [docs/CONFIG.md](docs/CONFIG.md)
* Integration: [docs/INTEGRATION.md](docs/INTEGRATION.md)

---

## 📜 License

MIT. See [LICENSE](LICENSE).

---

## ⭐ Support

If this tool helps you, star the repo and share it. Issues and PRs welcome.
