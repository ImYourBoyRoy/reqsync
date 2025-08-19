# src/reqsync/policy.py

from __future__ import annotations

from dataclasses import dataclass

from packaging.requirements import Requirement
from packaging.version import Version

from ._types import Policy


@dataclass
class CapStrategy:
    # future expansion: per-package strategy like "next-major" or "next-minor"
    default: str = "next-major"
    per_package: dict[str, str] | None = None

    def for_package(self, name: str) -> str:
        if self.per_package and name in self.per_package:
            return self.per_package[name]
        return self.default


def _next_major(v: Version) -> str:
    return f"{v.major + 1}.0.0"


def _next_minor(v: Version) -> str:
    return f"{v.major}.{v.minor + 1}.0"


def apply_policy(
    req: Requirement,
    installed_version: str,
    policy: Policy,
    allow_prerelease: bool,
    keep_local: bool,
    cap_strategy: CapStrategy | None = None,
) -> str | None:
    """
    Return new content string for the requirement applying the given policy.
    Return None to indicate no change should be made.
    """
    v = Version(installed_version)

    if (v.is_prerelease or v.is_devrelease) and not allow_prerelease:
        return None

    floor_version = installed_version
    if v.local and not keep_local:
        # FIX: Use v.public to correctly strip the local version segment.
        floor_version = v.public

    # Build new spec according to policy
    if policy == "lower-bound":
        new_spec = f">={floor_version}"
    elif policy == "floor-only":
        # Only raise an existing lower bound if present and lower than installed
        if not req.specifier:
            return None
        # Find any lower bound
        lowered = False
        for sp in req.specifier:
            if sp.operator in (">=", ">", "~=", "=="):
                # We conservatively override to >= floor_version if installed is higher
                lowered = True
                break
        if not lowered:
            return None
        new_spec = f">={floor_version}"
    elif policy == "floor-and-cap":
        strategy = cap_strategy.for_package(req.name) if cap_strategy else "next-major"
        upper = _next_major(v) if strategy == "next-major" else _next_minor(v)
        new_spec = f">={floor_version},<{upper}"
    else:
        new_spec = f">={floor_version}"

    # Recompose requirement string
    # Keep name, extras, marker; replace specifier text
    out = req.name
    if req.extras:
        out += "[" + ",".join(sorted(req.extras)) + "]"
    if new_spec:
        out += new_spec
    if req.marker:
        out += f"; {req.marker}"
    return out
