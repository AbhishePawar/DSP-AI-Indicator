"""Unit tests for evidence-grounded missing-share-count research."""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

import api_platform.api.share_count_research as share_count_research
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

def test_researcher_returns_only_source_grounded_share_evidence(
    monkeypatch,
) -> None:
    as_of = date.today().isoformat()
    source = (
        '{"info":{"symbol":"ABC","companyName":"ABC Limited"},'
        f'"metadata":{{"lastUpdateTime":"{as_of}"}},'
        '"securityInfo":{"issuedSize":12345}}'
    )
    source_url = "https://www.nseindia.com/api/quote-equity?symbol=ABC"

    class ConfiguredAdapter:
        def is_configured(self) -> bool:
            return True

    adapter = ConfiguredAdapter()
    registry = SimpleNamespace(
        config=SimpleNamespace(provider_mode="direct", default_provider="gemini"),
        get=lambda name: adapter if name == "gemini" else None,
    )
    monkeypatch.setattr(
        share_count_research, "build_default_registry", lambda: registry
    )
    monkeypatch.setattr(
        share_count_research,
        "_fetch_nse_record",
        lambda symbol: (source, source_url) if symbol == "ABC" else None,
    )
    monkeypatch.setattr(
        share_count_research,
        "_json_completion",
        lambda _provider, _prompt: {
            "ticker": "ABC",
            "shares_outstanding": 12345,
            "as_of": as_of,
            "evidence_excerpt": '"issuedSize":12345',
        },
    )

    researcher = share_count_research.build_share_count_researcher()
    assert researcher is not None
    evidence = researcher("ABC", "ABC Ltd", "NSE")
    assert evidence is not None
    assert evidence.ticker == "ABC"
    assert evidence.company_name == "ABC Limited"
    assert evidence.metric == "issued_equity_shares"
    assert evidence.shares_outstanding == 12345
    assert evidence.unit == "shares"
    assert evidence.as_of == as_of
    assert evidence.evidence_url == source_url


def test_researcher_rejects_company_identity_mismatch(monkeypatch) -> None:
    as_of = date.today().isoformat()
    source = (
        '{"info":{"symbol":"ABC","companyName":"ABC Limited"},'
        f'"metadata":{{"lastUpdateTime":"{as_of}"}},'
        '"securityInfo":{"issuedSize":12345}}'
    )

    class ConfiguredAdapter:
        def is_configured(self) -> bool:
            return True

    adapter = ConfiguredAdapter()
    registry = SimpleNamespace(
        config=SimpleNamespace(provider_mode="direct", default_provider="gemini"),
        get=lambda name: adapter if name == "gemini" else None,
    )
    monkeypatch.setattr(
        share_count_research, "build_default_registry", lambda: registry
    )
    monkeypatch.setattr(
        share_count_research,
        "_fetch_nse_record",
        lambda _symbol: (
            source,
            "https://www.nseindia.com/api/quote-equity?symbol=ABC",
        ),
    )
    monkeypatch.setattr(
        share_count_research,
        "_json_completion",
        lambda *_: pytest.fail(
            "AI must not be called for mismatched company identity"
        ),
    )

    researcher = share_count_research.build_share_count_researcher()
    assert researcher is not None
    assert researcher("ABC", "Different Company Ltd", "NSE") is None
