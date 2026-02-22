# ./src/reqsync/parse.py
"""Line parsing helpers for requirements files and include graphs.

Used by the sync core to classify lines, preserve non-package directives, detect
hash-protected stanzas, and discover `-r`/`-c` linked files.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from packaging.requirements import Requirement

from .errors import HashPinsPresentError

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


@dataclass(frozen=True)
class IncludeRef:
    """Relationship discovered in a requirements line."""

    path: str
    kind: Literal["requirement", "constraint"]


@dataclass(frozen=True)
class ParsedLine:
    """Parsed representation of one raw requirements line."""

    original: str
    content: str | None
    comment: str
    eol: str
    requirement: Requirement | None
    kind: str


def is_pip_directive(stripped: str) -> bool:
    """Return True for non-package requirement directives."""

    if not stripped or stripped.startswith("#"):
        return True
    token = stripped.split()[0]
    if token.startswith("--") and token not in {"--hash"}:
        return True
    return token in PIP_DIRECTIVE_PREFIXES


def split_trailing_comment(raw_no_eol: str) -> tuple[str, str]:
    """Split inline comments while preserving URLs containing '#'."""

    parts = raw_no_eol.split(" #", 1)
    if len(parts) == 2:
        return parts[0].rstrip(), " #" + parts[1]
    return raw_no_eol.rstrip(), ""


def guard_hashes(lines: Iterable[str], allow_hashes: bool) -> None:
    """Fail fast when hash-pinned stanzas are present and not allowed."""

    if allow_hashes:
        return
    for line in lines:
        if "--hash=" in line:
            raise HashPinsPresentError()


def _split_eol(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def parse_line(line: str) -> ParsedLine:
    """Parse one raw requirement line preserving trailing comment and eol."""

    raw, eol = _split_eol(line)
    stripped = raw.strip()

    if not stripped or stripped.startswith("#"):
        return ParsedLine(line, None, "", eol, None, "comment")
    if "--hash=" in stripped:
        return ParsedLine(line, None, "", eol, None, "hashed")
    if stripped.startswith(("-e", "--editable")):
        return ParsedLine(line, None, "", eol, None, "editable")
    if is_pip_directive(stripped):
        return ParsedLine(line, None, "", eol, None, "directive")
    if VCS_OR_URL_RE.match(stripped):
        return ParsedLine(line, None, "", eol, None, "vcs")
    if LOCAL_PATH_RE.match(stripped):
        return ParsedLine(line, None, "", eol, None, "path")

    content, comment = split_trailing_comment(raw)
    try:
        return ParsedLine(line, content, comment, eol, Requirement(content), "package")
    except Exception:
        logging.warning("Unparseable requirement kept as-is: %s", stripped)
        return ParsedLine(line, None, "", eol, None, "unparsed")


def _extract_link_path(raw_value: str) -> str:
    value, _comment = split_trailing_comment(raw_value)
    value = value.strip().strip('"').strip("'")
    return value


def find_file_links(lines: Iterable[str]) -> list[IncludeRef]:
    """Find -r/--requirement and -c/--constraint links in a file."""

    refs: list[IncludeRef] = []
    for line in lines:
        stripped = line.strip()
        include_match = INCLUDE_RE.match(stripped)
        if include_match:
            refs.append(IncludeRef(path=_extract_link_path(include_match.group(2)), kind="requirement"))
            continue

        constraint_match = CONSTRAINT_RE.match(stripped)
        if constraint_match:
            refs.append(IncludeRef(path=_extract_link_path(constraint_match.group(2)), kind="constraint"))

    return refs


def find_includes(lines: Iterable[str]) -> list[str]:
    """Compatibility helper returning include paths only."""

    return [ref.path for ref in find_file_links(lines) if ref.kind == "requirement"]


def find_constraints(lines: Iterable[str]) -> list[str]:
    """Compatibility helper returning constraint paths only."""

    return [ref.path for ref in find_file_links(lines) if ref.kind == "constraint"]


__all__ = [
    "IncludeRef",
    "ParsedLine",
    "find_constraints",
    "find_file_links",
    "find_includes",
    "guard_hashes",
    "is_pip_directive",
    "parse_line",
    "split_trailing_comment",
]
