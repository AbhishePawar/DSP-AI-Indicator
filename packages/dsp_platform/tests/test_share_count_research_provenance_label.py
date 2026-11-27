"""A researched share count must never be reported as authenticated-provider evidence."""

from dsp_platform.investment_provenance.builder import source_evidence_from_trace

_BASE = {
    "authenticated": True,
    "ticker": "TCS",
    "shares_outstanding": 3_618_087_518.0,
    "statement_provenance": {"provider_id": "stmt"},
}


def test_research_fallback_shares_are_labelled_unverified_for_g2() -> None:
    trace = {
        **_BASE,
        "quote_provenance": {
            "provider_id": "quote",
            "shares_research_fallback": {
                "provider_id": "ai_research_fallback",
                "evidence_class": "public_research_unverified_for_g2",
            },
        },
    }
    out = source_evidence_from_trace(trace)
    assert out["shares_source"] == "research_fallback"
    assert out["shares_evidence_class"] == "public_research_unverified_for_g2"


def test_quote_shares_remain_authenticated_quote() -> None:
    out = source_evidence_from_trace(
        {**_BASE, "quote_provenance": {"provider_id": "q"}}
    )
    assert out["shares_source"] == "authenticated_quote"
    assert out["shares_evidence_class"] is None
