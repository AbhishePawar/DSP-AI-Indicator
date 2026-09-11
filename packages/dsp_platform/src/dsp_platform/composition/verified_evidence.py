"""SIMPLE-14M — verified official evidence → DSP composition inputs.

This is the only /analyse data path. Commercial quote/statement providers
are not called from here.
"""

from __future__ import annotations

import os
from typing import Any

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from data_engine.connector_framework.production_profile import is_production_environment
from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.dsp_gate import analysis_from_dataset, dsp_gate
from data_engine.official_research.judge import EvidenceJudge
from data_engine.official_research.models import ResearchRequest
from data_engine.official_research.nse_eod import (
    NseEodService,
    NseHttpTransport,
    NsePublicHttp,
)
from data_engine.official_research.nse_primary import NsePrimaryEvidenceService
from data_engine.official_research.orchestrator import (
    FINANCIAL_FIELDS,
    ResearchOrchestrator,
)
from data_engine.official_research.verified_dataset import VerifiedDataset
from data_engine.security_master.catalog import load_default_catalog
from data_engine.security_master.service import SecurityMasterService
from dsp_platform.composition.authenticated_valuation import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationBundle,
    AuthenticatedValuationError,
    load_authenticated_valuation_bundle,
    snapshot_from_statement,
    to_financial_statements,
)
from dsp_platform.composition.context import ExecutionContext
from valuation import MarketSnapshot

__all__ = [
    "VERIFIED_DATASET_KEY",
    "DSP_ANALYSIS_KEY",
    "dataset_to_bundle",
    "preload_verified_evidence",
]

VERIFIED_DATASET_KEY = "verified_dataset"
DSP_ANALYSIS_KEY = "dsp_analysis"
_AUTH_BUNDLE_KEY = "authenticated_valuation_bundle"
_AUTH_ERROR_KEY = "authenticated_valuation_error"
_AUTH_STATEMENTS_KEY = "authenticated_financial_statements"


def _auth_unavailable(detail: str | None) -> str:
    """Keep the P1-10 canonical marker while preserving the research diagnostic."""
    text = str(detail or "").strip()
    if not text:
        return DATA_UNAVAILABLE
    if DATA_UNAVAILABLE in text:
        return text
    if text.startswith("("):
        return f"{DATA_UNAVAILABLE} {text}"
    return f"{DATA_UNAVAILABLE} ({text})"


class _UnavailableNseHttp:
    """Test/default transport that does not contact NSE or any vendor."""

    def get_bytes(self, url: str, *, referer: str | None = None) -> bytes:
        _ = url, referer
        raise LookupError("official NSE EOD transport not injected")


def _research_mode(request: Any, *, production: bool) -> str:
    if production:
        requested = str(getattr(request, "research_mode", None) or "LIVE").upper()
        if requested == "MOCK":
            return "MOCK"  # caller must refuse before DSP
        return "LIVE"
    explicit = getattr(request, "research_mode", None)
    if explicit in {"LIVE", "MOCK"}:
        return explicit
    if os.environ.get("DSP_LIVE_NSE_EOD") == "1":
        return "LIVE"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return "MOCK"
    return "LIVE"


def _nse_services(
    request: Any, *, mode: str
) -> tuple[NseEodService, NsePrimaryEvidenceService | None]:
    injected = getattr(request, "nse_eod", None)
    if injected is not None:
        return injected, getattr(request, "nse_primary", None)
    transport: NseHttpTransport
    live_allowed = os.environ.get("DSP_LIVE_NSE_EOD") == "1"
    if mode == "LIVE" and live_allowed:
        transport = NsePublicHttp()
        return NseEodService(transport, mode=mode), NsePrimaryEvidenceService(
            transport, mode=mode
        )
    transport = _UnavailableNseHttp()
    return NseEodService(transport, mode=mode), None


def preload_verified_evidence(ctx: ExecutionContext) -> None:
    """Identity → official evidence → verified dataset. Never calls Upstox/FMP/Yahoo."""
    production = is_production_environment()
    mode = _research_mode(ctx.request, production=production)
    if production and mode == "MOCK":
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(
            "MOCK evidence cannot enter production"
        )
        return
    if production and getattr(ctx.request, "nse_eod", None) is not None:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(
            "injected NSE transport cannot enter production"
        )
        return

    ticker = str(ctx.request.ticker or "").strip()
    company = str(ctx.request.company or "").strip()
    isin = str(getattr(ctx.request, "isin", None) or "").strip() or None
    mic = str(getattr(ctx.request, "mic", None) or "").strip() or None
    exchange = str(getattr(ctx.request, "exchange", None) or "").strip() or None

    # P1-09 CI fixture only — DSPFIX memory quote/statements, never G2 / never LIVE NSE.
    if not production:
        from dsp_platform.p109_e2e_fixture import (
            P109_EVIDENCE_CLASS,
            P109_FIXTURE_TICKER,
        )

        if ticker.upper() == P109_FIXTURE_TICKER:
            try:
                bundle = load_authenticated_valuation_bundle(
                    ticker, exchange=exchange or "NYSE"
                )
            except AuthenticatedValuationError:
                bundle = None
            if bundle is not None:
                ctx.results[_AUTH_BUNDLE_KEY] = bundle
                try:
                    ctx.results[_AUTH_STATEMENTS_KEY] = to_financial_statements(bundle)
                except AuthenticatedValuationError as exc:
                    ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(str(exc))
                    ctx.results.pop(_AUTH_BUNDLE_KEY, None)
                    return
                trace = bundle.to_trace_dict()
                trace["evidence_class"] = P109_EVIDENCE_CLASS
                trace["g2_claim"] = False
                ctx.results["authenticated_valuation_trace"] = trace
                return

    query = ticker or company or isin or ""
    if not query:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable("identity required")
        return

    master = getattr(ctx.request, "security_master", None) or SecurityMasterService(
        load_default_catalog()
    )
    nse_eod, nse_primary = _nse_services(ctx.request, mode=mode)
    orch = ResearchOrchestrator(
        security_master=master,
        nse_eod=nse_eod,
        nse_primary=nse_primary,
        production=production,
    )
    fields = ("eod_close",) + FINANCIAL_FIELDS
    extra_fields = getattr(ctx.request, "research_fields", None)
    if extra_fields:
        fields = tuple(dict.fromkeys(fields + tuple(extra_fields)))
    document_text = getattr(ctx.request, "document_text", None)
    document_url = getattr(ctx.request, "document_url", None)
    events: tuple[CapitalEvent, ...] = tuple(
        getattr(ctx.request, "capital_events", ()) or ()
    )
    request = ResearchRequest(
        ticker=ticker or None,
        company=company or None,
        isin=isin,
        mic=mic,
        exchange=exchange,
        fields=fields,
        mode=mode,  # type: ignore[arg-type]
        document_url=document_url,
        candidate_urls=tuple(getattr(ctx.request, "candidate_urls", ()) or ()),
    )
    e2e = orch.analyse(
        request,
        corporate_actions=events,
        document_text=document_text,
    )
    extra = tuple(getattr(ctx.request, "extra_evidence", ()) or ())
    dataset = e2e.dataset
    if extra:
        judge = EvidenceJudge()
        research = orch._to_research_result(e2e, request)
        dataset = judge.build_verified_dataset(
            research, extra=extra, production=production, capital_events=events
        )
    if dataset is None:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(
            e2e.detail or f"identity {e2e.identity_status}"
        )
        ctx.results["authenticated_valuation_trace"] = {
            "official_research": e2e.to_public_dict(),
            "identity_status": e2e.identity_status,
            "ticker": ticker,
            "isin": isin,
            "mic": mic,
            "unresolved": list(e2e.unresolved),
            "mode": mode,
        }
        return
    gate = dsp_gate(dataset)
    analysis = analysis_from_dataset(dataset, gate=gate)
    ctx.results[VERIFIED_DATASET_KEY] = dataset
    ctx.results[DSP_ANALYSIS_KEY] = analysis
    trace = _trace_from_dataset(dataset, gate.blocked_reason)
    trace["official_research"] = e2e.to_public_dict()
    ctx.results["authenticated_valuation_trace"] = trace

    if dataset.identity_status not in {"VERIFIED"}:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(
            f"identity {dataset.identity_status}"
        )
        return
    if not gate.allowed:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(
            gate.blocked_reason
            or dataset.valuation_gate.detail
            or "VALUATION UNAVAILABLE"
        )
        return
    try:
        bundle = dataset_to_bundle(dataset, method_names=gate.allowed_methods)
    except AuthenticatedValuationError as exc:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(str(exc))
        return
    ctx.results[_AUTH_BUNDLE_KEY] = bundle
    try:
        ctx.results[_AUTH_STATEMENTS_KEY] = to_financial_statements(bundle)
    except AuthenticatedValuationError as exc:
        ctx.results[_AUTH_ERROR_KEY] = _auth_unavailable(str(exc))
        ctx.results.pop(_AUTH_BUNDLE_KEY, None)


def dataset_to_bundle(
    dataset: VerifiedDataset,
    *,
    method_names: tuple[str, ...],
) -> AuthenticatedValuationBundle:
    """Map VERIFIED fields only. No OP→EBIT, no previous-close-as-current."""
    _ = method_names
    if dataset.identity is None or dataset.identity_status != "VERIFIED":
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (identity not VERIFIED)")
    if dataset.mode == "MOCK" and is_production_environment():
        raise AuthenticatedValuationError(
            _auth_unavailable("MOCK evidence cannot enter production")
        )
    identity = dataset.identity
    price = dataset.price
    if dataset.price_status != "VERIFIED" or price is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (verified labeled price unavailable)"
        )
    if price.price_kind in {"PREVIOUS_CLOSE", "UNKNOWN"}:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (price_kind={price.price_kind} cannot enter valuation)"
        )
    shares = dataset.shares
    if dataset.shares_status != "VERIFIED" or shares is None or shares.shares <= 0:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (verified shares outstanding unavailable)"
        )
    if shares.semantic_type != "TOTAL_OUTSTANDING":
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share_semantic={shares.semantic_type} is not TOTAL_OUTSTANDING)"
        )
    financials = dataset.financials
    if financials is None or financials.period_end is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (verified financials unavailable)"
        )

    def _f(name: str) -> float | None:
        raw = dataset.verified_decimal(name)
        return None if raw is None else float(raw)

    equity = _f("equity")
    net_income = _f("net_income")
    cfo = _f("cfo")
    capex = _f("capex")
    if equity is None and net_income is None and cfo is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (required verified statement fields missing)"
        )

    extras: list[tuple[str, float]] = []
    ebit = _f("ebit")
    if ebit is not None:
        extras.append(("ebit", ebit))
    operating = _f("operating_profit")
    # Never alias operating profit as EBIT.

    exchange = (
        "NSE"
        if identity.mic == "XNSE"
        else ("BSE" if identity.mic == "XBOM" else identity.mic)
    )
    instrument = Instrument(
        symbol=identity.ticker,
        asset_class=AssetClass.EQUITY,
        currency=identity.currency,
        name=identity.company_name,
        exchange=exchange,
        isin=identity.isin,
    )
    period_end = financials.period_end
    statement = FundamentalStatement(
        instrument=instrument,
        period_end=period_end,
        period_type=StatementPeriodType.ANNUAL,
        fiscal_year=int(period_end.year),
        currency=identity.currency,
        revenue=_f("revenue"),
        operating_income=operating,
        net_income=net_income,
        total_assets=_f("total_assets"),
        total_liabilities=_f("total_liabilities"),
        total_equity=equity,
        cash_and_equivalents=_f("cash"),
        total_debt=_f("debt"),
        operating_cash_flow=cfo,
        capital_expenditures=None if capex is None else abs(capex),
        extra_line_items=tuple(extras),
    )
    snapshot = snapshot_from_statement(instrument, statement)
    market_cap = float(price.price) * float(shares.shares)
    quote_prov = {
        "provider_id": "official_nse_eod",
        "provider_name": "NSE UDiFF EOD",
        "source_type": "exchange_eod",
        "source": price.source,
        "retrieved_at": price.retrieved_at.isoformat(),
        "as_of": price.as_of.isoformat(),
        "price_kind": price.price_kind,
        "raw_price_field": price.raw_price_field,
        "isin": identity.isin,
        "mic": identity.mic,
    }
    stmt_prov = {
        "provider_id": "primary_evidence",
        "provider_name": "verified official evidence",
        "source_type": "company_ir",
        "retrieved_at": shares.last_verified_at.isoformat(),
        "as_of": financials.period_end.isoformat() if financials.period_end else None,
        "statement_basis": financials.statement_basis,
        "unit_scale": financials.unit_scale,
    }
    return AuthenticatedValuationBundle(
        ticker=identity.ticker,
        financial_snapshot=snapshot,
        market_snapshot=MarketSnapshot(market_cap=market_cap, as_of=price.as_of),
        current_market_price=float(price.price),
        shares_outstanding=float(shares.shares),
        reporting_currency=identity.currency,
        statement_provenance=stmt_prov,
        quote_provenance=quote_prov,
        period_kind="annual",
        statement_basis=financials.statement_basis or "unknown",
        unit_scale=financials.unit_scale or "actual",
        company_name=identity.company_name,
        isin=identity.isin,
        mic=identity.mic,
        price_kind=price.price_kind,
        price_as_of=price.as_of,
        price_retrieved_at=price.retrieved_at,
        valuation_methods=method_names,
    )


def _trace_from_dataset(
    dataset: VerifiedDataset, blocked: str | None
) -> dict[str, Any]:
    public = dataset.to_public_dict()
    price = public.get("price") or {}
    identity = public.get("identity") or {}
    return {
        "authenticated": dataset.price_status == "VERIFIED",
        "ticker": identity.get("ticker"),
        "isin": identity.get("isin"),
        "mic": identity.get("mic"),
        "company_name": identity.get("company_name"),
        "reporting_currency": identity.get("currency"),
        "current_market_price": None if not price else price.get("price"),
        "price_kind": None if not price else price.get("price_kind"),
        "price_as_of": None if not price else price.get("as_of"),
        "raw_price_field": None if not price else price.get("raw_price_field"),
        "shares_outstanding": (
            None
            if public.get("shares") is None
            else public["shares"].get("shares_outstanding")
        ),
        "valuation_status": dataset.valuation_gate.status,
        "valuation_detail": dataset.valuation_gate.detail,
        "blocked": blocked,
        "mode": dataset.mode,
        "identity_status": dataset.identity_status,
        "price_status": dataset.price_status,
        "shares_status": dataset.shares_status,
        "unresolved": list(dataset.unresolved),
        "verified_dataset": public,
        "quote_provenance": {
            "provider_id": "official_nse_eod",
            "source_type": "exchange_eod",
            "price_kind": None if not price else price.get("price_kind"),
            "as_of": None if not price else price.get("as_of"),
            "retrieved_at": None if not price else price.get("retrieved_at"),
        },
        "statement_provenance": {
            "provider_id": "primary_evidence",
            "source_type": "company_ir",
        },
    }
