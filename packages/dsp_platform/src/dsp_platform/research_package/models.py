"""Private canonical ResearchPackage models.

This object is server-side research evidence for a future private prompt
generator. It is not an HTTP DTO, browser payload, or PublicDecisionPack field.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import Any

from dsp_platform.external_evidence.models import ValidatedExternalEvidencePackage

__all__ = [
    "ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE",
    "PRIVATE_FIELD_NAMES",
    "RESEARCH_PACKAGE_SCHEMA_VERSION",
    "SOURCE_PIPELINE_COMPOSE_INTELLIGENCE",
    "PackageSection",
    "ResearchPackage",
    "ResearchPackageSourceError",
    "SectionStatus",
    "contains_private_fields",
    "freeze_mapping",
    "strip_private_fields",
]

RESEARCH_PACKAGE_SCHEMA_VERSION = "dsp.research_package.v1"
SOURCE_PIPELINE_COMPOSE_INTELLIGENCE = "compose_intelligence"

ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE = (
    "No canonical DSP entry/exit engine is present. "
    "entry_price, entry_zone, exit_price, and target_price are not implemented."
)

# Fields that must never appear on a ResearchPackage (AI/provider internals).
PRIVATE_FIELD_NAMES = frozenset(
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


class ResearchPackageSourceError(TypeError):
    """Raised when ResearchPackage is built from a non-composition source."""


class SectionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_IMPLEMENTED = "not_implemented"


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """Deep-freeze a mapping into a read-only MappingProxyType tree."""
    if value is None:
        return None

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, list):
            return tuple(_freeze(v) for v in obj)
        if isinstance(obj, tuple):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


def strip_private_fields(obj: Any) -> Any:
    """Drop provider/AI private keys if they appear in a mapping tree."""
    if isinstance(obj, Mapping):
        return {
            str(k): strip_private_fields(v)
            for k, v in obj.items()
            if str(k) not in PRIVATE_FIELD_NAMES
        }
    if isinstance(obj, list):
        return [strip_private_fields(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(strip_private_fields(v) for v in obj)
    return obj


def contains_private_fields(obj: Any) -> list[str]:
    """Return private field names found anywhere in a mapping tree."""
    found: list[str] = []

    def _walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                name = str(key)
                if name in PRIVATE_FIELD_NAMES:
                    found.append(name)
                _walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _walk(item)

    _walk(obj)
    return found


def _plain(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


@dataclass(frozen=True, slots=True)
class PackageSection:
    """One ResearchPackage section — pass-through payload only."""

    name: str
    status: str
    available: bool
    payload: Mapping[str, Any] | None
    provenance: Mapping[str, Any]
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "available": self.available,
            "payload": _plain(self.payload) if self.payload is not None else None,
            "provenance": _plain(self.provenance),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ResearchPackage:
    """Private immutable aggregate of compose_intelligence outputs.

    ``to_dict`` exists for tests and internal inspection only. It is not a
    public API contract and must not be returned to a client.
    """

    schema_version: str
    methodology_version: str
    source_pipeline: str
    identity: PackageSection
    market_data: PackageSection
    financial_statements: PackageSection
    financials: PackageSection
    valuation: PackageSection
    economic_moat: PackageSection
    management_quality: PackageSection
    financial_strength: PackageSection
    earnings_quality: PackageSection
    growth_quality: PackageSection
    business_quality: PackageSection
    risk: PackageSection
    investment_recommendation: PackageSection
    investment_committee: PackageSection
    buffett_authority: PackageSection
    evidence: PackageSection
    entry_exit: PackageSection
    limitations: tuple[str, ...]
    errors: tuple[str, ...]
    pipeline_ok: bool
    external_evidence: ValidatedExternalEvidencePackage | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "methodology_version": self.methodology_version,
            "source_pipeline": self.source_pipeline,
            "identity": self.identity.to_dict(),
            "market_data": self.market_data.to_dict(),
            "financial_statements": self.financial_statements.to_dict(),
            "financials": self.financials.to_dict(),
            "valuation": self.valuation.to_dict(),
            "economic_moat": self.economic_moat.to_dict(),
            "management_quality": self.management_quality.to_dict(),
            "financial_strength": self.financial_strength.to_dict(),
            "earnings_quality": self.earnings_quality.to_dict(),
            "growth_quality": self.growth_quality.to_dict(),
            "business_quality": self.business_quality.to_dict(),
            "risk": self.risk.to_dict(),
            "investment_recommendation": self.investment_recommendation.to_dict(),
            "investment_committee": self.investment_committee.to_dict(),
            "buffett_authority": self.buffett_authority.to_dict(),
            "evidence": self.evidence.to_dict(),
            "entry_exit": self.entry_exit.to_dict(),
            "limitations": list(self.limitations),
            "errors": list(self.errors),
            "pipeline_ok": self.pipeline_ok,
            "external_evidence": (
                None
                if self.external_evidence is None
                else self.external_evidence.to_prompt_payload()
            ),
        }
