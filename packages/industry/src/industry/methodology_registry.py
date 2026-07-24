"""Industry Methodology registry — policy ownership only."""

from __future__ import annotations

from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.enums import MethodologyLifecycle
from industry.exceptions import IndustryError
from industry.methodology import (
    AssembledMethodology,
    IndustryMethodology,
    assemble_methodology,
)
from industry.semver import parse_semver
from industry.taxonomy import IndustryTaxonomy

__all__ = ["IndustryMethodologyRegistry"]


class IndustryMethodologyRegistry:
    """Versioned registry of IndustryMethodology policies.

    One methodology id is bound to one industry_id. Multiple semver versions
    may coexist; lookup_active returns the highest ACTIVE semver.
    """

    def __init__(
        self,
        taxonomy: IndustryTaxonomy,
        characteristics: InvestmentCharacteristicsRegistry | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._characteristics = characteristics
        self._by_key: dict[tuple[str, str], IndustryMethodology] = {}
        # industry_id → methodology id (enforces one lineage per industry)
        self._industry_method: dict[str, str] = {}

    def register(self, methodology: IndustryMethodology) -> IndustryMethodology:
        self._validate_refs(methodology)
        existing_lineage = self._industry_method.get(methodology.industry_id)
        if (
            existing_lineage is not None
            and existing_lineage != methodology.id
        ):
            msg = (
                f"industry {methodology.industry_id!r} already bound to "
                f"methodology {existing_lineage!r}; cannot register "
                f"{methodology.id!r}"
            )
            raise IndustryError(msg)
        key = methodology.registry_key
        existing = self._by_key.get(key)
        if existing is not None:
            if existing == methodology:
                return existing
            msg = (
                f"duplicate industry methodology: {methodology.id!r} "
                f"version {methodology.version!r}"
            )
            raise IndustryError(msg)
        self._by_key[key] = methodology
        self._industry_method[methodology.industry_id] = methodology.id
        return methodology

    def get(self, methodology_id: str, *, version: str) -> IndustryMethodology:
        key = (methodology_id.strip().lower(), parse_semver(version).raw)
        try:
            return self._by_key[key]
        except KeyError as exc:
            msg = f"unknown industry methodology: {key!r}"
            raise IndustryError(msg) from exc

    def lookup(
        self, methodology_id: str, *, version: str
    ) -> IndustryMethodology:
        """Alias for get — explicit version pin."""
        return self.get(methodology_id, version=version)

    def lookup_active(self, methodology_id: str) -> IndustryMethodology:
        mid = methodology_id.strip().lower()
        active = [
            m
            for m in self._by_key.values()
            if m.id == mid and m.status is MethodologyLifecycle.ACTIVE
        ]
        if not active:
            msg = f"no active industry methodology for {mid!r}"
            raise IndustryError(msg)
        return max(active, key=lambda m: parse_semver(m.version))

    def lookup_active_for_industry(
        self, industry_id: str
    ) -> IndustryMethodology:
        iid = industry_id.strip().lower()
        mid = self._industry_method.get(iid)
        if mid is None:
            msg = f"no methodology registered for industry {iid!r}"
            raise IndustryError(msg)
        return self.lookup_active(mid)

    def contains(self, methodology_id: str, *, version: str | None = None) -> bool:
        mid = methodology_id.strip().lower()
        if version is not None:
            return (mid, parse_semver(version).raw) in self._by_key
        return any(m.id == mid for m in self._by_key.values())

    def list_all(
        self,
        *,
        industry_id: str | None = None,
        status: MethodologyLifecycle | None = None,
    ) -> tuple[IndustryMethodology, ...]:
        items = list(self._by_key.values())
        if industry_id is not None:
            iid = industry_id.strip().lower()
            items = [m for m in items if m.industry_id == iid]
        if status is not None:
            items = [m for m in items if m.status is status]
        return tuple(
            sorted(
                items,
                key=lambda m: (m.id, parse_semver(m.version).as_tuple()),
            )
        )

    def deprecate(
        self, methodology_id: str, *, version: str
    ) -> IndustryMethodology:
        current = self.get(methodology_id, version=version)
        if current.status is MethodologyLifecycle.DEPRECATED:
            return current
        deprecated = IndustryMethodology(
            id=current.id,
            industry_id=current.industry_id,
            version=current.version,
            status=MethodologyLifecycle.DEPRECATED,
            name=current.name,
            description=current.description,
            characteristic_ids=current.characteristic_ids,
            valuation=current.valuation,
            dimensions=current.dimensions,
            metrics=current.metrics,
            peer_policy=current.peer_policy,
            interpretation_notes=current.interpretation_notes,
            changelog=current.changelog,
        )
        self._by_key[deprecated.registry_key] = deprecated
        return deprecated

    def assemble(
        self, methodology: IndustryMethodology
    ) -> AssembledMethodology:
        """Merge methodology with registered characteristics + system defaults."""
        chars = ()
        if methodology.characteristic_ids:
            if self._characteristics is None:
                msg = (
                    "characteristics registry required to assemble methodology "
                    f"{methodology.id!r}"
                )
                raise IndustryError(msg)
            chars = tuple(
                self._characteristics.lookup_active(cid)
                for cid in methodology.characteristic_ids
            )
        return assemble_methodology(methodology, chars)

    def validate(self) -> None:
        for key, item in self._by_key.items():
            if item.registry_key != key:
                msg = f"registry corruption: key {key!r} stores {item.registry_key!r}"
                raise IndustryError(msg)
            self._validate_refs(item)
            expected_mid = self._industry_method.get(item.industry_id)
            if expected_mid != item.id:
                msg = (
                    f"registry corruption: industry {item.industry_id!r} "
                    f"maps to {expected_mid!r} but stores {item.id!r}"
                )
                raise IndustryError(msg)

    def _validate_refs(self, methodology: IndustryMethodology) -> None:
        if not self._taxonomy.contains(methodology.industry_id):
            msg = (
                f"unknown industry for methodology {methodology.id!r}: "
                f"{methodology.industry_id!r}"
            )
            raise IndustryError(msg)
        if methodology.characteristic_ids:
            if self._characteristics is None:
                msg = (
                    f"characteristics registry required for methodology "
                    f"{methodology.id!r} characteristic refs"
                )
                raise IndustryError(msg)
            for cid in methodology.characteristic_ids:
                if not self._characteristics.contains(cid):
                    msg = (
                        f"unknown investment characteristics reference: "
                        f"{cid!r} on methodology {methodology.id!r}"
                    )
                    raise IndustryError(msg)
