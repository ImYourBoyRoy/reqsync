# ./tests/test_parse.py
"""Requirements parsing behavior tests.

Validates line classification and linked-file discovery to keep rewrite behavior
predictable across directives, package lines, and hash-protected stanzas.
"""

from __future__ import annotations

import pytest

from reqsync.errors import HashPinsPresentError
from reqsync.parse import find_file_links, guard_hashes, parse_line


def test_parse_line_classifies_package_and_preserves_comment() -> None:
    parsed = parse_line('pandas>=1.0 # keep me\n')
    assert parsed.kind == "package"
    assert parsed.requirement is not None
    assert parsed.comment == " # keep me"
    assert parsed.eol == "\n"


def test_parse_line_classifies_directives_and_hashes() -> None:
    directive = parse_line("--index-url https://pypi.org/simple\n")
    hashed = parse_line("requests==2.31.0 --hash=sha256:abc\n")

    assert directive.kind == "directive"
    assert hashed.kind == "hashed"


def test_find_file_links_extracts_include_and_constraint_paths() -> None:
    lines = [
        "-r requirements/base.txt\n",
        "--constraint requirements/constraints.txt # pinned\n",
    ]
    refs = find_file_links(lines)

    assert len(refs) == 2
    assert refs[0].kind == "requirement" and refs[0].path == "requirements/base.txt"
    assert refs[1].kind == "constraint" and refs[1].path == "requirements/constraints.txt"


def test_guard_hashes_raises_without_allow_hashes() -> None:
    with pytest.raises(HashPinsPresentError):
        guard_hashes(["requests==2.31.0 --hash=sha256:abc"], allow_hashes=False)

    guard_hashes(["requests==2.31.0 --hash=sha256:abc"], allow_hashes=True)
