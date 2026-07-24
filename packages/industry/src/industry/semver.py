"""Semantic version parsing and ordering for industry registries."""

from __future__ import annotations

import re

from core.exceptions import ValidationError

__all__ = [
    "SemVer",
    "compare_semver",
    "parse_semver",
    "require_semver",
]

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)$"
)


class SemVer:
    """MAJOR.MINOR.PATCH only — no prerelease / build metadata in C2.3."""

    __slots__ = ("major", "minor", "patch", "raw")

    def __init__(self, major: int, minor: int, patch: int, *, raw: str) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch
        self.raw = raw

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.as_tuple() <= other.as_tuple()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.as_tuple() > other.as_tuple()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.as_tuple() >= other.as_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()

    def __hash__(self) -> int:
        return hash(self.as_tuple())

    def __repr__(self) -> str:
        return f"SemVer({self.raw!r})"


def parse_semver(version: str) -> SemVer:
    cleaned = version.strip()
    match = _SEMVER_RE.fullmatch(cleaned)
    if match is None:
        msg = (
            f"invalid semantic version {version!r}; "
            f"expected MAJOR.MINOR.PATCH (e.g. '1.0.0')"
        )
        raise ValidationError(msg)
    return SemVer(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        raw=cleaned,
    )


def require_semver(version: str, *, field: str = "version") -> str:
    """Validate and return normalized semver string (trimmed)."""
    return parse_semver(version).raw


def compare_semver(left: str, right: str) -> int:
    """Return -1 / 0 / 1 for left < / == / > right."""
    a = parse_semver(left).as_tuple()
    b = parse_semver(right).as_tuple()
    if a < b:
        return -1
    if a > b:
        return 1
    return 0
