"""Authoritative release-identity profiles for RC and future GA.

Living product identity is declared by PRODUCTION_VERSION_MANIFEST.json
(channel / milestone / decision). Validators select a STRICT profile from
that declaration — they do not accept arbitrary versions.

VERSION (repo root) semantics:
  Product channel version (living product/release label).
  Same domain as frontend product version for this monorepo.
  NOT the HTTP API contract (v1.0.0) and NOT the backend package alone.
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict


class ReleaseProfile(TypedDict):
    name: str
    backend: str
    frontend: str
    api_contract: str
    epic: str
    channel: str
    decision: str
    product_version: str
    milestone: str


# Living RC — current product state (EPS-003). Do not promote silently.
RC_PROFILE: ReleaseProfile = {
    "name": "RELEASE_CANDIDATE",
    "backend": "2.0.0",
    "frontend": "2.0.0-rc.1",
    "api_contract": "v1.0.0",
    "epic": "EPS-003",
    "channel": "rc",
    "decision": "RELEASE_CANDIDATE",
    "product_version": "2.0.0-rc.1",
    "milestone": "EPS-003",
}

# Future GA — preserved for certify_p8 / promotion; not the living state.
GA_PROFILE: ReleaseProfile = {
    "name": "GA_CANDIDATE",
    "backend": "2.0.0",
    "frontend": "2.0.0",
    "api_contract": "v1.0.0",
    "epic": "P8.0",
    "channel": "ga-candidate",
    "decision": "GO_WITH_CONDITIONS",
    "product_version": "2.0.0",
    "milestone": "P8.0",
}

RELEASE_PROFILES: dict[str, ReleaseProfile] = {
    RC_PROFILE["channel"]: RC_PROFILE,
    GA_PROFILE["channel"]: GA_PROFILE,
}


def resolve_profile(prod_manifest: Mapping[str, Any]) -> ReleaseProfile:
    """Resolve a strict profile from the living production manifest channel."""
    channel = str(prod_manifest.get("channel") or "").strip()
    if channel not in RELEASE_PROFILES:
        known = ", ".join(sorted(RELEASE_PROFILES))
        raise ValueError(
            f"Unknown release channel {channel!r}; expected one of: {known}"
        )
    return RELEASE_PROFILES[channel]


def profile_matches_manifest(
    profile: ReleaseProfile, prod_manifest: Mapping[str, Any]
) -> list[str]:
    """Return human-readable mismatch details (empty if aligned)."""
    checks = (
        ("milestone", profile["milestone"], prod_manifest.get("milestone")),
        ("backendVersion", profile["backend"], prod_manifest.get("backendVersion")),
        ("frontendVersion", profile["frontend"], prod_manifest.get("frontendVersion")),
        ("apiContract", profile["api_contract"], prod_manifest.get("apiContract")),
        ("channel", profile["channel"], prod_manifest.get("channel")),
        ("decision", profile["decision"], prod_manifest.get("decision")),
    )
    mismatches: list[str] = []
    for key, expected, actual in checks:
        if actual != expected:
            mismatches.append(f"{key}: expected {expected!r}, got {actual!r}")
    return mismatches
