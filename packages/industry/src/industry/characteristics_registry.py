"""Investment Characteristics registry."""

from __future__ import annotations

from industry.characteristics import InvestmentCharacteristics
from industry.enums import CharacteristicLifecycle
from industry.exceptions import IndustryError
from industry.semver import parse_semver

__all__ = ["InvestmentCharacteristicsRegistry"]


class InvestmentCharacteristicsRegistry:
    """Versioned registry of reusable investment archetypes.

    Provides defaults for future IndustryMethodology — never peers or metrics.
    """

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], InvestmentCharacteristics] = {}

    def register(
        self, characteristics: InvestmentCharacteristics
    ) -> InvestmentCharacteristics:
        key = characteristics.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == characteristics:
                return existing
            msg = (
                f"duplicate investment characteristics: "
                f"{characteristics.id!r} version {characteristics.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = characteristics
        return characteristics

    def get(self, characteristic_id: str, *, version: str) -> InvestmentCharacteristics:
        key = (
            characteristic_id.strip().lower(),
            parse_semver(version).raw,
        )
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown investment characteristics: {key!r}"
            raise IndustryError(msg) from exc

    def lookup_active(self, characteristic_id: str) -> InvestmentCharacteristics:
        """Return ACTIVE version with greatest semantic version."""
        cid = characteristic_id.strip().lower()
        active = [
            c
            for c in self._by_key.values()
            if c.id == cid and c.status is CharacteristicLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active investment characteristics for {cid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda c: parse_semver(c.version))

    def list_all(
        self,
        *,
        status: CharacteristicLifecycle | None = None,
    ) -> tuple[InvestmentCharacteristics, ...]:
        items = list(self._by_key.values())
        if status is not None:
            items = [c for c in items if c.status is status]
        return tuple(sorted(items, key=lambda c: c.registry_key))

    def contains(self, characteristic_id: str, *, version: str | None = None) -> bool:
        cid = characteristic_id.strip().lower()
        if version is not None:
            return (cid, parse_semver(version).raw) in self._by_key
        return any(c.id == cid for c in self._by_key.values())

    def deprecate(
        self, characteristic_id: str, *, version: str
    ) -> InvestmentCharacteristics:
        current = self.get(characteristic_id, version=version)
        if current.status is CharacteristicLifecycle.DEPRECATED:
            return current
        deprecated = InvestmentCharacteristics(
            id=current.id,
            name=current.name,
            version=current.version,
            status=CharacteristicLifecycle.DEPRECATED,
            description=current.description,
            capital_intensity=current.capital_intensity,
            cash_flow_profile=current.cash_flow_profile,
            growth_profile=current.growth_profile,
            earnings_stability=current.earnings_stability,
            cyclicality=current.cyclicality,
            pricing_power=current.pricing_power,
            regulatory_intensity=current.regulatory_intensity,
            asset_intensity=current.asset_intensity,
            capital_allocation_style=current.capital_allocation_style,
            competitive_character=current.competitive_character,
            business_economics_notes=current.business_economics_notes,
            defaults=current.defaults,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def validate(self) -> None:
        """Integrity check — unique keys already enforced; sanity on ids."""
        for key, item in self._by_key.items():
            if item.registry_key != key:
                msg = f"registry corruption: key {key!r} stores {item.registry_key!r}"
                raise IndustryError(msg)
            if not item.id or not item.version:
                msg = f"invalid characteristics entry: {item!r}"
                raise IndustryError(msg)
