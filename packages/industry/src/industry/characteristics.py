"""Investment Characteristics and Industry Profile domain models."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import (
    AssetIntensity,
    CapitalAllocationStyle,
    CapitalIntensity,
    CashFlowProfile,
    CharacteristicLifecycle,
    ComparisonDimensionHint,
    CompetitiveCharacter,
    Cyclicality,
    EarningsStability,
    GrowthProfile,
    PricingPower,
    RegulatoryIntensity,
    ValuationPhilosophyHint,
)
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "CharacteristicDefaults",
    "IndustryProfile",
    "InvestmentCharacteristics",
]


@dataclass(frozen=True, slots=True)
class CharacteristicDefaults:
    """Soft default philosophy for methodologies to inherit and override.

    Guidance only — never peer sets, metrics, or valuation engine calls.
    """

    valuation_philosophy: ValuationPhilosophyHint | None = None
    preferred_method_hints: tuple[str, ...] = ()
    dimension_emphasis: tuple[ComparisonDimensionHint, ...] = ()
    investment_philosophy_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        methods = tuple(
            m.strip().lower() for m in self.preferred_method_hints if m.strip()
        )
        notes = tuple(n.strip() for n in self.investment_philosophy_notes if n.strip())
        object.__setattr__(self, "preferred_method_hints", methods)
        object.__setattr__(self, "investment_philosophy_notes", notes)
        object.__setattr__(self, "dimension_emphasis", tuple(self.dimension_emphasis))


@dataclass(frozen=True, slots=True)
class InvestmentCharacteristics:
    """Reusable investment archetype — defaults only.

    Does not own metrics, peers, industry identity, or methodologies.
    """

    id: str
    name: str
    version: str
    status: CharacteristicLifecycle = CharacteristicLifecycle.ACTIVE
    description: str | None = None
    capital_intensity: CapitalIntensity | None = None
    cash_flow_profile: CashFlowProfile | None = None
    growth_profile: GrowthProfile | None = None
    earnings_stability: EarningsStability | None = None
    cyclicality: Cyclicality | None = None
    pricing_power: PricingPower | None = None
    regulatory_intensity: RegulatoryIntensity | None = None
    asset_intensity: AssetIntensity | None = None
    capital_allocation_style: CapitalAllocationStyle | None = None
    competitive_character: CompetitiveCharacter | None = None
    business_economics_notes: tuple[str, ...] = ()
    defaults: CharacteristicDefaults = CharacteristicDefaults()

    def __post_init__(self) -> None:
        identity_id = _normalize_id(self.id, field="id")
        name = self.name.strip()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        version = require_semver(self.version, field="version")
        description = (
            None if self.description is None else self.description.strip() or None
        )
        notes = tuple(
            n.strip() for n in self.business_economics_notes if n.strip()
        )
        object.__setattr__(self, "id", identity_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "business_economics_notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)


@dataclass(frozen=True, slots=True)
class IndustryProfile:
    """Industry facts shell that may reference InvestmentCharacteristics.

    Does not own methodology, metrics, or peer eligibility. Characteristic
    references are optional defaults only.
    """

    industry_id: str
    version: str
    characteristic_ids: tuple[str, ...] = ()
    status: CharacteristicLifecycle = CharacteristicLifecycle.ACTIVE
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        industry_id = _normalize_id(self.industry_id, field="industry_id")
        version = require_semver(self.version, field="version")
        char_ids = tuple(
            _normalize_id(c, field="characteristic_ids")
            for c in self.characteristic_ids
        )
        # Preserve order, drop duplicates
        seen: set[str] = set()
        unique: list[str] = []
        for cid in char_ids:
            if cid not in seen:
                seen.add(cid)
                unique.append(cid)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "industry_id", industry_id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "characteristic_ids", tuple(unique))
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.industry_id, self.version)
