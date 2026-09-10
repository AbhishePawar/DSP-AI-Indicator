"""SIMPLE-14N-A LIVE IR registry + annual-document selection. Fail-closed is success."""

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
)
_EXTRA = (
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)


def _skip_if_disabled() -> None:
    if os.environ.get("DSP_SKIP_LIVE_NSE_EOD") == "1":
        pytest.skip("LIVE NSE skipped by DSP_SKIP_LIVE_NSE_EOD=1")


@pytest.mark.network
def test_live_ir_registry_and_annual_selection() -> None:
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
    for ticker, isin in _FIXTURES + _EXTRA:
        record = registry.record(isin)
        assert record is not None
        resolved = master.resolve(ticker, exchange="NSE", isin=isin, mic="XNSE")
        assert resolved.status == "RESOLVED"
        assert resolved.identity is not None
        assert resolved.identity.isin == isin
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
        assert research.isin == isin
        assert research.company
        if research.price is not None:
            assert research.price.price_kind == "EOD"
            assert research.price.isin == isin
        for field in ("ebit", "capex", "net_income", "shares_outstanding", "revenue"):
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
                    assert registry.allows(isin, item.source_url) or kind == "primary"
        net = research.evidence_for("net_income")
        shares = research.evidence_for("shares_outstanding")
        rows.append(
            {
                "ticker": ticker,
                "isin": isin,
                "ir_domain": record.official_domain,
                "ir_url": record.investor_relations_url,
                "seconds": round(elapsed, 3),
                "price": None if research.price is None else str(research.price.price),
                "net_income": None if not net else net[0].status,
                "shares": None if not shares else shares[0].status,
                "share_as_of": None
                if not shares
                else (None if shares[0].as_of is None else shares[0].as_of.isoformat()),
                "unresolved": list(research.unresolved)[:6],
            }
        )
    assert len(rows) == 7
    print("SIMPLE-14N-A LIVE eod_s", round(eod_s, 3), "rows", rows)
