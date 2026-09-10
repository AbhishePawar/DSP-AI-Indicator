"""SIMPLE-14N LIVE primary-document acquisition. Fail-closed is success."""

from __future__ import annotations

import os
import time

import pytest

from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import FINANCIAL_FIELDS, ResearchOrchestrator
from data_engine.official_research.source_policy import classify_source_url
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

_FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
)


def _skip_if_disabled() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


@pytest.mark.network
def test_live_primary_acquisition_fixtures_and_two_more() -> None:
    """LIVE — identity + bounded document attempt. Does not hard-code values."""
    _skip_if_disabled()
    master = SecurityMasterService(load_default_catalog())
    extra: list[tuple[str, str]] = []
    fixture_isins = {isin for _, isin in _FIXTURES}
    for listing in master.catalog.all():
        if listing.mic != "XNSE" or listing.security_type != "equity":
            continue
        if not listing.eligibility:
            continue
        if listing.isin in fixture_isins:
            continue
        extra.append((listing.ticker, listing.isin))
        if len(extra) >= 2:
            break
    if len(extra) < 2:
        pytest.skip("Security Master missing extra EQ names for LIVE sample")
    names = _FIXTURES + tuple(extra[:2])
    transport = NsePublicHttp()
    nse_eod = NseEodService(transport, mode="LIVE")
    nse_primary = NsePrimaryEvidenceService(transport, mode="LIVE")
    orch = ResearchOrchestrator(
        security_master=master,
        nse_eod=nse_eod,
        nse_primary=nse_primary,
        production=False,
    )
    t0 = time.perf_counter()
    try:
        bundle = nse_eod.fetch_latest()
    except LookupError as exc:
        pytest.skip(f"LIVE NSE EOD not reachable: {exc}")
    eod_s = time.perf_counter() - t0
    rows = []
    for ticker, isin in names:
        started = time.perf_counter()
        research = orch.research(
            ResearchRequest(
                ticker=ticker,
                isin=isin,
                mic="XNSE",
                fields=("eod_close",) + FINANCIAL_FIELDS,
                mode="LIVE",
            ),
            nse_bundle=bundle,
        )
        elapsed = time.perf_counter() - started
        assert research.mode == "LIVE"
        assert research.identity_status == "VERIFIED"
        assert research.isin == isin
        if research.price is not None:
            assert research.price.price_kind == "EOD"
            assert research.price.raw_price_field == "ClsPric"
            assert research.price.isin == isin
        for field in ("ebit", "capex", "net_income", "shares_outstanding"):
            items = research.evidence_for(field)
            if not items:
                continue
            item = items[0]
            if item.status == "VERIFIED":
                assert item.as_of is not None
                if field != "shares_outstanding":
                    assert item.raw_unit or item.unit
                if item.source_url:
                    kind = classify_source_url(item.source_url)
                    assert kind != "secondary"
                    assert kind != "forbidden"
        rows.append(
            {
                "ticker": ticker,
                "isin": isin,
                "seconds": round(elapsed, 3),
                "price": None if research.price is None else str(research.price.price),
                "shares": research.evidence_for("shares_outstanding")[0].status
                if research.evidence_for("shares_outstanding")
                else "UNAVAILABLE",
                "net_income": research.evidence_for("net_income")[0].status
                if research.evidence_for("net_income")
                else "UNAVAILABLE",
                "unresolved": list(research.unresolved)[:8],
            }
        )
    assert len(rows) == len(names)
    _ = eod_s
    print("SIMPLE-14N LIVE rows:", rows)
