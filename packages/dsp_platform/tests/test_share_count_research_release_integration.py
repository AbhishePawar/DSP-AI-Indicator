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


# --- PR #34 audit regressions -------------------------------------------------


def _never_called(*_: object) -> ShareCountResearchEvidence:
    raise AssertionError("research must not run when an approved source exists")


def test_trusted_statement_count_wins_and_research_is_not_called() -> None:
    latest = SimpleNamespace(
        shares_outstanding=SimpleNamespace(available=True, value=3_618_087_518.0),
        period_end=date(2026, 3, 31),
    )
    shares, prov = _resolve_shares(  # type: ignore[arg-type]
        _quote(),
        latest,
        ticker="TCS",
        researcher=_never_called,
        company_name="Tata Consultancy Services Ltd",
        exchange="NSE",
    )
    assert shares == 3_618_087_518.0
    assert prov["source"] == "authenticated_financial_statement"
    assert prov["verified"] is True


def test_no_researcher_and_no_approved_source_is_controlled() -> None:
    with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
        _resolve(_quote(), None)


@pytest.mark.parametrize(
    "bad_value",
    [0.0, -1.0, float("nan"), float("inf"), 1.5, "3618087518", True, None],
)
def test_malformed_research_counts_are_rejected(bad_value: object) -> None:
    with pytest.raises(AuthenticatedValuationError, match="share count"):
        _resolve(_quote(), lambda *_: _evidence(shares_outstanding=bad_value))


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"ticker": "INFY"}, "ticker mismatch"),
        ({"metric": "free_float_shares"}, "issued equity shares"),
        ({"unit": "crore"}, "unit must be shares"),
        ({"source_id": "RANDOMBLOG"}, "unapproved"),
        ({"evidence_url": "http://www.nseindia.com/x"}, "HTTPS"),
        ({"as_of": "not-a-date"}, "date missing or invalid"),
        ({"as_of": (date.today() + timedelta(days=3)).isoformat()}, "future"),
    ],
)
def test_ungrounded_research_fields_are_rejected(
    override: dict[str, object], message: str
) -> None:
    with pytest.raises(AuthenticatedValuationError, match=message):
        _resolve(_quote(), lambda *_: _evidence(**override))


def test_research_without_requested_company_identity_fails_closed() -> None:
    with pytest.raises(AuthenticatedValuationError, match="company identity"):
        _resolve_shares(  # type: ignore[arg-type]
            _quote(),
            _latest(),
            ticker="TCS",
            researcher=lambda *_: _evidence(),
            company_name=None,
            exchange="NSE",
        )


def test_research_count_inconsistent_with_eps_is_rejected() -> None:
    from dsp_platform.composition.financial_integrity import (
        FinancialIntegrityError,
        assert_eps_share_integrity,
    )

    shares, _ = _resolve(_quote(), lambda *_: _evidence())
    period = SimpleNamespace(
        net_income=SimpleNamespace(available=True, value=1_000_000_000.0),
        eps_basic=SimpleNamespace(available=True, value=50.0),
        eps_diluted=_MISSING,
    )
    with pytest.raises(FinancialIntegrityError, match="EPS inconsistent"):
        assert_eps_share_integrity(period, shares)  # type: ignore[arg-type]


def test_research_evidence_class_can_never_clear_g2() -> None:
    from data_engine.evidence_classes import may_clear_g2

    _, prov = _resolve(_quote(), lambda *_: _evidence())
    assert may_clear_g2(prov["evidence_class"]) is False
