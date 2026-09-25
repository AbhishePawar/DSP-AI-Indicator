"""LIVE qualify SIMPLE-14N. Fail-closed is a valid outcome. No hardcoded values."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

os.environ["DSP_LIVE_NSE_EOD"] = "1"
os.environ.pop("PYTEST_CURRENT_TEST", None)

from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import FINANCIAL_FIELDS, ResearchOrchestrator
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
)


def main() -> int:
    master = SecurityMasterService(load_default_catalog())
    extra: list[tuple[str, str]] = []
    fixture_isins = {isin for _, isin in FIXTURES}
    for listing in master.catalog.all():
        if listing.mic != "XNSE" or not listing.eligibility:
            continue
        if listing.isin in fixture_isins:
            continue
        extra.append((listing.ticker, listing.isin))
        if len(extra) >= 2:
            break
    names = FIXTURES + tuple(extra[:2])
    transport = NsePublicHttp()
    nse_eod = NseEodService(transport, mode="LIVE")
    nse_primary = NsePrimaryEvidenceService(transport, mode="LIVE")
    orch = ResearchOrchestrator(
        security_master=master,
        nse_eod=nse_eod,
        nse_primary=nse_primary,
        production=False,
    )
    out: dict[str, object] = {"names": [list(item) for item in names], "rows": []}
    t0 = time.perf_counter()
    try:
        bundle = nse_eod.fetch_latest()
        eod = {
            "ok": True,
            "seconds": round(time.perf_counter() - t0, 3),
            "as_of": bundle.discovered.trading_date
            if hasattr(bundle.discovered, "trading_date")
            else None,
            "file": getattr(bundle.discovered, "file_name", None)
            or getattr(bundle.discovered, "fileActlName", None),
        }
    except LookupError as exc:
        eod = {"ok": False, "error": str(exc), "seconds": round(time.perf_counter() - t0, 3)}
        bundle = None
    out["eod"] = eod
    print(json.dumps({"eod": eod}, default=str))
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
        row = {
            "ticker": ticker,
            "isin": research.isin,
            "identity": research.identity_status,
            "seconds": round(time.perf_counter() - started, 3),
            "price": None if research.price is None else str(research.price.price),
            "price_kind": None if research.price is None else research.price.price_kind,
            "price_as_of": None
            if research.price is None
            else research.price.as_of.isoformat(),
            "shares": _status(research, "shares_outstanding"),
            "net_income": _status(research, "net_income"),
            "revenue": _status(research, "revenue"),
            "ebit": _status(research, "ebit"),
            "capex": _status(research, "capex"),
            "unresolved": list(research.unresolved)[:12],
        }
        out["rows"].append(row)
        print(json.dumps(row, default=str))
    out["total_seconds"] = round(time.perf_counter() - t0, 3)
    target = Path("artifacts") / "simple14n_live_qualify.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"wrote": str(target), "total_seconds": out["total_seconds"]}))
    return 0


def _status(research, field: str) -> dict[str, object]:
    rows = research.evidence_for(field)
    if not rows:
        return {"status": "UNAVAILABLE"}
    item = rows[0]
    return {
        "status": item.status,
        "as_of": None if item.as_of is None else item.as_of.isoformat(),
        "source": item.source,
        "raw_unit": item.raw_unit,
        "statement_basis": item.statement_basis,
    }


if __name__ == "__main__":
    raise SystemExit(main())
