# CONTRIBUTING.md

# Contributing to reqsync

Thank you for helping. This project favors correctness, safety, and minimal runtime dependencies. Keep scope tight.

Repo: https://github.com/ImYourBoyRoy/reqsync

## Ground rules
- Keep runtime deps minimal. Don’t add new runtime dependencies without discussion.
- Backward compatibility matters. Don’t change exit codes or defaults unless necessary.
- Safety first. Never modify hashed requirements, constraints, or system Python without explicit flags.
- Stay in scope. This tool floors top-level requirements to the installed versions. It does not manage lockfiles.

## What we accept
- Bug fixes with tests.
- Performance or UX improvements that don’t add runtime deps.
- Well-scoped features behind flags and with docs.
- Docs that reduce confusion or support adoption.

## What we will reject
- Features that try to replace pip-tools/poetry/uv lockfiles.
- Recomputing `--hash` values inside reqsync.
- Global state, hidden I/O, or implicit network calls beyond `pip` when requested.

---

## Getting started (dev setup)

```bash
# clone
git clone https://github.com/ImYourBoyRoy/reqsync.git
cd reqsync

# Python 3.8–3.13 supported
python -V

# create a venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# install project and dev tools
pip install -U pip
pip install -e .[dev]

# install pre-commit hooks
pre-commit install

# run the full suite once
pre-commit run -a
pytest -q
ruff check .
ruff format --check .
mypy src/reqsync
python -m build
python -m twine check dist/*
````

Quick smoke test:

```bash
python -m reqsync.cli run --path requirements.txt --dry-run --show-diff --no-upgrade
```

---

## Code style and quality

* Formatting and linting: **Ruff**. Config in `pyproject.toml`. Run `ruff check .` and `ruff format .`.
* Types: **mypy** in `strict` mode. Keep types green.
* Tests: **pytest**. Add unit tests and, if relevant, integration tests using `tmp_path`.
* Docstrings: focused and short. No narrative walls.
* Logging: use the project logger; redact secrets using the built-in redactor.

### File layout

```
src/reqsync/
  cli.py         # Typer CLI
  core.py        # Orchestration + public sync() API
  parse.py       # Requirement line parsing and classification
  policy.py      # Policy application
  io.py          # I/O, encoding/newline preservation, locking, backups
  env.py         # venv guard, pip calls, installed map
  report.py      # Diffs and JSON reports
  config.py      # Load/merge config from reqsync.toml / pyproject
  _types.py      # Options/Result types and exit codes
  _logging.py    # Logging + secret redaction
  __init__.py    # public API + __version__
tests/
  ...            # match modules with test_*.py
```

---

## Testing guidelines

Write tests that cover:

* **parse.py**: comments, inline comments with URLs, extras, markers, directives (`-r`, `-c`), VCS/URL, local paths, editables, hashed lines.
* **policy.py**: `lower-bound`, `floor-only`, `floor-and-cap`, pre/dev/local version handling.
* **io.py**: BOM and newline preservation, atomic writes, rollback on failure.
* **env.py**: venv detection, pip timeout and arg allowlist.
* **core.py**: includes recursion, constraints detection, skip logic, `--only/--exclude`, `--check`, `--dry-run`.

Fixtures:

* Use `tmp_path` for file ops. Don’t touch the repo’s files.
* If you must simulate pip, stub subprocess calls.

Minimum bar for a PR:

* New code is covered by tests.
* `pre-commit run -a` passes locally.
* CI matrix is green (Linux/macOS/Windows; Python 3.8–3.13).

---

## Commit and PR process

### Commits

* Use clear, actionable messages. Conventional Commits are welcome but not required.
* Keep changesets focused. Avoid mixed refactors + features in one PR.

### PR checklist

* [ ] Reason for change is clear in the description.
* [ ] Unit tests added or updated.
* [ ] `pre-commit run -a` is clean.
* [ ] `pytest -q` is green.
* [ ] `ruff check .` and `mypy src/reqsync` are green.
* [ ] Docs updated (USAGE/CONFIG/INTEGRATION) if flags or behavior changed.
* [ ] `CHANGELOG.md` updated under `[Unreleased]`.

### Review expectations

* We will ask for tests if missing.
* We will push back on runtime deps, scope creep, and hidden side effects.

---

## Versioning and releases

* Versions are derived from Git tags via `hatch-vcs`.
* Tag format: `vX.Y.Z`. Example:

  ```bash
  git switch -c release/v0.1.0
  # update CHANGELOG.md under [Unreleased] -> [v0.1.0] with date
  git commit -am "chore(release): v0.1.0"
  git tag -a v0.1.0 -m "v0.1.0"
  git push origin v0.1.0
  git push origin HEAD:main
  ```
* GitHub Actions `publish.yml` builds and publishes to PyPI via OIDC Trusted Publishing.

---

## Backward compatibility

* Don’t change default behavior lightly.
* Exit codes are part of the contract. If you must change them, call it out in CHANGELOG and bump MINOR or MAJOR.
* Keep Python support 3.8–current unless there’s a pressing reason to drop older versions.

---

## Security

* Don’t log secrets. The logger redacts common token patterns; still avoid printing creds.
* If you find a vulnerability, open a **private** security advisory or email the maintainer. Don’t drop a public issue with exploit details.

---

## Issue guidelines

Before opening an issue:

* Reproduce on latest `main`.
* Provide:

  * OS, Python version, `pip --version`
  * A minimal `requirements.txt` sample (redact private URLs)
  * Exact command and full output (redacted)
  * What you expected vs what happened

Feature requests:

* Describe the real workflow pain.
* Propose a flag-based solution that is off by default.
* State the impact on runtime deps (should be none).

---

## Local release dry-run (maintainers)

```bash
# clean and build
rm -rf dist build *.egg-info
python -m build

# check metadata
python -m twine check dist/*

# smoke test wheel
python -m pip install --force-reinstall dist/*.whl
python -m reqsync.cli run --help
```

---

## Thanks

Contributions that make the tool safer, clearer, or faster are welcome. Keep it focused.