"""Industry Evidence Provider tests (C3.3)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from industry import (
    EvidenceAvailability,
    EvidenceProviderCapability,
    EvidenceProviderResult,
    EvidenceResolutionContext,
    IndustryError,
    IndustryEvidenceProvider,
    IndustryEvidenceProviderRegistry,
    PlaceholderEvidenceProvider,
    build_example_evidence_providers,
    seed_example_evidence_provider_context,
    seed_example_evidence_registries,
)


class TestProviderModels:
    def test_duplicate_capability_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate provider capability"):
            IndustryEvidenceProvider(
                id="dsp.provider.x",
                name="X",
                version="1.0.0",
                capabilities=(
                    EvidenceProviderCapability(evidence_id="dsp.evidence.roe_persistence"),
                    EvidenceProviderCapability(evidence_id="dsp.evidence.roe_persistence"),
                ),
            )

    def test_available_requires_value(self) -> None:
        with pytest.raises(ValidationError, match="must include a value"):
            EvidenceProviderResult(
                evidence_id="dsp.evidence.roe_persistence",
                provider_id="dsp.provider.x",
                availability=EvidenceAvailability.AVAILABLE,
            )


class TestProviderRegistry:
    def test_register_lookup_resolve(self) -> None:
        evidence, providers = seed_example_evidence_provider_context()
        meta = providers.lookup_active("dsp.provider.fundamental")
        assert "dsp.evidence.nim_stability" in meta.evidence_ids
        ctx = EvidenceResolutionContext(instrument_key="HDFCBANK")
        result = providers.resolve(
            "dsp.provider.fundamental",
            "dsp.evidence.nim_stability",
            ctx,
        )
        assert result.availability is EvidenceAvailability.INSUFFICIENT_DATA
        assert result.value is None
        providers.validate()

    def test_availability_and_placeholder(self) -> None:
        _, providers = seed_example_evidence_provider_context()
        provider = providers.get_provider("dsp.provider.decision_pack")
        ctx = EvidenceResolutionContext(
            instrument_key="ICICIBANK",
            extras=(("emit_placeholder", "true"),),
        )
        assert (
            provider.availability("dsp.evidence.roe_persistence", ctx)
            is EvidenceAvailability.AVAILABLE
        )
        result = provider.resolve("dsp.evidence.roe_persistence", ctx)
        assert result.availability is EvidenceAvailability.AVAILABLE
        assert result.is_placeholder is True
        assert str(result.value).startswith("placeholder:")

    def test_not_applicable(self) -> None:
        _, providers = seed_example_evidence_provider_context()
        result = providers.resolve(
            "dsp.provider.valuation",
            "dsp.evidence.nim_stability",
            EvidenceResolutionContext(instrument_key="NTPC"),
        )
        assert result.availability is EvidenceAvailability.NOT_APPLICABLE

    def test_resolve_many_deterministic(self) -> None:
        _, providers = seed_example_evidence_provider_context()
        provider = providers.get_provider("dsp.provider.fundamental")
        ctx = EvidenceResolutionContext(instrument_key="HDFCBANK")
        results = provider.resolve_many(
            ("dsp.evidence.nim_stability", "dsp.evidence.roe_persistence"),
            ctx,
        )
        assert [r.evidence_id for r in results] == [
            "dsp.evidence.nim_stability",
            "dsp.evidence.roe_persistence",
        ]

    def test_unsupported_evidence_ref_rejected(self) -> None:
        evidence, _ = seed_example_evidence_registries()
        registry = IndustryEvidenceProviderRegistry(evidence)
        bad = PlaceholderEvidenceProvider(
            IndustryEvidenceProvider(
                id="dsp.provider.bad",
                name="Bad",
                version="1.0.0",
                capabilities=(
                    EvidenceProviderCapability(
                        evidence_id="dsp.evidence.does_not_exist"
                    ),
                ),
            )
        )
        with pytest.raises(IndustryError, match="unsupported evidence"):
            registry.register(bad)

    def test_duplicate_provider_rejected(self) -> None:
        _, providers = seed_example_evidence_provider_context()
        twin = build_example_evidence_providers()[0]
        with pytest.raises(IndustryError, match="duplicate"):
            providers.register(twin)
