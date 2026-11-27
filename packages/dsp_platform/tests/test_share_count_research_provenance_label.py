"""Share-count provenance must preserve financial authority boundaries."""

from dsp_platform.investment_provenance.builder import source_evidence_from_trace

_BASE = {
    "authenticated": True,
    "ticker": "TCS",
    "shares_outstanding": 3_618_087_518.0,
    "statement_provenance": {"provider_id": "stmt"},
    "quote_provenance": {"provider_id": "quote"},
}


def test_research_fallback_shares_are_labelled_unverified_for_g2():
    trace = {
        **_BASE,
        "share_count_provenance": {
            "retrieval": "ai_research_fallback",
            "provider_id": "ai_research_fallback",
            "verified": False,
            "evidence_class": "public_research_unverified_for_g2",
        },
    }

    out = source_evidence_from_trace(trace)

    assert out["shares_source"] == "research_fallback"
    assert out["share_count_verified"] is False
    assert out["shares_evidence_class"] == "public_research_unverified_for_g2"


def test_quote_alone_does_not_establish_share_count_authority():
    out = source_evidence_from_trace(_BASE)

    assert out["shares_source"] is None
    assert out["share_count_verified"] is False
    assert out["shares_evidence_class"] is None


def test_verified_statement_share_count_retains_authority():
    out = source_evidence_from_trace({
        **_BASE,
        "share_count_provenance": {
            "source": "authenticated_financial_statement",
            "verified": True,
            "as_of": "2026-03-31",
        },
    })

    assert out["shares_source"] == "verified_source"
    assert out["share_count_verified"] is True
    assert out["share_count_source"] == "authenticated_financial_statement"


def test_unverified_share_count_is_not_promoted():
    out = source_evidence_from_trace({
        **_BASE,
        "share_count_provenance": {
            "source": "unverified_source",
            "verified": False,
        },
    })

    assert out["shares_source"] == "unverified_source"
    assert out["share_count_verified"] is False
