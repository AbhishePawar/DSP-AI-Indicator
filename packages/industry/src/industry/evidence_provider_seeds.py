"""Illustrative EvidenceProvider implementations (C3.3 — no engine wiring)."""

from __future__ import annotations

from industry.enums import EvidenceAvailability
from industry.evidence_provider import (
    EvidenceProviderCapability,
    EvidenceProviderResult,
    EvidenceResolutionContext,
    IndustryEvidenceProvider,
)
from industry.evidence_provider_registry import IndustryEvidenceProviderRegistry
from industry.evidence_registry import IndustryEvidenceRegistry
from industry.evidence_seeds import seed_example_evidence_registries

__all__ = [
    "EXAMPLE_PROVIDER_IDS",
    "PlaceholderEvidenceProvider",
    "build_example_evidence_providers",
    "register_example_evidence_providers",
    "seed_example_evidence_provider_context",
]

EXAMPLE_PROVIDER_IDS: tuple[str, ...] = (
    "dsp.provider.decision_pack",
    "dsp.provider.fundamental",
    "dsp.provider.valuation",
    "dsp.provider.technical",
)

_PLACEHOLDER_NOTE = (
    "C3.3 illustrative provider — no analysis-engine integration; "
    "values are explicit placeholders only."
)


class PlaceholderEvidenceProvider:
    """Deterministic stub provider. Never calculates or interprets evidence."""

    def __init__(self, metadata: IndustryEvidenceProvider) -> None:
        self._meta = metadata
        self._supported = frozenset(metadata.evidence_ids)

    def provider_metadata(self) -> IndustryEvidenceProvider:
        return self._meta

    def supports(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> bool:
        return evidence_id.strip().lower() in self._supported

    def availability(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> EvidenceAvailability:
        if not self.supports(evidence_id, context):
            return EvidenceAvailability.NOT_APPLICABLE
        if context.extras and any(k == "force_unavailable" for k, _ in context.extras):
            return EvidenceAvailability.UNAVAILABLE
        if context.extras and any(
            k == "emit_placeholder" and v.lower() in {"1", "true", "yes"}
            for k, v in context.extras
        ):
            return EvidenceAvailability.AVAILABLE
        # Unwired sources are insufficient until real adapters exist.
        return EvidenceAvailability.INSUFFICIENT_DATA

    def resolve(
        self, evidence_id: str, context: EvidenceResolutionContext
    ) -> EvidenceProviderResult:
        eid = evidence_id.strip().lower()
        if not self.supports(eid, context):
            return EvidenceProviderResult(
                evidence_id=eid,
                provider_id=self._meta.id,
                availability=EvidenceAvailability.NOT_APPLICABLE,
                notes=("Evidence id is outside this provider's capabilities.",),
            )
        availability = self.availability(eid, context)
        if availability is EvidenceAvailability.UNAVAILABLE:
            return EvidenceProviderResult(
                evidence_id=eid,
                provider_id=self._meta.id,
                availability=EvidenceAvailability.UNAVAILABLE,
                notes=(_PLACEHOLDER_NOTE, "Forced unavailable via context."),
            )
        if context.extras and any(
            k == "emit_placeholder" and v.lower() in {"1", "true", "yes"}
            for k, v in context.extras
        ):
            return EvidenceProviderResult(
                evidence_id=eid,
                provider_id=self._meta.id,
                availability=EvidenceAvailability.AVAILABLE,
                value=f"placeholder:{eid}",
                is_placeholder=True,
                as_of=context.as_of,
                notes=(_PLACEHOLDER_NOTE,),
            )
        return EvidenceProviderResult(
            evidence_id=eid,
            provider_id=self._meta.id,
            availability=EvidenceAvailability.INSUFFICIENT_DATA,
            notes=(_PLACEHOLDER_NOTE,),
        )

    def resolve_many(
        self,
        evidence_ids: tuple[str, ...],
        context: EvidenceResolutionContext,
    ) -> tuple[EvidenceProviderResult, ...]:
        # Deterministic: preserve caller order, skip empties
        ordered = tuple(e.strip().lower() for e in evidence_ids if e.strip())
        return tuple(self.resolve(eid, context) for eid in ordered)


def build_example_evidence_providers() -> tuple[PlaceholderEvidenceProvider, ...]:
    return (
        PlaceholderEvidenceProvider(
            IndustryEvidenceProvider(
                id="dsp.provider.decision_pack",
                name="DecisionPack Provider",
                version="1.0.0",
                description=(
                    "Future adapter reading DecisionPack fields for evidence."
                ),
                capabilities=(
                    EvidenceProviderCapability(
                        evidence_id="dsp.evidence.roe_persistence",
                        notes=("May later map assurance/MoS-adjacent pack fields.",),
                    ),
                ),
                notes=("Placeholder only — does not read DecisionPack objects.",),
            )
        ),
        PlaceholderEvidenceProvider(
            IndustryEvidenceProvider(
                id="dsp.provider.fundamental",
                name="Fundamental Provider",
                version="1.0.0",
                capabilities=(
                    EvidenceProviderCapability(evidence_id="dsp.evidence.roe_persistence"),
                    EvidenceProviderCapability(evidence_id="dsp.evidence.nim_stability"),
                ),
                notes=("Placeholder only — no fundamental engine calls.",),
            )
        ),
        PlaceholderEvidenceProvider(
            IndustryEvidenceProvider(
                id="dsp.provider.valuation",
                name="Valuation Provider",
                version="1.0.0",
                capabilities=(
                    EvidenceProviderCapability(
                        evidence_id="dsp.evidence.regulated_cash_flow_visibility",
                    ),
                ),
                notes=("Placeholder only — no valuation engine calls.",),
            )
        ),
        PlaceholderEvidenceProvider(
            IndustryEvidenceProvider(
                id="dsp.provider.technical",
                name="Technical Provider",
                version="1.0.0",
                capabilities=(
                    EvidenceProviderCapability(
                        evidence_id="dsp.evidence.roe_persistence",
                        notes=(
                            "Illustrative overlap capability; routing policy later.",
                        ),
                    ),
                ),
                notes=("Placeholder only — no technical engine calls.",),
            )
        ),
    )


def register_example_evidence_providers(
    registry: IndustryEvidenceProviderRegistry,
) -> IndustryEvidenceProviderRegistry:
    for provider in build_example_evidence_providers():
        registry.register(provider)
    return registry


def seed_example_evidence_provider_context(
    evidence: IndustryEvidenceRegistry | None = None,
    providers: IndustryEvidenceProviderRegistry | None = None,
) -> tuple[IndustryEvidenceRegistry, IndustryEvidenceProviderRegistry]:
    """Seed evidence definitions + illustrative providers."""
    if evidence is None:
        _, evidence_reg = seed_example_evidence_registries()
    else:
        evidence_reg = evidence
    provider_reg = providers or IndustryEvidenceProviderRegistry(evidence_reg)
    register_example_evidence_providers(provider_reg)
    return evidence_reg, provider_reg
