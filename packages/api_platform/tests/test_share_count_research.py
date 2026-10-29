"""Unit tests for evidence-grounded missing-share-count research."""
from __future__ import annotations

from datetime import date, timedelta

from api_platform.api.share_count_research import (
    _company_identity_matches,
    _evidence_is_grounded,
)


def _result(*, ticker: str = "ABC", count: int = 12345, as_of: str | None = None):
    excerpt = f'"issuedSize":{count}'
    return {
        "ticker": ticker,
        "shares_outstanding": count,
        "as_of": as_of or date.today().isoformat(),
        "evidence_excerpt": excerpt,
    }


def test_accepts_exact_recent_official_issued_size_field() -> None:
    result = _result()
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC") == (
        12345.0,
        date.today(),
    )


def test_rejects_ticker_mismatch() -> None:
    result = _result(ticker="XYZ")
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_model_generated_excerpt_not_in_source() -> None:
    result = _result(count=12346)
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_count_not_equal_to_quoted_value() -> None:
    result = _result(count=12346)
    result["evidence_excerpt"] = '"issuedSize":12345'
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_stale_shareholding_evidence() -> None:
    stale = (date.today() - timedelta(days=121)).isoformat()
    result = _result(as_of=stale)
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_non_total_share_fields() -> None:
    result = {
        "ticker": "ABC",
        "shares_outstanding": 12345,
        "as_of": date.today().isoformat(),
        "evidence_excerpt": '"promoterShares":12345',
    }
    source = '{"info":{"symbol":"ABC"},"promoterShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_model_date_that_differs_from_source_date() -> None:
    source_date = date.today() - timedelta(days=1)
    result = _result(as_of=date.today().isoformat())
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345}}'
    assert _evidence_is_grounded(result, source, "ABC", source_date) is None


def test_rejects_fractional_share_count() -> None:
    result = {
        "ticker": "ABC",
        "shares_outstanding": 12345.5,
        "as_of": date.today().isoformat(),
        "evidence_excerpt": '"issuedSize":12345.5',
    }
    source = '{"info":{"symbol":"ABC"},"securityInfo":{"issuedSize":12345.5}}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_company_identity_accepts_legal_suffix_variants() -> None:
    assert _company_identity_matches("HDFC Bank Limited", "HDFC BANK LTD")


def test_company_identity_rejects_mismatched_company() -> None:
    assert not _company_identity_matches("HDFC Bank Limited", "ABC Industries Ltd")
