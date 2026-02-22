# ./src/reqsync/policy.py
"""Version rewrite policies used by reqsync.

The policy layer converts an installed version plus an existing requirement line
into a rewritten requirement string according to selected floor/cap semantics.
"""

from __future__ import annotations

from dataclasses import dataclass

from packaging.requirements import Requirement
from packaging.version import Version

from ._types import Policy


@dataclass(frozen=True)
class CapStrategy:
    """Controls cap behavior for floor-and-cap policy."""

    default: str = "next-major"
    per_package: dict[str, str] | None = None

    def for_package(self, name: str) -> str:
        if self.per_package and name in self.per_package:
            return self.per_package[name]
        return self.default


def _next_major(version: Version) -> str:
    return f"{version.major + 1}.0.0"


def _next_minor(version: Version) -> str:
    return f"{version.major}.{version.minor + 1}.0"


def _build_base_requirement(req: Requirement) -> str:
    output = req.name
    if req.extras:
        output += "[" + ",".join(sorted(req.extras)) + "]"
    return output


_FLOOR_OPERATORS = {">=", ">", "~=", "=="}


def _with_floor_preserving_non_floor(req: Requirement, floor_version: str, require_existing_floor: bool) -> str | None:
    """Return specifiers with an updated floor and preserved non-floor constraints."""

    preserved: list[str] = []
    has_existing_floor = False
    for item in req.specifier:
        if item.operator in _FLOOR_OPERATORS:
            has_existing_floor = True
            continue
        preserved.append(str(item))

    if require_existing_floor and not has_existing_floor:
        return None

    return ",".join([f">={floor_version}", *preserved])


def apply_policy(
    req: Requirement,
    installed_version: str,
    policy: Policy,
    allow_prerelease: bool,
    keep_local: bool,
    cap_strategy: CapStrategy | None = None,
) -> str | None:
    """Return a rewritten requirement line content or None for no-op."""

    parsed = Version(installed_version)

    if (parsed.is_prerelease or parsed.is_devrelease) and not allow_prerelease:
        return None

    floor_version = installed_version if (parsed.local and keep_local) else parsed.public

    if policy == "update-in-place":
        if not req.specifier:
            spec = f">={floor_version}"
        else:
            updated = False
            spec_parts: list[str] = []
            for item in req.specifier:
                if item.operator in {">=", "~=", "=="}:
                    spec_parts.append(f"{item.operator}{floor_version}")
                    updated = True
                else:
                    spec_parts.append(str(item))
            if not updated:
                spec_parts.append(f">={floor_version}")
            spec = ",".join(spec_parts)
    elif policy == "lower-bound":
        maybe_spec = _with_floor_preserving_non_floor(req, floor_version, require_existing_floor=False)
        if maybe_spec is None:
            return None
        spec = maybe_spec
    elif policy == "floor-only":
        maybe_spec = _with_floor_preserving_non_floor(req, floor_version, require_existing_floor=True)
        if maybe_spec is None:
            return None
        spec = maybe_spec
    elif policy == "floor-and-cap":
        strategy = cap_strategy.for_package(req.name) if cap_strategy else "next-major"
        upper = _next_major(parsed) if strategy == "next-major" else _next_minor(parsed)
        spec = f">={floor_version},<{upper}"
    else:
        spec = f">={floor_version}"

    output = _build_base_requirement(req)
    if spec:
        output += spec
    if req.marker:
        output += f"; {req.marker}"
    return output


__all__ = ["CapStrategy", "apply_policy"]
