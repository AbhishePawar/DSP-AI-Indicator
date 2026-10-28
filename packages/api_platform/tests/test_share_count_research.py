"""Unit tests for evidence-grounded missing-share-count research."""
from __future__ import annotations

from datetime import date, timedelta

from api_platform.api.share_count_research import _evidence_is_grounded


def _result(*, ticker: str = "ABC", count: int = 12345, as_of: str | None = None):
    excerpt = f'"totalNoOfShares":{count}'
    return {
        "ticker": ticker,
        "shares_outstanding": count,
        "as_of": as_of or date.today().isoformat(),
        "evidence_excerpt": excerpt,
    }


def test_accepts_exact_recent_official_total_share_field() -> None:
    result = _result()
    source = '{"symbol":"ABC","totalNoOfShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") == (
        12345.0,
        date.today(),
    )


def test_rejects_ticker_mismatch() -> None:
    result = _result(ticker="XYZ")
    source = '{"symbol":"ABC","totalNoOfShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_model_generated_excerpt_not_in_source() -> None:
    result = _result(count=12346)
    source = '{"symbol":"ABC","totalNoOfShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_count_not_equal_to_quoted_value() -> None:
    result = _result(count=12346)
    result["evidence_excerpt"] = '"totalNoOfShares":12345'
    source = '{"symbol":"ABC","totalNoOfShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_stale_shareholding_evidence() -> None:
    stale = (date.today() - timedelta(days=121)).isoformat()
    result = _result(as_of=stale)
    source = '{"symbol":"ABC","totalNoOfShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None


def test_rejects_non_total_share_fields() -> None:
    result = {
        "ticker": "ABC",
        "shares_outstanding": 12345,
        "as_of": date.today().isoformat(),
        "evidence_excerpt": '"promoterShares":12345',
    }
    source = '{"symbol":"ABC","promoterShares":12345}'
    assert _evidence_is_grounded(result, source, "ABC") is None
