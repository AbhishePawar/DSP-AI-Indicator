#!/usr/bin/env python3
"""G2 provider configuration diagnostic (no secret values, optional network).

Reports:
  provider configured / base URL / API key / production adapter selected

Never prints API keys. Distinguishes missing credential vs invalid configuration
vs network / auth / schema failures when --probe is set and credentials exist.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _present(name: str) -> bool:
    return bool(str(os.environ.get(name) or "").strip())


def diagnose(*, probe: bool = False, ticker: str = "AAPL") -> dict[str, Any]:
    http_quote_key = _present("DSP_MARKET_QUOTE_API_KEY")
    http_quote_url = _present("DSP_MARKET_QUOTE_BASE_URL")
    http_stmt_key = _present("DSP_FINANCIAL_STATEMENT_API_KEY")
    http_stmt_url = _present("DSP_FINANCIAL_STATEMENT_BASE_URL")
    fmp_key = _present("DSP_FMP_API_KEY") or _present("DSP_INVESTMENT_FMP_API_KEY")

    http_ready = http_quote_key and http_quote_url and http_stmt_key and http_stmt_url
    route = "configured_http" if http_ready else ("fmp" if fmp_key else "none")
    provider_configured = route != "none"

    report: dict[str, Any] = {
        "provider_configured": "yes" if provider_configured else "no",
        "route": route,
        "base_url_configured": "yes"
        if (http_ready or fmp_key)
        else "no",
        "api_key_configured": "yes" if (http_ready or fmp_key) else "no",
        "production_adapter_selected": "unknown",
        "credential_presence": {
            "DSP_FMP_API_KEY": "PRESENT" if _present("DSP_FMP_API_KEY") else "ABSENT",
            "DSP_INVESTMENT_FMP_API_KEY": (
                "PRESENT" if _present("DSP_INVESTMENT_FMP_API_KEY") else "ABSENT"
            ),
            "DSP_MARKET_QUOTE_API_KEY": "PRESENT" if http_quote_key else "ABSENT",
            "DSP_MARKET_QUOTE_BASE_URL": "PRESENT" if http_quote_url else "ABSENT",
            "DSP_FINANCIAL_STATEMENT_API_KEY": "PRESENT" if http_stmt_key else "ABSENT",
            "DSP_FINANCIAL_STATEMENT_BASE_URL": "PRESENT" if http_stmt_url else "ABSENT",
        },
        "classification": "missing_credential"
        if not provider_configured
        else "configured",
        "dsp_environment": os.environ.get("DSP_ENVIRONMENT", ""),
        "probe": None,
    }

    # Select adapters without printing secrets.
    try:
        from data_engine.financial_statement.adapters import (
            build_default_statement_adapter_from_env,
        )
        from data_engine.market_quote.adapters import build_default_quote_adapter_from_env

        quote = build_default_quote_adapter_from_env()
        stmt = build_default_statement_adapter_from_env()
        q_name = type(quote).__name__
        s_name = type(stmt).__name__
        unsafe = any(
            tok in n.lower()
            for n in (q_name, s_name)
            for tok in ("null", "memory", "demo", "seed", "fake")
        )
        report["production_adapter_selected"] = "no" if unsafe else "yes"
        report["adapters"] = {
            "quote_class": q_name,
            "quote_provider_id": getattr(quote, "provider_id", None),
            "quote_authenticated": bool(getattr(quote.health(), "authenticated", False)),
            "statement_class": s_name,
            "statement_provider_id": getattr(stmt, "provider_id", None),
            "statement_authenticated": bool(
                getattr(stmt.health(), "authenticated", False)
            ),
        }
        if not provider_configured:
            report["classification"] = "missing_credential"
            report["production_adapter_selected"] = "no"
        elif unsafe:
            report["classification"] = "invalid_configuration"
    except Exception as exc:  # noqa: BLE001
        report["classification"] = (
            "missing_credential" if not provider_configured else "invalid_configuration"
        )
        report["adapter_error"] = f"{type(exc).__name__}: {exc}"
        report["production_adapter_selected"] = "no"
        return report

    if not probe or not provider_configured:
        return report

    # Optional live probe — never log secrets.
    probe_result: dict[str, Any] = {"ticker": ticker.upper(), "ok": False}
    try:
        from contracts.domain.instrument import AssetClass, Instrument
        from data_engine.financial_statement.service import StatementQuery

        instrument = Instrument(
            symbol=ticker.upper(),
            asset_class=AssetClass.EQUITY,
            currency="USD",
        )
        q = quote.get_quote(instrument)
        if q is None:
            probe_result["classification"] = "provider_response_failure"
            probe_result["detail"] = "quote returned None"
            report["probe"] = probe_result
            report["classification"] = "provider_response_failure"
            return report
        s = stmt.get_statements(StatementQuery(instrument=instrument, limit=2))
        if s is None or not s.periods:
            probe_result["classification"] = "provider_response_failure"
            probe_result["detail"] = "statements returned empty"
            report["probe"] = probe_result
            report["classification"] = "provider_response_failure"
            return report
        probe_result.update(
            {
                "ok": True,
                "classification": "ok",
                "quote_provider_id": q.provenance.provider_id,
                "statement_provider_id": s.provenance.provider_id,
                "quote_retrieved_at": str(q.provenance.retrieved_at),
                "statement_retrieved_at": str(s.provenance.retrieved_at),
                "currency": s.reporting_currency or q.currency,
                "period_count": len(s.periods),
                "price_available": bool(
                    q.current_price.available and q.current_price.value is not None
                ),
            }
        )
        report["probe"] = probe_result
        report["classification"] = "ok"
    except Exception as exc:  # noqa: BLE001
        text = f"{type(exc).__name__}: {exc}".lower()
        if "401" in text or "unauthorized" in text or "403" in text:
            cls = "authentication_failure"
        elif "timeout" in text or "timed out" in text:
            cls = "provider_timeout"
        elif "invalidproviderdata" in text or "schema" in text:
            cls = "schema_failure"
        elif "integrity" in text or "p1-02" in text:
            cls = "p1_02_integrity_failure"
        elif "connection" in text or "network" in text or "resolve" in text:
            cls = "network_failure"
        else:
            cls = "provider_response_failure"
        probe_result["classification"] = cls
        probe_result["detail"] = f"{type(exc).__name__}: {exc}"
        report["probe"] = probe_result
        report["classification"] = cls
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Attempt live provider calls when credentials are configured",
    )
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON only",
    )
    args = parser.parse_args(argv)
    report = diagnose(probe=args.probe, ticker=args.ticker)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"provider configured = {report['provider_configured']}")
        print(f"base URL configured = {report['base_url_configured']}")
        print(f"API key configured = {report['api_key_configured']}")
        print(f"production adapter selected = {report['production_adapter_selected']}")
        print(f"route = {report['route']}")
        print(f"classification = {report['classification']}")
        for name, label in report["credential_presence"].items():
            print(f"{name}={label}")
        if report.get("probe") is not None:
            print(f"probe = {json.dumps(report['probe'], sort_keys=True)}")
    return 0 if report["provider_configured"] == "yes" else 2


if __name__ == "__main__":
    # Ensure repo packages resolve when run as a script.
    root = _repo_root()
    sys.path[:0] = [
        str(root / "packages" / "data_engine" / "src"),
        str(root / "packages" / "contracts" / "src"),
    ]
    raise SystemExit(main())
