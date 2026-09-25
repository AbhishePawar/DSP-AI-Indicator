"""Dump LIVE 14N-C WIPRO/HDFC field matrix from orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import FINANCIAL_FIELDS, ResearchOrchestrator
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

OUT = Path("artifacts/simple14nc_live_wipro_hdfc.json")
FIELDS = FINANCIAL_FIELDS + ("total_assets", "total_liabilities")


def dump(ticker: str, isin: str, orch, bundle) -> dict:
    started = perf_counter()
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
    fields = {}
    for field in FINANCIAL_FIELDS:
        items = research.evidence_for(field)
        if not items:
            fields[field] = None
            continue
        item = items[0]
        fields[field] = {
            "status": item.status,
            "value": item.value,
            "raw": item.raw_value,
            "unit": item.raw_unit or item.unit,
            "as_of": None if item.as_of is None else item.as_of.isoformat(),
            "current_through": None if item.current_through is None else item.current_through.isoformat(),
            "basis": item.statement_basis,
            "locator": item.evidence_locator,
            "url": item.source_url,
            "ca": item.corporate_action_status,
        }
    return {
        "ticker": ticker,
        "seconds": round(perf_counter() - started, 3),
        "identity": research.identity_status,
        "price": None if research.price is None else str(research.price.price),
        "fields": fields,
        "unresolved": list(research.unresolved)[:10],
    }


def main() -> None:
    master = SecurityMasterService(load_default_catalog())
    transport = NsePublicHttp()
    nse_eod = NseEodService(transport, mode="LIVE")
    orch = ResearchOrchestrator(
        security_master=master,
        nse_eod=nse_eod,
        nse_primary=NsePrimaryEvidenceService(transport, mode="LIVE"),
        production=False,
    )
    bundle = nse_eod.fetch_latest()
    rows = [
        dump("WIPRO", "INE075A01022", orch, bundle),
        dump("HDFCBANK", "INE040A01034", orch, bundle),
        dump("RELIANCE", "INE002A01018", orch, bundle),
    ]
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    for row in rows:
        print(row["ticker"], row["seconds"], {k: (v or {}).get("status") for k, v in row["fields"].items()})


if __name__ == "__main__":
    main()
