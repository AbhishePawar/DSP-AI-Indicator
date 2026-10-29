"""Phase 7 release: missing verified share counts use the NSE research fallback.

Research is last resort, identity/source/freshness checked, cross-checked
against the quote, and labelled as unverified research.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from dsp_platform.composition.authenticated_valuation import (
    AuthenticatedValuationError,
    ShareCountResearchEvidence,
    _resolve_shares,
)
from dsp_platform.investment_provenance.builder import (
    build_investment_provenance,
    source_evidence_from_trace,
)

_MISSING = SimpleNamespace(available=False, value=None)


def _quote(shares: float | None = None) -> SimpleNamespace:
    field = SimpleNamespace(available=True, value=shares) if shares else _MISSING
    return SimpleNamespace(shares_outstanding=field)


def _latest() -> SimpleNamespace:
    return SimpleNamespace(shares_outstanding=_MISSING)


def _evidence(**overrides: object) -> ShareCountResearchEvidence:
    values: dict[str, object] = {
        "ticker": "TCS",
        "company_name": "Tata Consultancy Services Limited",
        "metric": "issued_equity_shares",
        "shares_outstanding": 3_618_087_518.0,
        "source_id": "NSE",
        "source": "NSE quote-equity securityInfo.issuedSize",
        "evidence_url": "https://www.nseindia.com/api/quote-equity?symbol=TCS",
        "as_of": (date.today() - timedelta(days=1)).isoformat(),
        "unit": "shares",
    }
    values.update(overrides)
    return ShareCountResearchEvidence(**values)  # type: ignore[arg-type]


def _resolve(quote: SimpleNamespace, researcher: object) -> tuple[float, dict]:
    return _resolve_shares(  # type: ignore[arg-type]
        quote,
        _latest(),
        ticker="TCS",
        researcher=researcher,  # type: ignore[arg-type]
        company_name="Tata Consultancy Services Ltd",
        exchange="NSE",
    )


def test_missing_shares_recovered_by_research_and_labelled_unverified() -> None:
    calls: list[tuple] = []

    def research(*args: object) -> ShareCountResearchEvidence:
        calls.append(args)
        return _evidence()

    shares, prov = _resolve(_quote(), research)
    assert calls == [("TCS", "Tata Consultancy Services Ltd", "NSE")]
    assert shares == 3_618_087_518.0
    assert prov["source"] == "NSE"
    assert prov["retrieval"] == "ai_research_fallback"
    assert prov["verified"] is False
    assert prov["evidence_class"] == "public_research_unverified_for_g2"


def test_unverifiable_research_returns_controlled_data_unavailable() -> None:
    with pytest.raises(AuthenticatedValuationError, match="no validated evidence"):
        _resolve(_quote(), lambda *_: None)


def test_research_failure_is_controlled() -> None:
    def boom(*_: object) -> None:
        raise TimeoutError("upstream")

    with pytest.raises(AuthenticatedValuationError, match="research failed"):
        _resolve(_quote(), boom)


def test_research_for_other_company_is_rejected() -> None:
    with pytest.raises(AuthenticatedValuationError, match="company identity"):
        _resolve(_quote(), lambda *_: _evidence(company_name="Infosys Limited"))


def test_stale_research_is_rejected() -> None:
    old = (date.today() - timedelta(days=200)).isoformat()
    with pytest.raises(AuthenticatedValuationError, match="stale"):
        _resolve(_quote(), lambda *_: _evidence(as_of=old))


def test_research_conflicting_with_quote_fails_closed() -> None:
    with pytest.raises(AuthenticatedValuationError, match="disagree"):
        _resolve(_quote(5_000_000_000.0), lambda *_: _evidence())


def test_quote_alone_still_never_becomes_denominator() -> None:
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        _resolve_shares(_quote(3_618_087_518.0), _latest(), ticker="TCS")  # type: ignore[arg-type]


def test_provenance_marks_research_shares() -> None:
    trace = {
        "authenticated": True,
        "share_count_provenance": {
            "source": "NSE",
            "retrieval": "ai_research_fallback",
            "verified": False,
            "evidence_class": "public_research_unverified_for_g2",
        },
    }
    out = source_evidence_from_trace(trace)
    assert out["shares_source"] == "research_fallback"
    assert out["share_count_verified"] is False
    assert out["shares_evidence_class"] == "public_research_unverified_for_g2"
    record = build_investment_provenance(
        public_payload={}, ticker="TCS", authenticated_valuation_trace=trace
    )
    assert (
        record.to_dict()["financial_validation"]["integrity"]
        == "authenticated_bundle_with_research_shares"
    )
