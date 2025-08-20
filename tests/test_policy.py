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
    assert out is not None and ">=1.2.3" in out and "+cpu" not in out, (
        f"Local segment should be stripped by default, got {out}"
    )


def test_update_in_place_policy():
    # Test case 1: Update '=='
    req1 = Requirement("pandas==1.0")
    out1 = apply_policy(req1, "2.2.2", policy="update-in-place", allow_prerelease=False, keep_local=False)
    assert out1 == "pandas==2.2.2", f"Expected '==2.2.2', got {out1}"

    # Test case 2: Update '~='
    req2 = Requirement("django~=4.0")
    out2 = apply_policy(req2, "4.2.1", policy="update-in-place", allow_prerelease=False, keep_local=False)
    assert out2 == "django~=4.2.1", f"Expected '~=4.2.1', got {out2}"

    # Test case 3: Update '>=' and preserve '<'
    req3 = Requirement("pydantic>=2.0,<3.0")
    out3 = apply_policy(req3, "2.7.0", policy="update-in-place", allow_prerelease=False, keep_local=False)
    # The order might change due to sorting, so check for both parts
    assert out3 is not None
    assert ">=2.7.0" in out3 and "<3.0" in out3, f"Expected '>=2.7.0,<3.0', got {out3}"

    # Test case 4: No specifier, defaults to '>='
    req4 = Requirement("requests")
    out4 = apply_policy(req4, "2.31.0", policy="update-in-place", allow_prerelease=False, keep_local=False)
    assert out4 == "requests>=2.31.0", f"Expected '>=2.31.0' for empty spec, got {out4}"

    # Test case 5: Only a ceiling specifier, should add a floor
    req5 = Requirement("somepkg<2.0")
    out5 = apply_policy(req5, "1.5.0", policy="update-in-place", allow_prerelease=False, keep_local=False)
    assert out5 is not None
    assert ">=1.5.0" in out5 and "<2.0" in out5, f"Expected to add '>=1.5.0', got {out5}"
