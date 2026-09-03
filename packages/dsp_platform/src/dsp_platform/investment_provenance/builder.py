"""Build server-authoritative investment provenance from analyse outputs (P1-06)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from dsp_platform.investment_provenance.fingerprint import canonical_fingerprint
from dsp_platform.investment_provenance.models import (
    RELEASE_IDENTITY,
    InvestmentProvenanceRecord,
)
from dsp_platform.investment_provenance.redaction import redact_secrets

__all__ = [
    "build_investment_provenance",
    "source_evidence_from_trace",
    "new_analysis_id",
]


def new_analysis_id() -> str:
    return str(uuid4())


def source_evidence_from_trace(trace: Mapping[str, Any] | None) -> dict[str, Any]:
    """Slim public source evidence — never invents 'live' without connector proof."""
    if not trace:
        return {
            "authenticated": False,
            "status": "unavailable",
            "reason": "authenticated valuation bundle not available for this run",
        }
    stmt = dict(trace.get("statement_provenance") or {})
    quote = dict(trace.get("quote_provenance") or {})
    share_count = dict(trace.get("share_count_provenance") or {})
    authenticated = bool(trace.get("authenticated"))
    return redact_secrets(
        {
            "authenticated": authenticated,
            "status": "authenticated" if authenticated else "unavailable",
            "ticker": trace.get("ticker"),
            "reporting_currency": trace.get("reporting_currency"),
            "period_kind": trace.get("period_kind"),
            "statement_basis": trace.get("statement_basis"),
            "unit_scale": trace.get("unit_scale"),
            "current_market_price": trace.get("current_market_price"),
            "shares_outstanding": trace.get("shares_outstanding"),
            "statement_provider": (
                stmt.get("provider_id")
                or stmt.get("provider_name")
                or stmt.get("provider")
                or stmt.get("source")
            ),
            "statement_source_type": stmt.get("source_type") or stmt.get("kind"),
            "statement_retrieved_at": stmt.get("retrieved_at") or stmt.get("as_of"),
            "quote_provider": (
                quote.get("provider_id")
                or quote.get("provider_name")
                or quote.get("provider")
                or quote.get("source")
            ),
            "quote_source_type": quote.get("source_type") or quote.get("kind"),
            "quote_retrieved_at": quote.get("retrieved_at") or quote.get("as_of"),
            "share_count_provider": (
                share_count.get("provider_id")
                or share_count.get("provider_name")
                or share_count.get("provider")
                or share_count.get("source")
            ),
            "share_count_source_type": share_count.get("source_type")
            or share_count.get("kind"),
            "share_count_retrieved_at": share_count.get("retrieved_at")
            or share_count.get("as_of"),
            "statement_provenance": stmt,
            "quote_provenance": quote,
            "share_count_provenance": share_count,
        }
    )


def build_investment_provenance(
    *,
    public_payload: Mapping[str, Any],
    ticker: str,
    company: str = "",
    exchange: str | None = None,
    correlation_id: str | None = None,
    analysis_id: str | None = None,
    owner_user_id: str | None = None,
    org_id: str | None = None,
    authenticated_valuation_trace: Mapping[str, Any] | None = None,
    financial_statements_digest: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> InvestmentProvenanceRecord:
    """Construct provenance solely from server pipeline outputs.

    Client-supplied audit/valuation/Buffett/recommendation fields must never
    be passed here as authoritative evidence.
    """
    now = created_at or datetime.now(tz=UTC).isoformat()
    aid = analysis_id or new_analysis_id()
    meta = dict(public_payload.get("metadata") or {})
    stage_summaries = list(public_payload.get("stage_summaries") or [])
    by_stage = {str(s.get("stage")): s for s in stage_summaries if isinstance(s, dict)}
    valuation_stage = by_stage.get("valuation") or {}
    rec_summary = dict(public_payload.get("recommendation_summary") or {})
    committee_summary = dict(public_payload.get("committee_summary") or {})
    buffett = dict(public_payload.get("buffett_authority") or {})
    source = source_evidence_from_trace(
        authenticated_valuation_trace
        or public_payload.get("source_evidence")
        or public_payload.get("authenticated_valuation_trace")
    )

    financial_stage = by_stage.get("financial") or {}
    financial_validation = {
        "status": financial_stage.get("status") or "unavailable",
        "available": bool(financial_stage.get("has_result")),
        "score": financial_stage.get("score"),
        "label": financial_stage.get("label"),
        "statement_basis": source.get("statement_basis"),
        "unit_scale": source.get("unit_scale"),
        "currency": source.get("reporting_currency"),
        "integrity": (
            "authenticated_bundle"
            if source.get("authenticated")
            else "client_or_degraded_path"
        ),
    }

    val_status = str(valuation_stage.get("status") or "unavailable")
    val_available = val_status in {"succeeded", "degraded"} and bool(
        valuation_stage.get("has_result")
    )
    mos = rec_summary.get("margin_of_safety")
    valuation = {
        "status": val_status if val_available else "unavailable",
        "available": val_available,
        "score": valuation_stage.get("score") if val_available else None,
        "label": valuation_stage.get("label") if val_available else None,
        "market_price": source.get("current_market_price"),
        "margin_of_safety": mos,
        "recommendation_linked": rec_summary.get("decision"),
        "reason": (
            None if val_available else "valuation stage unavailable or incomplete"
        ),
    }

    conclusion = {
        "recommendation": rec_summary.get("decision"),
        "recommendation_score": rec_summary.get("score"),
        "recommendation_label": rec_summary.get("label"),
        "recommendation_confidence": rec_summary.get("confidence"),
        "committee_decision": committee_summary.get("decision"),
        "committee_score": committee_summary.get("score"),
        "committee_confidence": committee_summary.get("confidence"),
        "pipeline_ok": bool(public_payload.get("ok")),
    }

    # Prefer authenticated server trace for fingerprint authority; client
    # statement digests are non-authoritative attachment only.
    auth_trace = dict(authenticated_valuation_trace or {})
    input_fp_payload = redact_secrets(
        {
            "ticker": ticker.strip().upper(),
            "company": company,
            "exchange": exchange,
            "authenticated_valuation_trace": {
                k: auth_trace.get(k)
                for k in (
                    "ticker",
                    "reporting_currency",
                    "period_kind",
                    "statement_basis",
                    "unit_scale",
                    "current_market_price",
                    "shares_outstanding",
                    "statement_provenance",
                    "quote_provenance",
                    "share_count_provenance",
                )
                if auth_trace
            }
            or None,
            "client_financial_statements_digest": financial_statements_digest or {},
            "source_evidence": {
                k: source.get(k)
                for k in (
                    "authenticated",
                    "statement_basis",
                    "unit_scale",
                    "reporting_currency",
                    "period_kind",
                    "current_market_price",
                    "shares_outstanding",
                    "statement_provider",
                    "quote_provider",
                    "share_count_provider",
                )
            },
        }
    )
    result_fp_payload = redact_secrets(
        {
            "valuation": valuation,
            "buffett": {
                "overall_score": buffett.get("overall_score"),
                "overall_label": buffett.get("overall_label"),
                "overall_status": buffett.get("overall_status"),
                "recommendation": buffett.get("recommendation"),
                "committee_decision": buffett.get("committee_decision"),
                "factors": buffett.get("factors"),
            },
            "conclusion": conclusion,
            "pipeline_version": meta.get("pipeline_version"),
            "package_versions": meta.get("package_versions") or {},
        }
    )

    return InvestmentProvenanceRecord(
        analysis_id=aid,
        created_at=now,
        ticker=ticker.strip().upper(),
        company=company or "",
        exchange=exchange,
        correlation_id=correlation_id,
        owner_user_id=owner_user_id,
        org_id=org_id,
        calculated_at=now,
        source_evidence=source,
        financial_validation=financial_validation,
        valuation=valuation,
        buffett=redact_secrets(buffett),
        conclusion=conclusion,
        release=dict(RELEASE_IDENTITY),
        pipeline_version=meta.get("pipeline_version"),
        platform_version=meta.get("platform_version"),
        package_versions=dict(meta.get("package_versions") or {}),
        input_fingerprint=canonical_fingerprint(input_fp_payload),
        result_fingerprint=canonical_fingerprint(result_fp_payload),
    )
