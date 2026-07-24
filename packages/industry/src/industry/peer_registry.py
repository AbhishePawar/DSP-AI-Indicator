"""Registries for peer eligibility policies and instrument→industry bindings."""

from __future__ import annotations

from industry.exceptions import IndustryError
from industry.peer_eligibility import (
    InstrumentIndustryAssignment,
    PeerEligibilityPolicy,
)
from industry.semver import parse_semver
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "InstrumentIndustryRegistry",
    "PeerEligibilityPolicyRegistry",
]


class PeerEligibilityPolicyRegistry:
    """Versioned store of PeerEligibilityPolicy definitions."""

    def __init__(self, taxonomy: IndustryTaxonomy) -> None:
        self._taxonomy = taxonomy
        self._by_key: dict[tuple[str, str], PeerEligibilityPolicy] = {}

    def register(self, policy: PeerEligibilityPolicy) -> PeerEligibilityPolicy:
        self._validate(policy)
        key = policy.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == policy:
                return existing
            msg = (
                f"duplicate peer eligibility policy: {policy.id!r} "
                f"version {policy.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = policy
        return policy

    def get(self, policy_id: str, *, version: str) -> PeerEligibilityPolicy:
        key = (policy_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown peer eligibility policy: {key!r}"
            raise IndustryError(msg) from exc

    def lookup_active(self, policy_id: str) -> PeerEligibilityPolicy:
        pid = policy_id.strip().lower()
        matches = [p for p in self._by_key.values() if p.id == pid]
        if not matches:
            msg = f"unknown peer eligibility policy: {pid!r}"
            raise IndustryError(msg)
        return max(matches, key=lambda p: parse_semver(p.version))

    def contains(self, policy_id: str, *, version: str | None = None) -> bool:
        pid = policy_id.strip().lower()
        if version is not None:
            return (pid, parse_semver(version).raw) in self._by_key
        return any(p.id == pid for p in self._by_key.values())

    def list_all(self) -> tuple[PeerEligibilityPolicy, ...]:
        return tuple(
            sorted(
                self._by_key.values(),
                key=lambda p: (p.id, parse_semver(p.version).as_tuple()),
            )
        )

    def validate(self) -> None:
        for key, policy in self._by_key.items():
            if policy.registry_key != key:
                msg = f"registry corruption: key {key!r} stores {policy.registry_key!r}"
                raise IndustryError(msg)
            self._validate(policy)

    def _validate(self, policy: PeerEligibilityPolicy) -> None:
        if not self._taxonomy.contains(policy.subject_industry_id):
            msg = (
                f"peer policy {policy.id!r} references unknown subject industry "
                f"{policy.subject_industry_id!r}"
            )
            raise IndustryError(msg)
        for industry_id in (
            *policy.related_industry_ids,
            *policy.limited_industry_ids,
            *policy.not_comparable_industry_ids,
        ):
            if not self._taxonomy.contains(industry_id):
                msg = (
                    f"peer policy {policy.id!r} references unknown industry "
                    f"{industry_id!r}"
                )
                raise IndustryError(msg)


class InstrumentIndustryRegistry:
    """Maps instrument symbols to DSP IndustryIdentity (explicit bindings)."""

    def __init__(self, taxonomy: IndustryTaxonomy) -> None:
        self._taxonomy = taxonomy
        self._by_symbol: dict[str, InstrumentIndustryAssignment] = {}

    def register(
        self, assignment: InstrumentIndustryAssignment
    ) -> InstrumentIndustryAssignment:
        if not self._taxonomy.contains(assignment.industry_id):
            msg = (
                f"cannot bind {assignment.symbol!r} to unknown industry "
                f"{assignment.industry_id!r}"
            )
            raise IndustryError(msg)
        existing = self._by_symbol.get(assignment.symbol)
        if existing is not None:
            if existing == assignment:
                return existing
            msg = f"duplicate instrument industry binding: {assignment.symbol!r}"
            raise IndustryError(msg)
        self._by_symbol[assignment.symbol] = assignment
        return assignment

    def get(self, symbol: str) -> InstrumentIndustryAssignment:
        key = symbol.strip().upper()
        try:
            return self._by_symbol[key]
        except KeyError as exc:
            msg = f"unresolved instrument industry binding: {key!r}"
            raise IndustryError(msg) from exc

    def contains(self, symbol: str) -> bool:
        return symbol.strip().upper() in self._by_symbol

    def list_all(self) -> tuple[InstrumentIndustryAssignment, ...]:
        return tuple(sorted(self._by_symbol.values(), key=lambda a: a.symbol))

    def validate(self) -> None:
        for symbol, assignment in self._by_symbol.items():
            if assignment.symbol != symbol:
                msg = f"registry corruption at {symbol!r}"
                raise IndustryError(msg)
            if not self._taxonomy.contains(assignment.industry_id):
                msg = (
                    f"broken binding {symbol!r} → unknown industry "
                    f"{assignment.industry_id!r}"
                )
                raise IndustryError(msg)
