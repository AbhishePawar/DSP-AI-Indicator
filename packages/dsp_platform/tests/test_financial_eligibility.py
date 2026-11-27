"""Financial research evidence eligibility regression tests."""

from dataclasses import replace

import pytest

from dsp_platform.research_retrieval.financial_eligibility import (
    financial_evidence_rejection_reason,
)

from dsp_platform.research_retrieval.models import (
    EvidenceFreshness,
    EvidenceStatus,
    ProvenanceRecord,
    ResearchEvidenceRecord,
    SourceTier,
)


@pytest.fixture
def evidence():

    provenance = ProvenanceRecord(
        source="official_company_filing",
        source_tier=SourceTier.PRIMARY,
        provider="public_research",
        retrieved_at="2026-11-27T10:00:00+00:00",
        canonical_url="https://www.infosys.com/report",
        original_url="https://www.infosys.com/report",
        publisher="Infosys",
        published_at="2026-06-01",
        effective_period="FY2026",
        content_hash="a" * 64,
    )

    return ResearchEvidenceRecord(
        evidence_id="ev_test",
        ticker="INFY",
        claim="Reported revenue",
        status=EvidenceStatus.VERIFIED,
        provenance=provenance,
        freshness=EvidenceFreshness.CURRENT,
        metric_name="revenue",
        metric_value=100000.0,
        units="INR crore",
        raw_excerpt="Revenue INR crore 100000",
    )


def check(record, **overrides):

    expected = {
        "ticker": "INFY",
        "metric_name": "revenue",
        "period": "FY2026",
        "units": "INR crore",
    }

    expected.update(overrides)

    return financial_evidence_rejection_reason(
        record, **expected
    )


def test_valid_primary_evidence(evidence):
    assert check(evidence) is None


def test_normalized_identity(evidence):
    assert check(
        evidence, ticker=" infy "
    ) is None


@pytest.mark.parametrize(
    "status",
    [
        EvidenceStatus.UNVERIFIED,
        EvidenceStatus.REJECTED,
        EvidenceStatus.STALE,
        EvidenceStatus.CONFLICTING,
        EvidenceStatus.UNAVAILABLE,
    ],
)
def test_unverified_status_rejected(evidence, status):

    item = replace(evidence, status=status)

    assert check(item) == "evidence_not_verified"


def test_secondary_source_rejected(evidence):

    item = replace(
        evidence,
        provenance=replace(
            evidence.provenance,
            source_tier=SourceTier.SECONDARY,
        ),
    )

    assert check(item) == "primary_source_required"


@pytest.mark.parametrize(
    "freshness",
    [
        EvidenceFreshness.STALE,
        EvidenceFreshness.UNKNOWN,
        EvidenceFreshness.HISTORICAL,
    ],
)
def test_invalid_freshness(evidence, freshness):

    item = replace(evidence, freshness=freshness)

    assert check(item) == "freshness_not_verified"


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("ticker", "TCS", "ticker_mismatch"),
        ("metric_name", "net_income", "metric_mismatch"),
        ("units", "USD million", "units_mismatch"),
        ("metric_value", None, "missing_value"),
        ("metric_value", True, "invalid_value"),
        ("metric_value", float("nan"), "non_finite_value"),
        ("metric_value", float("inf"), "non_finite_value"),
        ("conflicts_with", ("ev_other",), "conflicting_evidence"),
        ("raw_excerpt", "", "missing_grounded_excerpt"),
        ("rejection_reason", "invalid", "rejected_evidence"),
    ],
)
def test_invalid_evidence(evidence, field, value, reason):

    item = replace(evidence, **{field: value})

    assert check(item) == reason


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("effective_period", "FY2025", "period_mismatch"),
        ("canonical_url", "", "missing_source_url"),
        ("content_hash", None, "missing_document_hash"),
        ("published_at", None, "missing_publication_date"),
    ],
)
def test_invalid_provenance(evidence, field, value, reason):

    item = replace(
        evidence,
        provenance=replace(
            evidence.provenance,
            **{field: value}
        ),
    )

    assert check(item) == reason


def test_zero_is_not_missing(evidence):

    assert check(
        replace(evidence, metric_value=0.0)
    ) is None


def test_negative_value_can_be_valid(evidence):

    assert check(
        replace(evidence, metric_value=-100.0)
    ) is None


def test_missing_expected_identity(evidence):

    assert check(
        evidence, ticker=""
    ) == "missing_expected_identity"
