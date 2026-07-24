"""Industry Evidence Registry tests (C3.1 — definitions only)."""

from __future__ import annotations

import pytest
from core.exceptions import ValidationError

from industry import (
    EvidenceCategory,
    EvidenceLifecycle,
    EvidenceProviderRef,
    EvidenceSnapshotRef,
    EvidenceVersion,
    IndustryError,
    IndustryEvidenceDefinition,
    IndustryEvidenceRegistry,
    IndustryMetricDefinition,
    IndustryMetricRegistry,
    MetricUnit,
    compare_semver,
    seed_example_evidence_registries,
)


def _metric(
    mid: str = "dsp.metric.demo",
    *,
    version: str = "1.0.0",
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE,
) -> IndustryMetricDefinition:
    return IndustryMetricDefinition(
        id=mid,
        name=mid,
        version=version,
        category=EvidenceCategory.FINANCIAL,
        unit=MetricUnit.RATIO,
        status=status,
    )


def _evidence(
    eid: str = "dsp.evidence.demo",
    *,
    version: str = "1.0.0",
    status: EvidenceLifecycle = EvidenceLifecycle.ACTIVE,
    related: tuple[str, ...] = (),
) -> IndustryEvidenceDefinition:
    return IndustryEvidenceDefinition(
        id=eid,
        name=eid,
        version=version,
        category=EvidenceCategory.FINANCIAL,
        purpose="Describe a financial pattern without declaring preference.",
        status=status,
        related_metric_ids=related,
    )


class TestModels:
    def test_immutable_and_semver(self) -> None:
        m = _metric("DSP.Metric.ROE")
        assert m.id == "dsp.metric.roe"
        assert EvidenceVersion("1.2.3").value == "1.2.3"
        with pytest.raises(ValidationError, match="semantic version"):
            IndustryMetricDefinition(
                id="dsp.metric.x",
                name="X",
                version="1.0",
                category=EvidenceCategory.FINANCIAL,
            )

    def test_forbidden_language(self) -> None:
        with pytest.raises(ValidationError, match="forbidden"):
            IndustryEvidenceDefinition(
                id="dsp.evidence.bad",
                name="Bad",
                version="1.0.0",
                category=EvidenceCategory.FINANCIAL,
                purpose="Identify the best company in the peer set.",
            )

    def test_snapshot_ref_definition_only(self) -> None:
        ref = EvidenceSnapshotRef(
            snapshot_id="snap.1",
            methodology_id="dsp.methodology.commercial_banking",
            methodology_version="1.0.0",
            digest="abc123",
        )
        assert ref.digest == "abc123"


class TestMetricRegistry:
    def test_register_lookup_semver_active(self) -> None:
        reg = IndustryMetricRegistry()
        reg.register(_metric(version="1.9.0"))
        reg.register(_metric(version="1.10.0"))
        assert compare_semver("1.10.0", "1.9.0") == 1
        assert reg.lookup_active("dsp.metric.demo").version == "1.10.0"
        assert reg.lookup("dsp.metric.demo", version="1.9.0").version == "1.9.0"

    def test_duplicate_rejected(self) -> None:
        reg = IndustryMetricRegistry()
        reg.register(_metric())
        with pytest.raises(IndustryError, match="duplicate"):
            reg.register(
                IndustryMetricDefinition(
                    id="dsp.metric.demo",
                    name="Other",
                    version="1.0.0",
                    category=EvidenceCategory.RISK,
                )
            )

    def test_deprecate(self) -> None:
        reg = IndustryMetricRegistry()
        reg.register(_metric())
        reg.deprecate("dsp.metric.demo", version="1.0.0")
        with pytest.raises(IndustryError, match="no active"):
            reg.lookup_active("dsp.metric.demo")


class TestEvidenceRegistry:
    def test_register_lookup_validate(self) -> None:
        metrics = IndustryMetricRegistry()
        metrics.register(_metric("dsp.metric.roe"))
        evidence = IndustryEvidenceRegistry(metrics)
        evidence.register(
            _evidence(related=("dsp.metric.roe",), version="1.0.0")
        )
        evidence.register(
            _evidence(related=("dsp.metric.roe",), version="2.0.0")
        )
        assert evidence.lookup_active("dsp.evidence.demo").version == "2.0.0"
        evidence.validate()

    def test_unknown_metric_ref_rejected(self) -> None:
        metrics = IndustryMetricRegistry()
        evidence = IndustryEvidenceRegistry(metrics)
        with pytest.raises(IndustryError, match="unknown related metric"):
            evidence.register(_evidence(related=("dsp.metric.missing",)))

    def test_metric_registry_required_for_refs(self) -> None:
        evidence = IndustryEvidenceRegistry()
        with pytest.raises(IndustryError, match="metric registry required"):
            evidence.register(_evidence(related=("dsp.metric.roe",)))

    def test_examples_banking_and_utilities(self) -> None:
        metrics, evidence = seed_example_evidence_registries()
        metrics.validate()
        evidence.validate()
        assert evidence.contains("dsp.evidence.nim_stability")
        assert evidence.contains("dsp.evidence.regulated_cash_flow_visibility")
        banking = evidence.lookup_active("dsp.evidence.nim_stability")
        assert "dsp.industry.commercial_banking" in banking.supported_industry_ids
        utilities = evidence.lookup_active(
            "dsp.evidence.regulated_cash_flow_visibility"
        )
        assert "dsp.industry.electric_utilities" in utilities.supported_industry_ids
        assert EvidenceProviderRef(provider_id="dsp.provider.banking_kpi")
