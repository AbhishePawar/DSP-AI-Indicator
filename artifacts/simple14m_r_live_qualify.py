"""LIVE qualification for SIMPLE-14M-R. Not imported by production."""

from __future__ import annotations

import json
import os
import time
from decimal import Decimal

os.environ["DSP_LIVE_NSE_EOD"] = "1"
os.environ.pop("PYTEST_CURRENT_TEST", None)

from data_engine.official_research.nse_eod import NseEodService, NsePublicHttp
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import FINANCIAL_FIELDS, ResearchOrchestrator
from data_engine.official_research.models import ResearchRequest
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration, pipeline_result_public_dict
from dsp_platform.composition.models import CompositionRequest
from fastapi.testclient import TestClient
from api_platform import create_app


FIXTURES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
)
ARBITRARY = ("RELIANCE", "INE002A01018")


def main() -> None:
    timings: dict[str, float] = {}
    report: dict[str, object] = {"timings_ms": timings}

    t0 = time.perf_counter()
    master = SecurityMasterService(load_default_catalog())
    timings["security_master"] = (time.perf_counter() - t0) * 1000

    http = NsePublicHttp()
    t0 = time.perf_counter()
    try:
        bundle = NseEodService(http, mode="LIVE").fetch_latest()
        timings["nse_eod_total"] = (time.perf_counter() - t0) * 1000
        report["nse_eod"] = {
            "fileActlName": bundle.discovered.file_name,
            "url": bundle.discovered.url,
            "trading_date": bundle.discovered.trading_date,
            "bucket": bundle.discovered.bucket,
            "rows": len(bundle.rows),
            "market_open": bundle.market.market_open,
            "session_date": None
            if bundle.market.session_date is None
            else bundle.market.session_date.isoformat(),
            "payload_size": bundle.payload_size,
        }
    except LookupError as exc:
        report["nse_eod_error"] = str(exc)
        bundle = None
        timings["nse_eod_total"] = (time.perf_counter() - t0) * 1000

    orch = ResearchOrchestrator(
        security_master=master,
        nse_eod=NseEodService(http, mode="LIVE"),
        nse_primary=NsePrimaryEvidenceService(http, mode="LIVE"),
        production=False,
    )
    fixture_rows = []
    for ticker, isin in (*FIXTURES, ARBITRARY):
        t0 = time.perf_counter()
        result = orch.research(
            ResearchRequest(
                ticker=ticker,
                isin=isin,
                mic="XNSE",
                fields=("eod_close",) + FINANCIAL_FIELDS,
                mode="LIVE",
            ),
            nse_bundle=bundle,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        price = result.price
        fixture_rows.append(
            {
                "ticker": ticker,
                "isin": result.isin,
                "identity": result.identity_status,
                "price": None if price is None else str(price.price),
                "price_kind": None if price is None else price.price_kind,
                "price_as_of": None if price is None else price.as_of.isoformat(),
                "raw_price_field": None if price is None else price.raw_price_field,
                "unresolved": list(result.unresolved),
                "fields": {
                    item.field: item.status for item in result.evidence
                },
                "elapsed_ms": elapsed,
            }
        )
    report["research"] = fixture_rows

    t0 = time.perf_counter()
    listing = master.resolve("INFY", isin="INE009A01021", mic="XNSE").identity
    primary = None
    if listing is not None:
        try:
            primary = NsePrimaryEvidenceService(http, mode="LIVE").fetch(listing)
        except LookupError as exc:
            report["primary_error"] = str(exc)
    timings["nse_primary"] = (time.perf_counter() - t0) * 1000
    if primary is not None:
        report["primary"] = {
            "fields": {
                name: {
                    "value": item.value,
                    "as_of": None if item.as_of is None else item.as_of.isoformat(),
                    "locator": item.locator,
                    "semantic": item.semantic_status,
                }
                for name, item in primary.fields.items()
            },
            "announcements_searched": primary.announcements_searched,
            "last_price_ignored": primary.last_price_ignored,
            "issues": list(primary.issues),
            "events": [event.event_type for event in primary.capital_events],
            "statement_basis": primary.statement_basis,
            "unit_scale": primary.unit_scale,
        }

    platform = DSPPlatform()
    analyse_rows = []
    for ticker, isin in (*FIXTURES, ARBITRARY):
        t0 = time.perf_counter()
        envelope = platform.compose_intelligence(
            CompositionRequest(
                ticker=ticker,
                isin=isin,
                mic="XNSE",
                exchange="NSE",
                research_mode="LIVE",
            )
        )
        elapsed = (time.perf_counter() - t0) * 1000
        public = pipeline_result_public_dict(envelope.payload)
        sv = public.get("server_valuation") or {}
        analyse_rows.append(
            {
                "ticker": ticker,
                "elapsed_ms": elapsed,
                "ok": public.get("ok"),
                "identity": (public.get("dsp_analysis") or {}).get("identity"),
                "price": sv.get("current_market_price"),
                "price_kind": sv.get("price_kind"),
                "price_as_of": sv.get("price_as_of"),
                "iv": sv.get("intrinsic_value_per_share"),
                "valuation_status": sv.get("valuation_status"),
                "valuation_detail": sv.get("valuation_detail"),
                "unresolved": (public.get("dsp_analysis") or {}).get("unresolved_issues"),
            }
        )
    report["compose"] = analyse_rows
    timings["analyse_four_plus_arbitrary"] = sum(
        row["elapsed_ms"] for row in analyse_rows
    )

    t0 = time.perf_counter()
    app = create_app(
        platform=PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    client = TestClient(app)
    forged = client.post(
        "/api/v1/analyse",
        json={
            "ticker": "INFY",
            "exchange": "NSE",
            "isin": "INE009A01021",
            "mic": "XNSE",
            "current_market_price": 1,
        },
    )
    timings["http_forgery"] = (time.perf_counter() - t0) * 1000
    body = forged.json()
    payload = body.get("payload") or {}
    report["http_forgery"] = {
        "status": forged.status_code,
        "price": (payload.get("server_valuation") or {}).get("current_market_price"),
        "iv": (payload.get("server_valuation") or {}).get("intrinsic_value_per_share"),
        "price_kind": (payload.get("server_valuation") or {}).get("price_kind"),
    }

    unknown = client.post(
        "/api/v1/analyse",
        json={"ticker": "NOTAREALTICKERXYZ", "isin": "INE999999999", "mic": "XNSE"},
    )
    report["http_unknown"] = {
        "status": unknown.status_code,
        "iv": ((unknown.json().get("payload") or {}).get("server_valuation") or {}).get(
            "intrinsic_value_per_share"
        ),
    }

    wrong = client.post(
        "/api/v1/analyse",
        json={
            "ticker": "INFY",
            "isin": "INE000000000",
            "mic": "XNSE",
            "exchange": "NSE",
        },
    )
    report["http_wrong_isin"] = {
        "status": wrong.status_code,
        "iv": ((wrong.json().get("payload") or {}).get("server_valuation") or {}).get(
            "intrinsic_value_per_share"
        ),
        "identity": ((wrong.json().get("payload") or {}).get("dsp_analysis") or {}).get(
            "data_status"
        ),
    }

    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
