"""SIMPLE-14N-B LIVE verified financial + share-currentness. Fail-closed is success."""

from __future__ import annotations

import os
import time

import pytest

from data_engine.official_research.company_sources import load_company_source_registry
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
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)


def _skip_if_disabled() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


@pytest.mark.network
def test_live_verified_financial_and_share_currentness() -> None:
    _skip_if_disabled()
    registry = load_company_source_registry()
    master = SecurityMasterService(load_default_catalog())
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
    for ticker, isin in _FIXTURES:
        record = registry.record(isin)
        assert record is not None
        resolved = master.resolve(ticker, exchange="NSE", isin=isin, mic="XNSE")
        assert resolved.status == "RESOLVED"
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
        assert research.identity_status == "VERIFIED"
        if research.price is not None:
            assert research.price.price_kind == "EOD"
        field_status = {}
        for field in FINANCIAL_FIELDS:
            items = research.evidence_for(field)
            if not items:
                field_status[field] = None
                continue
            item = items[0]
            field_status[field] = {
                "status": item.status,
                "value": item.value,
                "raw_value": item.raw_value,
                "as_of": None if item.as_of is None else item.as_of.isoformat(),
                "current_through": (
                    None
                    if item.current_through is None
                    else item.current_through.isoformat()
                ),
                "unit": item.unit,
                "raw_unit": item.raw_unit,
                "basis": item.statement_basis,
                "locator": item.evidence_locator,
                "url": item.source_url,
                "ca": item.corporate_action_status,
            }
            if item.status == "VERIFIED":
                assert item.as_of is not None
                if field != "shares_outstanding":
                    assert item.raw_unit or item.unit
                if item.source_url:
                    kind = classify_source_url(item.source_url)
                    assert kind != "secondary"
                    assert kind != "forbidden"
            if (
                ticker == "WIPRO"
                and field == "shares_outstanding"
                and item.as_of is not None
                and item.as_of.isoformat() <= "2026-06-26"
            ):
                assert item.status == "REFRESH_REQUIRED"
        rows.append(
            {
                "ticker": ticker,
                "seconds": round(elapsed, 3),
                "price": None if research.price is None else str(research.price.price),
                "fields": field_status,
                "unresolved": list(research.unresolved)[:8],
            }
        )
    assert len(rows) == 7
    print("SIMPLE-14N-B LIVE eod_s", round(eod_s, 3), "rows", rows)
