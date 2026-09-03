"""Validated external research evidence — input to future AI interpretation.

This is not a DSP calculation port, not a vendor adapter, and not a public
report DTO. Numerical facts here remain supporting evidence until a separate
approved DSP ingest exists.

Evidence record ≠ canonical calculation input.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

__all__ = [
    "CANONICAL_CALCULATION_FACT_IDS",
    "CURRENT_OUTSTANDING_FACT_IDS",
    "EXTERNAL_EVIDENCE_SCHEMA_VERSION",
    "PRIVATE_EVIDENCE_FIELD_NAMES",
    "SEARCH_SNIPPET_SOURCE_TYPES",
    "WEIGHTED_AVERAGE_SHARES_FACT_IDS",
    "EvidenceKind",
    "EvidenceQuality",
    "EvidenceValidationStatus",
    "ExternalEvidenceIdentity",
    "ExternalEvidenceRecord",
    "ExternalEvidenceValidationError",
    "QualitativeEvidenceTopic",
    "SourceTier",
    "SourceType",
    "ValidatedExternalEvidencePackage",
]

EXTERNAL_EVIDENCE_SCHEMA_VERSION = "dsp.validated_external_evidence.v1"

# Reuse the ResearchPackage private-field contract so evidence objects cannot
# carry prompts, provider routing, or secrets.
PRIVATE_EVIDENCE_FIELD_NAMES = frozenset(
    {
        "api_key",
        "api_keys",
        "chain_of_thought",
        "completion_tokens",
        "cot",
        "cost",
        "ai_cost",
        "model",
        "model_name",
        "private_prompt",
        "prompt",
        "prompt_tokens",
        "provider",
        "provider_id",
        "raw_ai_response",
        "raw_response",
        "raw_tool_payloads",
        "routing",
        "routing_reason",
        "routing_reasons",
        "routing_tier",
        "secret",
        "secrets",
        "system_prompt",
        "token_count",
        "tokens",
        "tool_calls",
    }
)

CURRENT_OUTSTANDING_FACT_IDS = frozenset(
    {
        "current_outstanding",
        "current_shares_outstanding",
        "current_shares",
        "shares_outstanding",
        "share_count",
    }
)

WEIGHTED_AVERAGE_SHARES_FACT_IDS = frozenset(
    {
        "weighted_average_shares",
        "weighted_average_shares_basic",
        "weighted_average_shares_diluted",
        "weighted_shares",
        "was",
        "diluted_shares",
        "basic_shares",
    }
)

CANONICAL_CALCULATION_FACT_IDS = frozenset(
    {
        "revenue",
        "operating_income",
        "net_income",
        "eps",
        "debt",
        "cash",
        "fcf",
        "free_cash_flow",
        "valuation_input",
        "intrinsic_value",
        "margin_of_safety",
        "dsp_score",
        "recommendation",
        *CURRENT_OUTSTANDING_FACT_IDS,
        *WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    }
)

SEARCH_SNIPPET_SOURCE_TYPES = frozenset(
    {
        "search_snippet",
        "serp_snippet",
        "search_result",
        "search_result_snippet",
    }
)


class ExternalEvidenceValidationError(ValueError):
    """Raised when external evidence fails DSP structural validation."""


class EvidenceKind(StrEnum):
    NUMERICAL = "numerical"
    QUALITATIVE = "qualitative"


class EvidenceValidationStatus(StrEnum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REJECTED = "rejected"


class SourceTier(StrEnum):
    """Established source-authority policy. Tier 3 is discovery only."""

    TIER_1_PRIMARY = "TIER_1_PRIMARY"
    TIER_2_SECONDARY = "TIER_2_SECONDARY"
    TIER_3_DISCOVERY = "TIER_3_DISCOVERY"
    TIER_4_NEWS_CONTEXT = "TIER_4_NEWS_CONTEXT"


class SourceType(StrEnum):
    FILING = "filing"
    TRANSCRIPT = "transcript"
    PRESS_RELEASE = "press_release"
    REGULATORY = "regulatory"
    COMPANY_WEBSITE = "company_website"
    NEWS = "news"
    ANALYST_REPORT = "analyst_report"
    INDUSTRY_REPORT = "industry_report"
    COURT_RECORD = "court_record"
    EXCHANGE_NOTICE = "exchange_notice"
    SEARCH_SNIPPET = "search_snippet"
    SERP_SNIPPET = "serp_snippet"
    SEARCH_RESULT = "search_result"
    SEARCH_RESULT_SNIPPET = "search_result_snippet"


class EvidenceQuality(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class QualitativeEvidenceTopic(StrEnum):
    MANAGEMENT_COMMENTARY = "management_commentary"
    MANAGEMENT_GUIDANCE = "management_guidance"
    COMPETITIVE_LANDSCAPE = "competitive_landscape"
    INDUSTRY_DEVELOPMENTS = "industry_developments"
    MARKET_SHARE = "market_share"
    REGULATORY_DEVELOPMENTS = "regulatory_developments"
    LITIGATION = "litigation"
    GOVERNANCE = "governance"
    RELATED_PARTY_TRANSACTIONS = "related_party_transactions"
    ACQUISITIONS = "acquisitions"
    CAPACITY_EXPANSION = "capacity_expansion"
    NEW_PRODUCTS = "new_products"
    GEOGRAPHIC_EXPANSION = "geographic_expansion"
    BRAND = "brand"
    NETWORK_EFFECTS = "network_effects"
    SWITCHING_COSTS = "switching_costs"
    COST_ADVANTAGE = "cost_advantage"
    INTANGIBLE_ASSETS = "intangible_assets"
    EFFICIENT_SCALE = "efficient_scale"
    DISTRIBUTION_ADVANTAGE = "distribution_advantage"
    PRICING_POWER = "pricing_power"
    CAPITAL_ALLOCATION = "capital_allocation"
    CORPORATE_DEVELOPMENTS = "corporate_developments"
    OTHER_QUALITATIVE = "other_qualitative"


@dataclass(frozen=True, slots=True)
class ExternalEvidenceIdentity:
    """Canonical company binding for one evidence record.

    Matching is exact on populated identity fields. Company names are stored
    but never used for fuzzy matching. Exchange suffixes are not invented.
    """

    symbol: str
    exchange: str | None = None
    isin: str | None = None
    company_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "isin": self.isin,
            "company_name": self.company_name,
        }


@dataclass(frozen=True, slots=True)
class ExternalEvidenceRecord:
    """One structurally typed external research fact.

    ``may_influence_calculation`` defaults to False and cannot become True
    at this layer. Reserved financial/share-count fields may exist only as
    supporting evidence; they do not populate DSP ports.
    """

    fact_id: str
    identity: ExternalEvidenceIdentity
    evidence_kind: EvidenceKind
    source_url: str
    source_type: SourceType
    source_tier: SourceTier
    retrieved_at: datetime
    evidence_quality: EvidenceQuality
    validation_status: EvidenceValidationStatus
    evidence_reference: str
    may_influence_calculation: bool = False
    numeric_value: float | None = None
    unit: str | None = None
    text_value: str | None = None
    as_of: date | None = None
    publication_date: date | None = None
    topic: QualitativeEvidenceTopic | None = None
    claimed_dsp_field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "identity": self.identity.to_dict(),
            "symbol": self.identity.symbol,
            "exchange": self.identity.exchange,
            "isin": self.identity.isin,
            "evidence_kind": self.evidence_kind.value,
            "numeric_value": self.numeric_value,
            "unit": self.unit,
            "text_value": self.text_value,
            "as_of": self.as_of.isoformat() if self.as_of is not None else None,
            "publication_date": (
                self.publication_date.isoformat()
                if self.publication_date is not None
                else None
            ),
            "source_url": self.source_url,
            "source_type": self.source_type.value,
            "source_tier": self.source_tier.value,
            "evidence_reference": self.evidence_reference,
            "retrieved_at": self.retrieved_at.isoformat(),
            "evidence_quality": self.evidence_quality.value,
            "validation_status": self.validation_status.value,
            "may_influence_calculation": self.may_influence_calculation,
            "topic": self.topic.value if self.topic is not None else None,
            "claimed_dsp_field": self.claimed_dsp_field,
        }


@dataclass(frozen=True, slots=True)
class ValidatedExternalEvidencePackage:
    """Immutable collection of structurally validated external evidence.

    Contains only ``validation_status=validated`` records. Candidate and
    rejected evidence cannot enter this package. The package is never a
    share-count port, valuation input, or recommendation input.
    """

    subject: ExternalEvidenceIdentity
    records: tuple[ExternalEvidenceRecord, ...]
    schema_version: str = EXTERNAL_EVIDENCE_SCHEMA_VERSION

    def canonical_calculation_inputs(self) -> Mapping[str, Any]:
        """External evidence never yields DSP calculation inputs."""
        return MappingProxyType({})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "subject": self.subject.to_dict(),
            "record_count": len(self.records),
            "records": [row.to_dict() for row in self.records],
            "may_influence_calculation": False,
            "calculation_inputs": {},
        }

    def to_prompt_payload(self) -> dict[str, Any]:
        """Safe payload for PrivateResearchPrompt — no secrets or routing."""
        return {
            "schema_version": self.schema_version,
            "handling": "supporting_research_context_not_dsp_calculation_input",
            "may_influence_calculation": False,
            "subject": self.subject.to_dict(),
            "records": [row.to_dict() for row in self.records],
        }
