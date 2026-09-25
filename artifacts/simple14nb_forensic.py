"""SIMPLE-14N-B forensic probe. Not a test of values. Fail-closed is success.

Proves retrieval failure classes for the seven-name set and whether an
approved primary route can return an annual PDF. Does not promote numbers.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "data_engine" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "dsp_platform" / "src"))

from data_engine.official_research.acquisition import acquire_primary_documents
from data_engine.official_research.annual_report import (
    html_document_links,
    latest_completed_indian_fy,
    select_annual_documents,
)
from data_engine.official_research.company_sources import load_company_source_registry
from data_engine.official_research.documents import (
    RetrievalFailure,
    retrieve_official_document,
)
from data_engine.official_research.extraction import parse_document_context
from data_engine.official_research.nse_eod import NSE_ALL_REPORTS, NseEodService, NsePublicHttp
from data_engine.official_research.nse_primary import (
    NSE_ANNOUNCEMENTS_URL,
    NSE_FINANCIAL_RESULTS_URL,
    NSE_QUOTE_EQUITY_URL,
    NSE_SHAREHOLDING_URL,
    NsePrimaryEvidenceService,
)
from data_engine.official_research.pdf_text import document_text_from_payload
from data_engine.official_research.source_policy import classify_source_url
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService

NAMES = (
    ("INFY", "INE009A01021"),
    ("TCS", "INE467B01029"),
    ("WIPRO", "INE075A01022"),
    ("HDFCBANK", "INE040A01034"),
    ("RELIANCE", "INE002A01018"),
    ("ASIANPAINT", "INE021A01026"),
    ("HINDUNILVR", "INE030A01027"),
)

NSE_ANNUAL_REPORTS_URL = "https://www.nseindia.com/api/annual-reports"
BSE_GETQUOTE = "https://api.bseindia.com/BseIndiaAPI/api/GetQuote/w"
BSE_ANNUAL = "https://api.bseindia.com/BseIndiaAPI/api/AnnualReport/w"
BSE_ANN = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
SEBI_HOME = "https://www.sebi.gov.in/"
MCA_HOME = "https://www.mca.gov.in/"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def classify_failure(message: str, status: int | None = None) -> str:
    lowered = str(message or "").lower()
    if status == 403 or "http 403" in lowered or "nse http 403" in lowered:
        return "403"
    if status == 404 or "http 404" in lowered:
        return "404"
    if status == 429 or "http 429" in lowered:
        return "429"
    if status is not None and status >= 500:
        return "5xx"
    if "unapproved redirect" in lowered:
        return "redirect_rejection"
    if "ssl" in lowered or "tls" in lowered or "certificate" in lowered:
        return "tls_failure"
    if "dns" in lowered or "nameresolution" in lowered or "getaddrinfo" in lowered:
        return "dns_failure"
    if "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    return "other"


def probe_url(transport: NsePublicHttp, url: str, *, referer: str | None = None) -> dict:
    started = time.perf_counter()
    try:
        payload = transport.get_bytes(url, referer=referer)
        elapsed = round(time.perf_counter() - started, 3)
        head = payload[:8]
        kind = "bytes"
        if payload.lstrip().startswith(b"%PDF"):
            kind = "pdf"
        elif payload.lstrip().startswith(b"<"):
            kind = "html"
        elif payload.lstrip().startswith((b"{", b"[")):
            kind = "json"
        return {
            "url": url,
            "ok": True,
            "class": "retrieved",
            "http_status": 200,
            "bytes": len(payload),
            "kind": kind,
            "head": head.decode("latin-1", errors="replace"),
            "seconds": elapsed,
        }
    except LookupError as exc:
        elapsed = round(time.perf_counter() - started, 3)
        message = str(exc)
        status = None
        for token in message.replace("NSE HTTP", "HTTP").split():
            if token.isdigit() and len(token) == 3:
                status = int(token)
                break
        return {
            "url": url,
            "ok": False,
            "class": classify_failure(message, status),
            "http_status": status,
            "reason": message,
            "seconds": elapsed,
        }


def probe_company_ir(url: str, *, isin: str, mic: str, registry, transport) -> dict:
    started = time.perf_counter()
    result = retrieve_official_document(
        url,
        transport=transport,
        isin=isin,
        mic=mic,
        source_type="company_ir",
        registry=registry,
    )
    elapsed = round(time.perf_counter() - started, 3)
    if isinstance(result, RetrievalFailure):
        return {
            "url": url,
            "ok": False,
            "class": classify_failure(result.reason, result.http_status),
            "http_status": result.http_status,
            "reason": result.reason,
            "seconds": elapsed,
        }
    kind = result.content_type
    pdf_links = []
    if result.content_type.startswith("text/html"):
        html = result.payload.decode("utf-8", errors="replace")
        pdf_links = [
            {"href": href, "label": label}
            for href, label in html_document_links(
                html,
                base_url=url,
                allow_url=lambda href: registry.allows(isin, href),
            )
        ]
    return {
        "url": url,
        "ok": True,
        "class": "retrieved",
        "http_status": result.http_status,
        "content_type": kind,
        "bytes": result.content_length,
        "hash": result.document_hash,
        "pdf_links": pdf_links[:20],
        "pdf_link_count": len(pdf_links),
        "seconds": elapsed,
    }


def json_preview(payload: bytes, limit: int = 800) -> object:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return payload[:limit].decode("latin-1", errors="replace")
    if isinstance(parsed, list):
        return {
            "type": "list",
            "len": len(parsed),
            "first_keys": list(parsed[0].keys()) if parsed and isinstance(parsed[0], dict) else None,
            "sample": parsed[:2],
        }
    if isinstance(parsed, dict):
        return {
            "type": "object",
            "keys": list(parsed.keys())[:40],
            "sample": {k: parsed[k] for k in list(parsed)[:8]},
        }
    return {"type": type(parsed).__name__}


def bse_probe_by_scrip(opener, scrip: str) -> dict:
    url = f"{BSE_ANNUAL}?scripcode={scrip}"
    started = time.perf_counter()
    request = Request(url, headers={"User-Agent": _UA, "Referer": "https://www.bseindia.com/"})
    try:
        with opener.open(request, timeout=20) as response:
            payload = response.read()
        return {
            "url": url,
            "ok": True,
            "class": "retrieved",
            "http_status": 200,
            "bytes": len(payload),
            "seconds": round(time.perf_counter() - started, 3),
            "preview": json_preview(payload),
        }
    except HTTPError as exc:
        body = exc.read()[:300] if exc.fp else b""
        return {
            "url": url,
            "ok": False,
            "class": classify_failure(f"HTTP {exc.code}", exc.code),
            "http_status": exc.code,
            "reason": body.decode("latin-1", errors="replace"),
            "seconds": round(time.perf_counter() - started, 3),
        }
    except (URLError, OSError) as exc:
        return {
            "url": url,
            "ok": False,
            "class": classify_failure(str(exc)),
            "reason": f"{type(exc).__name__}: {exc}",
            "seconds": round(time.perf_counter() - started, 3),
        }


def main() -> int:
    out: dict = {
        "started": date.today().isoformat(),
        "fy_wanted": latest_completed_indian_fy(),
        "names": [],
        "exchange_generic": {},
    }
    registry = load_company_source_registry()
    master = SecurityMasterService(load_default_catalog())
    transport = NsePublicHttp()
    nse_eod = NseEodService(transport, mode="LIVE")
    nse_primary = NsePrimaryEvidenceService(transport, mode="LIVE")
    bse_opener = build_opener(HTTPCookieProcessor(CookieJar()))

    t0 = time.perf_counter()
    try:
        bundle = nse_eod.fetch_latest()
        eod_ok = {
            "ok": True,
            "rows": len(bundle.rows),
            "trade_date": None if not bundle.rows else bundle.rows[0].trad_dt.isoformat(),
            "source_url": bundle.discovered.url,
            "seconds": round(time.perf_counter() - t0, 3),
        }
    except LookupError as exc:
        eod_ok = {
            "ok": False,
            "class": classify_failure(str(exc)),
            "reason": str(exc),
            "seconds": round(time.perf_counter() - t0, 3),
        }
        bundle = None
    out["nse_eod"] = eod_ok

    for url, label in (
        (SEBI_HOME, "sebi_home"),
        (MCA_HOME, "mca_home"),
        ("https://www.bseindia.com/", "bse_home"),
        ("https://nsearchives.nseindia.com/", "nse_archives_home"),
    ):
        out["exchange_generic"][label] = probe_url(transport, url)

    for ticker, isin in NAMES:
        row: dict = {"ticker": ticker, "isin": isin}
        record = registry.record(isin)
        row["registry"] = None if record is None else {
            "domain": record.official_domain,
            "ir": record.investor_relations_url,
            "financials": record.financial_results_url,
            "annual": record.annual_reports_url,
            "status": record.status,
            "verification_method": record.verification_method,
        }
        resolved = master.resolve(ticker, exchange="NSE", isin=isin, mic="XNSE")
        listing = resolved.identity
        row["identity"] = {
            "status": resolved.status,
            "company": None if listing is None else listing.company_name,
            "mic": None if listing is None else listing.mic,
            "listing_id": None if listing is None else listing.listing_id,
        }
        if listing is None:
            out["names"].append(row)
            continue

        if bundle is not None:
            matched = [r for r in bundle.rows if r.isin == isin and r.scty_srs == "EQ"]
            row["eod"] = {
                "matched": bool(matched),
                "price": None if not matched else str(matched[0].cls_pric),
                "trad_dt": None if not matched else matched[0].trad_dt.isoformat(),
            }
        else:
            row["eod"] = {"matched": False, "reason": "EOD bundle unavailable"}

        # NSE JSON routes already in the adapter.
        nse_routes = {}
        symbol = quote(ticker, safe="")
        for key, url in (
            ("quote_equity", f"{NSE_QUOTE_EQUITY_URL}?symbol={symbol}"),
            ("shareholding", f"{NSE_SHAREHOLDING_URL}?index=equities&symbol={symbol}"),
            ("financial_results", f"{NSE_FINANCIAL_RESULTS_URL}?index=equities&symbol={symbol}&period=Annual"),
            ("announcements", f"{NSE_ANNOUNCEMENTS_URL}?index=equities&symbol={symbol}"),
            ("annual_reports", f"{NSE_ANNUAL_REPORTS_URL}?index=equities&symbol={symbol}"),
        ):
            probe = probe_url(transport, url, referer=NSE_ALL_REPORTS)
            if probe.get("ok") and probe.get("kind") == "json":
                try:
                    payload = transport.get_bytes(url, referer=NSE_ALL_REPORTS)
                    probe["preview"] = json_preview(payload)
                    if key == "annual_reports":
                        parsed = json.loads(payload.decode("utf-8"))
                        docs = parsed if isinstance(parsed, list) else parsed.get("data") or parsed.get("dataList") or []
                        annual_hits = []
                        if isinstance(docs, list):
                            for item in docs[:12]:
                                if not isinstance(item, dict):
                                    continue
                                annual_hits.append(
                                    {
                                        k: item.get(k)
                                        for k in (
                                            "symbol",
                                            "fromYr",
                                            "toYr",
                                            "fy",
                                            "year",
                                            "fileName",
                                            "filePath",
                                            "file_name",
                                            "file_path",
                                            "desc",
                                            "companyName",
                                        )
                                        if k in item
                                    }
                                )
                        probe["annual_hits"] = annual_hits
                except Exception as exc:  # noqa: BLE001 — forensic only
                    probe["preview_error"] = str(exc)
            nse_routes[key] = probe
        row["nse_routes"] = nse_routes

        # Company IR registered URLs only — no guessed paths.
        ir_probes = []
        if record is not None:
            for label, url in (
                ("annual_reports_url", record.annual_reports_url),
                ("financial_results_url", record.financial_results_url),
                ("investor_relations_url", record.investor_relations_url),
            ):
                if not url:
                    ir_probes.append({"label": label, "url": None, "class": "not_registered"})
                    continue
                ir_probes.append({"label": label, **probe_company_ir(url, isin=isin, mic=listing.mic, registry=registry, transport=transport)})
        row["ir_routes"] = ir_probes

        # Existing acquisition path (14N-A reproduction with timings/failures).
        started = time.perf_counter()
        try:
            primary = nse_primary.fetch(listing)
            primary_elapsed = round(time.perf_counter() - started, 3)
            row["nse_primary"] = {
                "seconds": primary_elapsed,
                "issues": list(primary.issues)[:12],
                "fields": {
                    name: {
                        "status": item.semantic_status,
                        "as_of": None if item.as_of is None else item.as_of.isoformat(),
                        "locator": item.locator,
                        "basis": item.statement_basis,
                        "unit": item.raw_unit,
                    }
                    for name, item in primary.fields.items()
                },
                "announcement_docs": [
                    {"title": d.title, "kind": d.kind, "url": d.url, "as_of": None if d.as_of is None else d.as_of.isoformat()}
                    for d in primary.announcement_documents[:15]
                ],
                "announcement_count": len(primary.announcement_documents),
                "ca": [e.event_type for e in primary.capital_events],
            }
            payload = primary.announcement_payload
        except LookupError as exc:
            payload = None
            row["nse_primary"] = {
                "seconds": round(time.perf_counter() - started, 3),
                "class": classify_failure(str(exc)),
                "reason": str(exc),
            }

        started = time.perf_counter()
        acquired = acquire_primary_documents(
            listing,
            transport=transport,
            announcement_payload=payload,
            fetch_registered_ir=True,
        )
        row["acquisition"] = {
            "seconds": round(time.perf_counter() - started, 3),
            "timings": acquired.timings,
            "selected_url": acquired.selected_url,
            "issues": list(acquired.issues),
            "failures": [
                {
                    "url": f.url,
                    "reason": f.reason,
                    "http_status": f.http_status,
                    "class": classify_failure(f.reason, f.http_status),
                }
                for f in acquired.failures
            ],
            "documents": [
                {
                    "url": d.url,
                    "type": d.content_type,
                    "bytes": d.content_length,
                    "hash": d.document_hash,
                }
                for d in acquired.documents
            ],
            "fields": {
                name: {
                    "value_present": bool(item.value),
                    "status": item.semantic_status,
                    "as_of": None if item.as_of is None else item.as_of.isoformat(),
                    "locator": item.locator,
                    "basis": item.statement_basis,
                    "unit": item.raw_unit,
                    "currency": item.currency,
                }
                for name, item in acquired.fields.items()
            },
            "ca": [
                {
                    "type": e.event_type,
                    "date": e.event_date.isoformat() if e.event_date != date.max else "undated",
                    "capital_changing": e.capital_changing,
                }
                for e in acquired.capital_events
            ],
            "text_chars": len(acquired.sanitized_text or ""),
        }
        if acquired.sanitized_text:
            ctx = parse_document_context(acquired.sanitized_text)
            row["acquisition"]["document_context"] = {
                "currency": ctx.currency,
                "unit": ctx.unit_scale,
                "basis": ctx.statement_basis,
                "period_type": ctx.period_type,
                "period_end": None if ctx.period_end is None else ctx.period_end.isoformat(),
                "issues": list(ctx.issues),
            }

        # BSE: do not guess scrip codes. Try GetQuote by scripname if the API accepts ticker.
        bse_rows = []
        for url in (
            f"{BSE_GETQUOTE}?scripcode={ticker}",
            f"https://api.bseindia.com/BseIndiaAPI/api/GetScripHeaderData/w?scripcode={ticker}",
        ):
            started = time.perf_counter()
            request = Request(url, headers={"User-Agent": _UA, "Referer": "https://www.bseindia.com/"})
            try:
                with bse_opener.open(request, timeout=20) as response:
                    payload = response.read()
                bse_rows.append(
                    {
                        "url": url,
                        "ok": True,
                        "class": "retrieved",
                        "http_status": 200,
                        "bytes": len(payload),
                        "seconds": round(time.perf_counter() - started, 3),
                        "preview": json_preview(payload),
                    }
                )
            except HTTPError as exc:
                bse_rows.append(
                    {
                        "url": url,
                        "ok": False,
                        "class": classify_failure(f"HTTP {exc.code}", exc.code),
                        "http_status": exc.code,
                        "reason": str(exc),
                        "seconds": round(time.perf_counter() - started, 3),
                    }
                )
            except (URLError, OSError) as exc:
                bse_rows.append(
                    {
                        "url": url,
                        "ok": False,
                        "class": classify_failure(str(exc)),
                        "reason": f"{type(exc).__name__}: {exc}",
                        "seconds": round(time.perf_counter() - started, 3),
                    }
                )
        row["bse_routes"] = bse_rows

        out["names"].append(row)
        print(json.dumps({"ticker": ticker, "identity": row["identity"]["status"], "eod": row.get("eod"), "nse_classes": {k: v.get("class") for k, v in nse_routes.items()}, "ir": [{p.get("label"): p.get("class")} for p in ir_probes], "acq_selected": acquired.selected_url, "acq_failures": [f.http_status for f in acquired.failures]}, default=str), flush=True)

    dest = Path(__file__).with_suffix(".json")
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("WROTE", dest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
