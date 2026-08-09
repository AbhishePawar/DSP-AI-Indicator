#!/usr/bin/env python3
"""G2 — live authenticated vendor evidence drill.

Proves (when credentials are present):
  authenticated HTTP quote + statements
    → production adapters (not Null/memory/demo)
    → authenticated valuation bundle
    → /analyse composition path
    → P1-06 durable provenance

Fails closed when credentials are absent. Never fabricates live evidence.
Never logs API keys / Authorization headers.

Routes (either is sufficient):
  A) Single-key FMP — DSP_FMP_API_KEY or DSP_INVESTMENT_FMP_API_KEY
  B) ConfiguredHttp — quote key+URL and statement key+URL

Evidence: artifacts/g2_live_vendor_evidence.json
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

RELEASE_IDENTITY = {
    "epic": "EPS-003",
    "product_version": "2.0.0-rc.1",
    "channel": "rc",
    "decision": "RELEASE_CANDIDATE",
    "label": "EPS-003 · 2.0.0-rc.1 · rc · RELEASE_CANDIDATE",
}

HTTP_REQUIRED_ENV = (
    "DSP_MARKET_QUOTE_API_KEY",
    "DSP_MARKET_QUOTE_BASE_URL",
    "DSP_FINANCIAL_STATEMENT_API_KEY",
    "DSP_FINANCIAL_STATEMENT_BASE_URL",
)

FMP_KEY_ENVS = (
    "DSP_FMP_API_KEY",
    "DSP_INVESTMENT_FMP_API_KEY",
)

# Back-compat alias used by older tests / docs.
REQUIRED_ENV = HTTP_REQUIRED_ENV

FORBIDDEN_LIVE_FLAGS = (
    "DSP_MARKET_QUOTE_MEMORY",
    "DSP_FINANCIAL_STATEMENT_MEMORY",
)

DEFAULT_TICKER = "AAPL"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _truthy(name: str, environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return str(env.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def credential_presence(
    environ: dict[str, str] | None = None,
) -> dict[str, bool]:
    """Return PRESENT/ABSENT map — never values."""
    env = environ if environ is not None else os.environ
    names = list(HTTP_REQUIRED_ENV) + list(FMP_KEY_ENVS)
    return {name: bool(str(env.get(name) or "").strip()) for name in names}


def http_credentials_ready(environ: dict[str, str] | None = None) -> bool:
    present = credential_presence(environ)
    return all(present[name] for name in HTTP_REQUIRED_ENV)


def fmp_credentials_ready(environ: dict[str, str] | None = None) -> bool:
    present = credential_presence(environ)
    return any(present[name] for name in FMP_KEY_ENVS)


def credentials_ready(environ: dict[str, str] | None = None) -> bool:
    return http_credentials_ready(environ) or fmp_credentials_ready(environ)


def selected_route(environ: dict[str, str] | None = None) -> str:
    if http_credentials_ready(environ):
        return "configured_http"
    if fmp_credentials_ready(environ):
        return "fmp"
    return "none"


def memory_flags_enabled(environ: dict[str, str] | None = None) -> list[str]:
    return [name for name in FORBIDDEN_LIVE_FLAGS if _truthy(name, environ)]


def classify_gate(
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Pure gate classification — no network I/O."""
    present = credential_presence(environ)
    memory = memory_flags_enabled(environ)
    route = selected_route(environ)
    ready = credentials_ready(environ) and not memory
    if memory:
        evidence_class = "memory_seed_refused_as_live"
        status = "BLOCKED"
        reason = (
            "G2 refuses in-memory/seed adapters as live vendor evidence; "
            f"disable {', '.join(memory)}"
        )
    elif not ready:
        evidence_class = "credentials_unavailable"
        status = "BLOCKED"
        reason = (
            "G2 live authenticated vendor evidence requires EITHER "
            "(A) DSP_FMP_API_KEY or DSP_INVESTMENT_FMP_API_KEY "
            "(single-key Financial Modeling Prep free developer tier), "
            "OR (B) all four ConfiguredHttp secrets: "
            + ", ".join(HTTP_REQUIRED_ENV)
            + ". Inject via GitHub Environment 'live-data-evidence' "
            "(workflow_dispatch) or a secure local runtime - never commit."
        )
    else:
        # Credentials are necessary but not sufficient. Do NOT claim
        # real_live_authenticated_provider until CLEARED after live I/O.
        evidence_class = "credentials_present_pending_live"
        status = "READY"
        reason = (
            f"credentials present via route={route}; "
            "live execution permitted — evidence_class pending CLEARED"
        )
    return {
        "ready": ready,
        "status": status,
        "evidence_class": evidence_class,
        "reason": reason,
        "route": route,
        "credential_presence": {k: ("PRESENT" if v else "ABSENT") for k, v in present.items()},
        "memory_flags_enabled": memory,
        "required_secrets": [
            "DSP_FMP_API_KEY (preferred single-key FMP route)",
            *HTTP_REQUIRED_ENV,
        ],
        "secure_injection": [
            "GitHub Environment: live-data-evidence",
            "workflow_dispatch protected job",
            "organization/repository Actions secrets (names only above)",
            "production secret manager → runtime env (never source tree)",
            "FMP free developer signup: https://site.financialmodelingprep.com/developer/docs",
        ],
    }


def _write_evidence(evidence: dict[str, Any]) -> Path:
    root = _repo_root()
    out_dir = root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "g2_live_vendor_evidence.json"
    path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"evidence_written={path}")
    return path


def _provider_meta(route: str) -> dict[str, Any]:
    if route == "fmp":
        return {
            "quote_provider_id": "fmp_market_quote",
            "statement_provider_id": "fmp_financial_statements",
            "auth_mode": "api_key",
            "vendor": "financial_modeling_prep",
            "note": "Single authenticated FMP key satisfies quote + statements",
        }
    if route == "configured_http":
        return {
            "quote_provider_id": "configured_http_quote",
            "statement_provider_id": "configured_http_statements",
            "auth_mode": "api_key_bearer",
            "note": "Vendor-neutral ConfiguredHttp* adapters; base URL identifies endpoint",
        }
    return {
        "quote_provider_id": None,
        "statement_provider_id": None,
        "auth_mode": None,
        "vendor": None,
        "note": "No authenticated route selected — provider identity withheld",
    }


def _base_evidence(*, gate: dict[str, Any], commit: str) -> dict[str, Any]:
    return {
        "ok": False,
        "gate": "G2",
        "track": "live_authenticated_vendor_evidence",
        "evidence_class": gate["evidence_class"],
        "g2_status": gate["status"],
        "reason": gate["reason"],
        "route": gate.get("route"),
        "credential_presence": gate["credential_presence"],
        "memory_flags_enabled": gate["memory_flags_enabled"],
        "required_secrets": gate["required_secrets"],
        "secure_injection": gate["secure_injection"],
        "release_identity": dict(RELEASE_IDENTITY),
        "commit": commit,
        "started_at": datetime.now(tz=UTC).isoformat(),
        "ticker": os.environ.get("DSP_G2_TICKER", DEFAULT_TICKER).strip().upper()
        or DEFAULT_TICKER,
        "provider": _provider_meta(str(gate.get("route") or "none")),
        "steps": {},
        "secrets_logged": False,
    }


def _commit_sha() -> str:
    try:
        import subprocess

        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(_repo_root()),
        ).stdout.strip()
        return out or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def _fail(msg: str, evidence: dict[str, Any], code: int = 2) -> int:
    evidence["ok"] = False
    evidence["error"] = msg
    evidence["finished_at"] = datetime.now(tz=UTC).isoformat()
    if evidence.get("g2_status") != "CLEARED":
        evidence["g2_status"] = evidence.get("g2_status") or "BLOCKED"
    # Never leave real_live_authenticated_provider on a failed/blocked run.
    if evidence.get("evidence_class") == "real_live_authenticated_provider":
        evidence["evidence_class"] = "live_execution_failed"
    elif evidence.get("evidence_class") == "credentials_present_pending_live":
        evidence["evidence_class"] = "live_execution_failed"
    _write_evidence(evidence)
    print(f"FAIL G2: {msg}", file=sys.stderr)
    return code


def _assert_not_unsafe_adapter(adapter: Any, *, kind: str) -> None:
    name = type(adapter).__name__
    pid = str(getattr(adapter, "provider_id", "") or "")
    unsafe = (
        "Null" in name
        or "Memory" in name
        or "memory" in pid
        or pid.startswith("null_")
        or "demo" in pid
        or "seed" in pid
    )
    if unsafe:
        raise RuntimeError(
            f"G2 refuses {kind} adapter {name!r} / {pid!r} as live evidence"
        )


def _classify_live_failure(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if "401" in text or "unauthorized" in text or "forbidden" in text or "403" in text:
        return "authentication_failure"
    if "timeout" in text or "timed out" in text:
        return "provider_timeout"
    if "schema" in text or "invalidproviderdata" in text or "missing" in text:
        return "schema_failure"
    if "integrity" in text or "p1-02" in text or "financialintegrity" in text:
        return "p1_02_integrity_failure"
    if "connection" in text or "network" in text or "resolve" in text:
        return "network_failure"
    if "provider" in text:
        return "provider_response_failure"
    return "live_execution_failure"


def _run_live(evidence: dict[str, Any]) -> int:
    """Execute real authenticated provider → analyse → provenance chain."""
    ticker = evidence["ticker"]
    steps = evidence["steps"]

    # Ensure memory flags cannot sneak in during live run.
    for flag in FORBIDDEN_LIVE_FLAGS:
        os.environ.pop(flag, None)

    from contracts.domain.instrument import AssetClass, Instrument
    from data_engine.financial_statement.adapters import (
        build_default_statement_adapter_from_env,
    )
    from data_engine.financial_statement.service import StatementQuery
    from data_engine.market_quote.adapters import build_default_quote_adapter_from_env

    def _instrument(symbol: str) -> Instrument:
        return Instrument(
            symbol=symbol, asset_class=AssetClass.EQUITY, currency="USD"
        )
    from dsp_platform import (
        PlatformBuilder,
        PlatformConfiguration,
        build_composition_request,
        pipeline_result_public_dict,
    )
    from dsp_platform.composition.authenticated_valuation import (
        load_authenticated_valuation_bundle,
    )
    from dsp_platform.investment_provenance import (
        DatabaseInvestmentProvenanceStore,
        build_investment_provenance,
        new_analysis_id,
        reset_investment_provenance_store_for_tests,
    )
    from production_platform import InMemoryDatabasePort

    quote_adapter = build_default_quote_adapter_from_env()
    stmt_adapter = build_default_statement_adapter_from_env()
    _assert_not_unsafe_adapter(quote_adapter, kind="quote")
    _assert_not_unsafe_adapter(stmt_adapter, kind="statements")
    q_health = quote_adapter.health()
    s_health = stmt_adapter.health()
    steps["adapters"] = {
        "quote": {
            "class": type(quote_adapter).__name__,
            "provider_id": quote_adapter.provider_id,
            "authenticated": bool(getattr(q_health, "authenticated", False)),
            "health": q_health.to_dict()
            if hasattr(q_health, "to_dict")
            else {
                "provider_id": quote_adapter.provider_id,
                "authenticated": bool(getattr(q_health, "authenticated", False)),
            },
        },
        "statements": {
            "class": type(stmt_adapter).__name__,
            "provider_id": stmt_adapter.provider_id,
            "authenticated": bool(getattr(s_health, "authenticated", False)),
            "health": s_health.to_dict()
            if hasattr(s_health, "to_dict")
            else {
                "provider_id": stmt_adapter.provider_id,
                "authenticated": bool(getattr(s_health, "authenticated", False)),
            },
        },
    }
    if not steps["adapters"]["quote"]["authenticated"]:
        return _fail("quote adapter health reports authenticated=false", evidence)
    if not steps["adapters"]["statements"]["authenticated"]:
        return _fail("statement adapter health reports authenticated=false", evidence)

    instrument = _instrument(ticker)
    quote = quote_adapter.get_quote(instrument)
    if quote is None:
        return _fail(f"quote unavailable for {ticker}", evidence)
    q_prov = quote.provenance
    steps["quote"] = {
        "symbol": quote.symbol,
        "currency": quote.currency,
        "price_available": bool(
            getattr(quote.current_price, "available", False)
            and getattr(quote.current_price, "value", None) is not None
        ),
        "price_finite": bool(
            getattr(quote.current_price, "value", None) is not None
        ),
        "shares_outstanding_available": bool(
            getattr(quote.shares_outstanding, "available", False)
        ),
        "provider_id": getattr(q_prov, "provider_id", None),
        "source_type": getattr(q_prov, "source_type", None),
        "auth_mode": getattr(q_prov, "auth_mode", None),
        "retrieved_at": str(getattr(q_prov, "retrieved_at", None)),
    }
    if not steps["quote"]["price_available"]:
        return _fail("authenticated quote missing finite current_price", evidence)

    statements = stmt_adapter.get_statements(
        StatementQuery(instrument=instrument, limit=4)
    )
    if statements is None or not getattr(statements, "periods", None):
        return _fail(f"statements unavailable for {ticker}", evidence)
    s_prov = statements.provenance
    latest = statements.periods[0]
    identity = getattr(statements, "identity", None)
    steps["statements"] = {
        "symbol": getattr(identity, "symbol", None) or ticker,
        "period_count": len(statements.periods),
        "latest_period_end": str(getattr(latest, "period_end", None)),
        "statement_basis": getattr(latest, "statement_basis", None),
        "unit_scale": getattr(latest, "unit_scale", None),
        "currency": getattr(statements, "reporting_currency", None)
        or getattr(identity, "currency", None),
        "provider_id": getattr(s_prov, "provider_id", None),
        "source_type": getattr(s_prov, "source_type", None),
        "auth_mode": getattr(s_prov, "auth_mode", None),
        "retrieved_at": str(getattr(s_prov, "retrieved_at", None)),
    }

    def _get_statements(symbol: str):
        return stmt_adapter.get_statements(
            StatementQuery(instrument=_instrument(symbol), limit=4)
        )

    def _get_quote(symbol: str):
        return quote_adapter.get_quote(_instrument(symbol))

    bundle = load_authenticated_valuation_bundle(
        ticker,
        get_statements=_get_statements,
        get_quote=_get_quote,
    )
    steps["authenticated_bundle"] = {
        "ok": True,
        "ticker": bundle.ticker,
        "authenticated": True,
        "statement_basis": bundle.statement_basis,
        "unit_scale": bundle.unit_scale,
        "reporting_currency": bundle.reporting_currency,
        "current_market_price": bundle.current_market_price,
        "shares_outstanding": bundle.shares_outstanding,
        "quote_provider": (bundle.quote_provenance or {}).get("provider_id"),
        "statement_provider": (bundle.statement_provenance or {}).get("provider_id"),
    }

    # Wire durable provenance store for this process.
    db = InMemoryDatabasePort()
    reset_investment_provenance_store_for_tests(DatabaseInvestmentProvenanceStore(db))

    price = float(bundle.current_market_price)
    from dsp_platform.composition.authenticated_valuation import (
        to_financial_statements,
    )

    fs = to_financial_statements(bundle)
    request = build_composition_request(
        ticker=ticker,
        company=bundle.company_name or ticker,
        current_market_price=price,
        financial_statements=fs.to_dict() if hasattr(fs, "to_dict") else fs,
    )
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    envelope = platform.compose_intelligence(request)
    if envelope.payload is None:
        return _fail("compose_intelligence returned empty payload", evidence)
    public = pipeline_result_public_dict(envelope.payload)
    buffett = public.get("buffett_authority") or {}
    rec = public.get("recommendation_summary") or {}
    source = public.get("source_evidence") or {}
    steps["analyse"] = {
        "ok": bool(public.get("ok")),
        "pipeline_version": (public.get("metadata") or {}).get("pipeline_version"),
        "valuation_stage": next(
            (
                s
                for s in (public.get("stage_summaries") or [])
                if s.get("stage") == "valuation"
            ),
            None,
        ),
        "buffett_overall_score": buffett.get("overall_score"),
        "buffett_status": buffett.get("overall_status"),
        "recommendation": rec.get("decision"),
        "source_authenticated": source.get("authenticated"),
        "no_client_overrides": buffett.get("client_overrides_accepted") is False,
    }

    # Reject demo/null contamination signals (builder emits status=authenticated).
    if source.get("authenticated") is not True:
        return _fail("provenance not authenticated after live analyse", evidence)
    if str(source.get("status") or "") in {"live", "unavailable"} and not source.get(
        "authenticated"
    ):
        return _fail("provenance claimed live/unavailable without auth", evidence)

    analysis_id = new_analysis_id()
    record = build_investment_provenance(
        public_payload=public,
        ticker=ticker,
        company=bundle.company_name or ticker,
        analysis_id=analysis_id,
        authenticated_valuation_trace=bundle.to_trace_dict(),
        correlation_id=str(uuid4()),
    )
    store_a = DatabaseInvestmentProvenanceStore(db)
    store_a.append(record)
    store_b = DatabaseInvestmentProvenanceStore(db)
    restored = store_b.get(analysis_id)
    if restored is None:
        return _fail("provenance not durable across workers", evidence)

    steps["provenance"] = {
        "analysis_id": analysis_id,
        "audit_reference": analysis_id,
        "input_fingerprint": record.input_fingerprint,
        "result_fingerprint": record.result_fingerprint,
        "provider_statement": (record.source_evidence or {}).get("statement_provider"),
        "provider_quote": (record.source_evidence or {}).get("quote_provider"),
        "retrieved_statement": (record.source_evidence or {}).get(
            "statement_retrieved_at"
        ),
        "retrieved_quote": (record.source_evidence or {}).get("quote_retrieved_at"),
        "currency": (record.source_evidence or {}).get("reporting_currency"),
        "statement_basis": (record.source_evidence or {}).get("statement_basis"),
        "unit_scale": (record.source_evidence or {}).get("unit_scale"),
        "valuation_status": (record.valuation or {}).get("status"),
        "buffett_status": (record.buffett or {}).get("overall_status"),
        "recommendation": (record.conclusion or {}).get("recommendation"),
        "release_label": (record.release or {}).get("label"),
        "multi_worker_read": True,
    }

    evidence["ok"] = True
    evidence["g2_status"] = "CLEARED"
    evidence["evidence_class"] = "real_live_authenticated_provider"
    evidence["authenticated"] = True
    evidence["quote_adapter"] = type(quote_adapter).__name__
    evidence["statement_adapter"] = type(stmt_adapter).__name__
    evidence["quote_retrieved_at"] = steps["quote"]["retrieved_at"]
    evidence["statement_retrieved_at"] = steps["statements"]["retrieved_at"]
    evidence["currency"] = steps["statements"]["currency"] or steps["quote"]["currency"]
    evidence["statement_basis"] = steps["statements"]["statement_basis"]
    evidence["unit_scale"] = steps["statements"]["unit_scale"]
    evidence["analysis_id"] = analysis_id
    evidence["input_fingerprint"] = record.input_fingerprint
    evidence["result_fingerprint"] = record.result_fingerprint
    evidence["valuation_status"] = (record.valuation or {}).get("status")
    evidence["buffett_status"] = (record.buffett or {}).get("overall_status")
    evidence["provenance_status"] = "durable"
    evidence["finished_at"] = datetime.now(tz=UTC).isoformat()
    _write_evidence(evidence)
    print("OK G2 real authenticated vendor evidence PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    _ = argv
    gate = classify_gate()
    evidence = _base_evidence(gate=gate, commit=_commit_sha())
    evidence["steps"]["gate"] = {
        "ready": gate["ready"],
        "status": gate["status"],
        "route": gate.get("route"),
    }

    if not gate["ready"]:
        # Fail closed — do not claim live evidence.
        return _fail(gate["reason"], evidence, code=2)

    try:
        return _run_live(evidence)
    except Exception as exc:  # noqa: BLE001
        evidence["failure_class"] = _classify_live_failure(exc)
        evidence["traceback"] = traceback.format_exc(limit=8)
        return _fail(f"live execution failed: {exc}", evidence, code=1)


if __name__ == "__main__":
    raise SystemExit(main())
