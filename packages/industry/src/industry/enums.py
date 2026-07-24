"""Enumerations for Industry Identity, Characteristics, and Methodology."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AssetIntensity",
    "CapitalAllocationStyle",
    "CapitalIntensity",
    "CashFlowProfile",
    "CharacteristicLifecycle",
    "ComparisonDimension",
    "ComparisonDimensionHint",
    "CompetitiveCharacter",
    "Cyclicality",
    "EarningsStability",
    "GrowthProfile",
    "IdentityLifecycle",
    "MappingStatus",
    "MergeSource",
    "MetricImportance",
    "MethodologyLifecycle",
    "PeerEligibilityStatus",
    "GroupEligibilityStatus",
    "PeerUse",
    "PricingPower",
    "RegulatoryIntensity",
    "TaxonomySource",
    "ValuationPhilosophyHint",
    "EvidenceCategory",
    "EvidenceLifecycle",
    "MetricAvailability",
    "MetricUnit",
    "ApplicabilityLevel",
    "MissingEvidencePolicy",
    "EvidenceAvailability",
    "EvidenceBundleStatus",
    "EvidenceObservationCategory",
    "EvidenceObservationConfidence",
    "EvidenceObservationSeverity",
]


class TaxonomySource(StrEnum):
    """External classification systems. DSP never treats these as identity."""

    NSE = "nse"
    BSE = "bse"
    GICS = "gics"
    ICB = "icb"
    NAICS = "naics"
    CUSTOM = "custom"


class IdentityLifecycle(StrEnum):
    """Lifecycle of a DSP IndustryIdentity."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class MappingStatus(StrEnum):
    """Lifecycle of an external→DSP classification mapping."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"


class CharacteristicLifecycle(StrEnum):
    """Lifecycle of an InvestmentCharacteristics archetype."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class MethodologyLifecycle(StrEnum):
    """Lifecycle of an IndustryMethodology."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class MergeSource(StrEnum):
    """Provenance for a resolved methodology field — never silent."""

    METHODOLOGY = "methodology"
    CHARACTERISTICS = "characteristics"
    SYSTEM = "system"


class MetricImportance(StrEnum):
    """Placeholder importance for MetricApplicability (no calculations)."""

    CORE = "core"
    SECONDARY = "secondary"
    CONTEXTUAL = "contextual"
    NOT_APPLICABLE = "not_applicable"


class PeerUse(StrEnum):
    """Whether a metric may be used in future peer comparison."""

    ALLOWED = "allowed"
    CAUTION = "caution"
    FORBIDDEN = "forbidden"


class ComparisonDimension(StrEnum):
    """Unweighted comparison axes owned by IndustryMethodology."""

    QUALITY = "quality"
    GROWTH = "growth"
    FINANCIAL_STRENGTH = "financial_strength"
    VALUATION = "valuation"
    CAPITAL_ALLOCATION = "capital_allocation"
    DECISION_ROBUSTNESS = "decision_robustness"
    RISK = "risk"
    PREDICTABILITY = "predictability"
    EFFICIENCY = "efficiency"
    PROFITABILITY = "profitability"


class PeerEligibilityStatus(StrEnum):
    """Structural peer eligibility — not a score or rank."""

    DIRECT_PEER = "direct_peer"
    RELATED_PEER = "related_peer"
    LIMITED_COMPARISON = "limited_comparison"
    NOT_COMPARABLE = "not_comparable"
    INSUFFICIENT_DATA = "insufficient_data"
    UNKNOWN = "unknown"


class GroupEligibilityStatus(StrEnum):
    """Aggregate eligibility for a multi-instrument set."""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    MIXED = "mixed"


class CapitalIntensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CashFlowProfile(StrEnum):
    STABLE = "stable"
    CYCLICAL = "cyclical"
    VOLATILE = "volatile"
    PROJECT = "project"


class GrowthProfile(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXPONENTIAL = "exponential"


class EarningsStability(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class Cyclicality(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    STRUCTURAL = "structural"


class PricingPower(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class RegulatoryIntensity(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AssetIntensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CapitalAllocationStyle(StrEnum):
    REINVEST = "reinvest"
    DISTRIBUTE = "distribute"
    BALANCED = "balanced"
    OPPORTUNISTIC = "opportunistic"


class CompetitiveCharacter(StrEnum):
    COMMODITY = "commodity"
    FRANCHISE = "franchise"
    REGULATED = "regulated"
    NETWORK = "network"
    NICHE = "niche"


class ValuationPhilosophyHint(StrEnum):
    """Soft valuation preference hints — not engine method execution."""

    INCOME = "income"
    ASSET = "asset"
    EARNINGS = "earnings"
    CASH_FLOW = "cash_flow"
    HYBRID = "hybrid"


class ComparisonDimensionHint(StrEnum):
    """Soft comparison-dimension emphasis — not weights or scores."""

    QUALITY = "quality"
    GROWTH = "growth"
    VALUATION = "valuation"
    PREDICTABILITY = "predictability"
    CAPITAL_ALLOCATION = "capital_allocation"
    FINANCIAL_STRENGTH = "financial_strength"
    EFFICIENCY = "efficiency"
    RISK = "risk"


class EvidenceCategory(StrEnum):
    """Controlled vocabulary for industry evidence definitions."""

    FINANCIAL = "financial"
    BUSINESS_MODEL = "business_model"
    INDUSTRY_KPI = "industry_kpi"
    MANAGEMENT = "management"
    REGULATORY = "regulatory"
    CAPITAL_ALLOCATION = "capital_allocation"
    COMPETITIVE_POSITION = "competitive_position"
    ECONOMIC = "economic"
    MARKET_STRUCTURE = "market_structure"
    RISK = "risk"
    ESG = "esg"


class EvidenceLifecycle(StrEnum):
    """Lifecycle for IndustryMetricDefinition and IndustryEvidenceDefinition."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class MetricAvailability(StrEnum):
    """Whether a metric reading can be produced today (metadata only)."""

    AVAILABLE_TODAY = "available_today"
    DERIVABLE = "derivable"
    REQUIRES_NEW_DATA = "requires_new_data"
    REQUIRES_NEW_ENGINE = "requires_new_engine"


class MetricUnit(StrEnum):
    """Unit metadata for IndustryMetricDefinition — not a calculator."""

    RATIO = "ratio"
    PERCENT = "percent"
    CURRENCY = "currency"
    COUNT = "count"
    YEARS = "years"
    BASIS_POINTS = "basis_points"
    OTHER = "other"


class ApplicabilityLevel(StrEnum):
    """How an evidence definition applies under a methodology."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    UNSUPPORTED = "unsupported"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class MissingEvidencePolicy(StrEnum):
    """What future consumers should do when REQUIRED evidence is absent."""

    RECORD_GAP = "record_gap"
    DEGRADE = "degrade"
    HARD_FAIL = "hard_fail"


class EvidenceAvailability(StrEnum):
    """Resolution availability for an evidence provider result."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"
    INSUFFICIENT_DATA = "insufficient_data"
    ERROR = "error"


class EvidenceBundleStatus(StrEnum):
    """Assembly completeness of an EvidenceBundle — not a score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    EMPTY = "empty"


class EvidenceObservationSeverity(StrEnum):
    """Qualitative severity for an evidence observation — not a score."""

    INFO = "info"
    NOTICE = "notice"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"


class EvidenceObservationCategory(StrEnum):
    """Observation theme — interpretive labeling only, never a rank."""

    AVAILABILITY = "availability"
    METHODOLOGY = "methodology"
    STRUCTURAL = "structural"
    QUALITY = "quality"
    RISK = "risk"
    GROWTH = "growth"
    VALUATION = "valuation"
    LIMITATION = "limitation"
    OTHER = "other"


class EvidenceObservationConfidence(StrEnum):
    """Qualitative confidence label — not a numeric score."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
