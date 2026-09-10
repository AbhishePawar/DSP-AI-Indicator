"""LIVE official NSE EOD retrieval. Never treats MOCK fixtures as live."""

from __future__ import annotations

import os

import pytest

from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.orchestrator import ResearchOrchestrator
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

_FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
)


@pytest.mark.network
def test_live_nse_udiff_four_fixtures() -> None:
    """LIVE — official NSE UDiFF EOD for four regression fixtures."""
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE EOD skipped by DSP_SKIP_LIVE_NSE_EOD=1")
    try:
        bundle = NseEodService(NsePublicHttp(), mode="LIVE").fetch_latest()
    except LookupError as exc:
        pytest.skip(f"LIVE NSE EOD not reachable: {exc}")
    assert bundle.mode == "LIVE"
    assert bundle.rows
    orch = ResearchOrchestrator(
        security_master=SecurityMasterService(load_default_catalog()),
        nse_eod=NseEodService(NsePublicHttp(), mode="LIVE"),
        production=False,
    )
    for ticker, isin in _FIXTURES:
        result = orch.research(
            ResearchRequest(
                ticker=ticker,
                isin=isin,
                mic="XNSE",
                fields=("eod_close",),
                mode="LIVE",
            ),
            nse_bundle=bundle,
        )
        assert result.mode == "LIVE"
        assert result.identity_status == "VERIFIED"
        assert result.isin == isin
        assert result.price is not None
        assert result.price.price_kind == "EOD"
        assert result.price.raw_price_field == "ClsPric"
        assert result.price.isin == isin
        assert result.price.mic == "XNSE"
        assert result.price.price > 0
        assert result.evidence_for("eod_close")[0].status == "VERIFIED"


@pytest.mark.network
def test_live_nse_primary_does_not_use_last_price() -> None:
    """LIVE primary intake may be incomplete; lastPrice still cannot be EOD."""
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE EOD skipped by DSP_SKIP_LIVE_NSE_EOD=1")
    from data_engine.official_research.nse_primary import NsePrimaryEvidenceService

    listing = SecurityMasterService(load_default_catalog()).resolve(
        "INFY", isin="INE009A01021", mic="XNSE"
    )
    if listing.identity is None:
        pytest.skip("INFY missing from Security Master")
    try:
        bundle = NsePrimaryEvidenceService(NsePublicHttp(), mode="LIVE").fetch(
            listing.identity
        )
    except LookupError as exc:
        pytest.skip(f"LIVE NSE primary not reachable: {exc}")
    assert "eod_close" not in bundle.fields
    assert "price" not in bundle.fields
    shares = bundle.fields.get("shares_outstanding")
    if shares is not None:
        assert shares.as_of is not None
