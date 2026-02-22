# ./tests/test_policy.py
"""Policy engine tests for requirement rewriting.

Confirms each supported policy produces expected floor/cap behavior and handles
pre-release/local versions according to safety flags.
"""

from __future__ import annotations

from packaging.requirements import Requirement

from reqsync.policy import apply_policy


def test_lower_bound_policy_basic() -> None:
    req = Requirement("pandas")
    output = apply_policy(req, "2.2.2", policy="lower-bound", allow_prerelease=False, keep_local=False)
    assert output is not None and output.startswith("pandas>=") and "2.2.2" in output


def test_lower_bound_preserves_existing_ceiling_constraints() -> None:
    req = Requirement("portalocker>=2.0,<3")
    output = apply_policy(req, "2.7.0", policy="lower-bound", allow_prerelease=False, keep_local=False)
    assert output is not None
    assert ">=2.7.0" in output
    assert "<3" in output


def test_floor_only_requires_existing_lower_bound() -> None:
    no_floor = Requirement("pandas")
    assert apply_policy(no_floor, "2.2.2", policy="floor-only", allow_prerelease=False, keep_local=False) is None

    with_floor = Requirement("pandas>=1.0")
    output = apply_policy(with_floor, "2.2.2", policy="floor-only", allow_prerelease=False, keep_local=False)
    assert output is not None and "pandas>=2.2.2" in output


def test_floor_only_preserves_existing_ceiling_constraints() -> None:
    req = Requirement("portalocker>=2.0,<3")
    output = apply_policy(req, "2.7.0", policy="floor-only", allow_prerelease=False, keep_local=False)
    assert output is not None
    assert ">=2.7.0" in output
    assert "<3" in output


def test_floor_and_cap_defaults_to_next_major() -> None:
    req = Requirement("pydantic")
    output = apply_policy(req, "2.7.0", policy="floor-and-cap", allow_prerelease=False, keep_local=False)
    assert output is not None and ">=2.7.0,<3.0.0" in output


def test_prerelease_blocked_by_default() -> None:
    req = Requirement("somepkg")
    assert apply_policy(req, "1.0.0rc1", policy="lower-bound", allow_prerelease=False, keep_local=False) is None


def test_local_version_stripped_by_default() -> None:
    req = Requirement("fastembed")
    output = apply_policy(req, "1.2.3+cpu", policy="lower-bound", allow_prerelease=True, keep_local=False)
    assert output is not None and ">=1.2.3" in output and "+cpu" not in output


def test_update_in_place_policy() -> None:
    req_equal = Requirement("pandas==1.0")
    assert (
        apply_policy(req_equal, "2.2.2", policy="update-in-place", allow_prerelease=False, keep_local=False)
        == "pandas==2.2.2"
    )

    req_compatible = Requirement("django~=4.0")
    assert (
        apply_policy(req_compatible, "4.2.1", policy="update-in-place", allow_prerelease=False, keep_local=False)
        == "django~=4.2.1"
    )

    req_range = Requirement("pydantic>=2.0,<3.0")
    output = apply_policy(req_range, "2.7.0", policy="update-in-place", allow_prerelease=False, keep_local=False)
    assert output is not None and ">=2.7.0" in output and "<3.0" in output

    req_empty = Requirement("requests")
    assert (
        apply_policy(req_empty, "2.31.0", policy="update-in-place", allow_prerelease=False, keep_local=False)
        == "requests>=2.31.0"
    )
