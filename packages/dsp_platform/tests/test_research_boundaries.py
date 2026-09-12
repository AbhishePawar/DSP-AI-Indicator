from datetime import date

import pytest

from dsp_platform.research_assembly import (
    EvidenceJudge,
    EvidenceStatus,
    InMemoryShareCountPort,
    ShareCount,
    SourceEvidence,
)


def test_evidence_judge_verifies_allowed_primary_source() -> None:
    evidence = SourceEvidence(
        evidence_id="sec-1",
        url="https://www.sec.gov/Archives/edgar/data/1/10-k.htm",
        title="Annual filing",
        publisher="SEC",
        claim="Revenue was reported for the period.",
    )

    verified = EvidenceJudge().verify(evidence)

    assert verified.status is EvidenceStatus.VERIFIED
    assert verified.to_dict()["evidence_id"] == "sec-1"


def test_evidence_judge_rejects_secondary_source() -> None:
    evidence = SourceEvidence(
        evidence_id="blog-1",
        url="https://example.com/company-analysis",
        title="Analysis",
        publisher="Research blog",
        claim="The company may grow rapidly.",
    )

    assert EvidenceJudge().verify(evidence).status is EvidenceStatus.REJECTED


def test_share_count_port_is_independent_and_normalizes_ticker() -> None:
    row = ShareCount("TCS", 3_600_000_000, date(2026, 3, 31), "issuer filing")
    port = InMemoryShareCountPort((row,))

    assert port.get_outstanding_shares(" tcs ") == row
    assert port.get_outstanding_shares("INFY") is None


def test_share_count_rejects_non_positive_values() -> None:
    with pytest.raises(ValueError, match="positive finite"):
        ShareCount("TCS", 0, date(2026, 3, 31), "issuer filing")
