# tests/test_policy.py

from packaging.requirements import Requirement

from reqsync.policy import apply_policy


def test_lower_bound_policy_basic():
    req = Requirement("pandas")
    out = apply_policy(req, "2.2.2", policy="lower-bound", allow_prerelease=False, keep_local=False)
    assert out is not None and out.startswith("pandas>=") and "2.2.2" in out, f"Expected floor to installed, got {out}"

def test_floor_only_requires_existing_lower_bound():
    req = Requirement("pandas")
    out = apply_policy(req, "2.2.2", policy="floor-only", allow_prerelease=False, keep_local=False)
    assert out is None, "Without an existing lower bound, floor-only should be a no-op"

    req2 = Requirement("pandas>=1.0")
    out2 = apply_policy(req2, "2.2.2", policy="floor-only", allow_prerelease=False, keep_local=False)
    assert out2 is not None and "pandas>=2.2.2" in out2, f"Should lift lower bound to installed, got {out2}"


def test_floor_and_cap_defaults_to_next_major():
    req = Requirement("pydantic")
    out = apply_policy(req, "2.7.0", policy="floor-and-cap", allow_prerelease=False, keep_local=False)
    assert out is not None and ">=2.7.0,<3.0.0" in out, f"Expected cap to next major, got {out}"


def test_prerelease_blocked_by_default():
    req = Requirement("somepkg")
    out = apply_policy(req, "1.0.0rc1", policy="lower-bound", allow_prerelease=False, keep_local=False)
    assert out is None, "Pre-release should be refused unless allow_prerelease is set"


def test_local_version_stripped_by_default():
    req = Requirement("fastembed")
    out = apply_policy(req, "1.2.3+cpu", policy="lower-bound", allow_prerelease=True, keep_local=False)
    assert out is not None and ">=1.2.3" in out and "+cpu" not in out, f"Local segment should be stripped by default, got {out}"
