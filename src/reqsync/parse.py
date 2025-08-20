# src/reqsync/parse.py

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

from packaging.requirements import Requirement

PIP_DIRECTIVE_PREFIXES = (
    "-r",
    "--requirement",
    "-c",
    "--constraint",
    "-e",
    "--editable",
    "--index-url",
    "--extra-index-url",
    "--find-links",
    "--trusted-host",
    "--no-index",
)

VCS_OR_URL_RE = re.compile(r"^\s*(git\+|https?://|ssh://|file:|svn\+|hg\+|bzr\+)", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"^\s*(\.\.?/|/|[a-zA-Z]:\\)")
INCLUDE_RE = re.compile(r"^\s*(-r|--requirement)\s+(.+)$", re.IGNORECASE)
CONSTRAINT_RE = re.compile(r"^\s*(-c|--constraint)\s+(.+)$", re.IGNORECASE)


def is_pip_directive(stripped: str) -> bool:
    if not stripped or stripped.startswith("#"):
        return True
    if stripped.startswith("--"):
        return True
    token = stripped.split()[0]
    return token in PIP_DIRECTIVE_PREFIXES


def split_trailing_comment(raw_no_eol: str) -> tuple[str, str]:
    parts = raw_no_eol.split(" #", 1)
    if len(parts) == 2:
        return parts[0].rstrip(), " #" + parts[1]
    return raw_no_eol.rstrip(), ""


def guard_hashes(lines: Iterable[str], allow_hashes: bool) -> None:
    if allow_hashes:
        return
    for ln in lines:
        if "--hash=" in ln:
            raise ValueError(
                "requirements contains --hash pins. Modifying versions would invalidate hashes. "
                "Re-run with --allow-hashes to skip hashed lines."
            )


@dataclass
class ParsedLine:
    original: str
    content: str | None
    comment: str
    eol: str
    requirement: Requirement | None
    kind: str


def _split_eol(s: str) -> tuple[str, str]:
    if s.endswith("\r\n"):
        return s[:-2], "\r\n"
    if s.endswith("\n"):
        return s[:-1], "\n"
    if s.endswith("\r"):
        return s[:-1], "\r"
    return s, ""


def parse_line(line: str) -> ParsedLine:
    raw, eol = _split_eol(line)
    stripped = raw.strip()

    if not stripped or stripped.startswith("#"):
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="comment")
    if "--hash=" in stripped:
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="hashed")
    if stripped.startswith(("-e", "--editable")):
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="editable")
    if is_pip_directive(stripped):
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="directive")
    if VCS_OR_URL_RE.match(stripped):
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="vcs")
    if LOCAL_PATH_RE.match(stripped):
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="path")

    content, comment = split_trailing_comment(raw)
    try:
        req = Requirement(content)
        return ParsedLine(original=line, content=content, comment=comment, eol=eol, requirement=req, kind="package")
    except Exception:
        logging.warning("Unparseable requirement kept as-is: %s", stripped)
        return ParsedLine(original=line, content=None, comment="", eol=eol, requirement=None, kind="comment")


def find_includes(lines: Iterable[str]) -> list[str]:
    incs: list[str] = []
    for ln in lines:
        m = INCLUDE_RE.match(ln.strip())
        if m:
            incs.append(m.group(2))
    return incs


def find_constraints(lines: Iterable[str]) -> list[str]:
    cons: list[str] = []
    for ln in lines:
        m = CONSTRAINT_RE.match(ln.strip())
        if m:
            cons.append(m.group(2))
    return cons
