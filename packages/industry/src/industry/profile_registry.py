"""Industry Profile registry — optional characteristic references."""

from __future__ import annotations

from industry.characteristics import IndustryProfile
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import CharacteristicLifecycle
from industry.exceptions import IndustryError
from industry.semver import parse_semver
from industry.taxonomy import IndustryTaxonomy

__all__ = ["IndustryProfileRegistry"]


class IndustryProfileRegistry:
    """Stores IndustryProfile shells that reference characteristics by id.

    Does not implement methodology. Validates industry and characteristic
    references against injected registries.
    """

    def __init__(
        self,
        taxonomy: IndustryTaxonomy,
        characteristics: InvestmentCharacteristicsRegistry,
    ) -> None:
        self._taxonomy = taxonomy
        self._characteristics = characteristics
        self._by_key: dict[tuple[str, str], IndustryProfile] = {}

    def register(self, profile: IndustryProfile) -> IndustryProfile:
        if not self._taxonomy.contains(profile.industry_id):
            msg = (
                f"cannot create profile for unknown industry: "
                f"{profile.industry_id!r}"
            )
            raise IndustryError(msg)
        for cid in profile.characteristic_ids:
            if not self._characteristics.contains(cid):
                msg = (
                    f"unknown investment characteristics reference: {cid!r} "
                    f"on profile {profile.industry_id!r}"
                )
                raise IndustryError(msg)
        key = profile.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == profile:
                return existing
            msg = (
                f"duplicate industry profile: {profile.industry_id!r} "
                f"version {profile.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = profile
        return profile

    def get(self, industry_id: str, *, version: str) -> IndustryProfile:
        key = (industry_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown industry profile: {key!r}"
            raise IndustryError(msg) from exc

    def lookup_active(self, industry_id: str) -> IndustryProfile:
        iid = industry_id.strip().lower()
        active = [
            p
            for p in self._by_key.values()
            if p.industry_id == iid
            and p.status is CharacteristicLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry profile for {iid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda p: parse_semver(p.version))

    def list_all(
        self,
        *,
        status: CharacteristicLifecycle | None = None,
    ) -> tuple[IndustryProfile, ...]:
        items = list(self._by_key.values())
        if status is not None:
            items = [p for p in items if p.status is status]
        return tuple(sorted(items, key=lambda p: p.registry_key))

    def validate(self) -> None:
        for profile in self._by_key.values():
            if not self._taxonomy.contains(profile.industry_id):
                msg = (
                    f"broken profile reference to unknown industry "
                    f"{profile.industry_id!r}"
                )
                raise IndustryError(msg)
            for cid in profile.characteristic_ids:
                if not self._characteristics.contains(cid):
                    msg = (
                        f"broken profile reference to unknown characteristics "
                        f"{cid!r}"
                    )
                    raise IndustryError(msg)
