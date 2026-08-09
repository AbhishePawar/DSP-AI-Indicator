"""P1-12 — bind research object / report / export to server investment provenance.

Institutional export must represent the exact owned analysis identified by
``analysis_id``. Client valuation, Buffett, and provenance fields are never
authoritative.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_provenance import (
    InvestmentProvenanceForbidden,
    InvestmentProvenanceRecord,
    get_investment_provenance_store,
)

__all__ = [
    "TrustChainError",
    "actor_org_id",
    "load_owned_provenance",
    "bind_analysis_payload_to_provenance",
    "assert_research_object_bound",
    "assert_report_bound",
    "requires_trust_binding",
]


class TrustChainError(Exception):
    """Fail-closed trust-chain violation."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


def actor_org_id(actor: Mapping[str, Any] | None) -> str | None:
    """Org from server-validated JWT only."""
    if not actor:
        return None
    user = actor.get("user") if isinstance(actor.get("user"), dict) else {}
    claims = user.get("claims") if isinstance(user.get("claims"), dict) else {}
    for key in ("org_id", "organization_id", "tenant_id"):
        raw = (user or {}).get(key) or (claims or {}).get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def requires_trust_binding(
    *,
    analysis_payload: Mapping[str, Any] | None,
    valuation_signals: Mapping[str, Any] | None,
) -> bool:
    """True when the request carries investment conclusions that must be bound."""
    if isinstance(valuation_signals, Mapping) and valuation_signals:
        for key in (
            "intrinsic_value_per_share",
            "margin_of_safety",
            "current_market_price",
            "fair_value",
            "enterprise_value",
        ):
            if valuation_signals.get(key) is not None:
                return True
    if not isinstance(analysis_payload, Mapping) or not analysis_payload:
        return False
    if analysis_payload.get("buffett_authority") is not None:
        return True
    if analysis_payload.get("server_valuation") is not None:
        return True
    if analysis_payload.get("analysis_id") or analysis_payload.get("audit_reference"):
        return True
    rec = analysis_payload.get("recommendation_summary")
    if isinstance(rec, Mapping) and any(
        rec.get(k) is not None
        for k in (
            "margin_of_safety",
            "decision",
            "score",
            "label",
            "confidence",
            "intrinsic_value_per_share",
        )
    ):
        return True
    committee = analysis_payload.get("committee_summary")
    if isinstance(committee, Mapping) and any(
        committee.get(k) is not None for k in ("decision", "score", "confidence")
    ):
        return True
    stages = analysis_payload.get("stage_summaries")
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, Mapping):
                continue
            if str(stage.get("stage") or "") == "valuation" and stage.get("has_result"):
                return True
    return False


def load_owned_provenance(
    analysis_id: str | None,
    actor: Mapping[str, Any],
) -> InvestmentProvenanceRecord:
    aid = (analysis_id or "").strip()
    if not aid:
        raise TrustChainError(
            "analysis_id is required to bind export to server analysis",
            error_code="TRUST_CHAIN_ANALYSIS_ID_REQUIRED",
            status_code=400,
        )
    store = get_investment_provenance_store()
    store.ensure_fresh()
    user_id = str(actor.get("user_id") or "").strip() or None
    try:
        record = store.get(
            aid,
            actor_user_id=user_id,
            org_id=actor_org_id(actor),
        )
    except InvestmentProvenanceForbidden as exc:
        raise TrustChainError(
            str(exc) or "investment provenance access denied",
            error_code="TRUST_CHAIN_FORBIDDEN",
            status_code=403,
        ) from None
    if record is None:
        raise TrustChainError(
            "investment provenance not found for analysis_id",
            error_code="TRUST_CHAIN_NOT_FOUND",
            status_code=404,
        )
    return record


def bind_analysis_payload_to_provenance(
    client_payload: Mapping[str, Any] | None,
    record: InvestmentProvenanceRecord,
    *,
    symbol: str,
) -> dict[str, Any]:
    """Return analysis payload with server-owned conclusions only."""
    ticker = symbol.strip().upper()
    if record.ticker and record.ticker != ticker:
        raise TrustChainError(
            "analysis_id ticker does not match export symbol",
            error_code="TRUST_CHAIN_TICKER_MISMATCH",
            status_code=409,
        )

    base = dict(client_payload or {})
    for key in ("analysis_id", "audit_reference"):
        raw = base.get(key)
        if raw is not None and str(raw).strip() and str(raw).strip() != record.analysis_id:
            raise TrustChainError(
                "client analysis_id does not match bound provenance",
                error_code="TRUST_CHAIN_ANALYSIS_ID_MISMATCH",
                status_code=409,
            )

    _reject_forged_conclusions(base, record)

    # Strip client conclusion surfaces — re-inject from provenance only.
    base.pop("buffett_authority", None)
    base.pop("server_valuation", None)
    base.pop("committee_summary", None)
    base.pop("recommendation_summary", None)

    conclusion = dict(record.conclusion or {})
    valuation = dict(record.valuation or {})
    buffett = dict(record.buffett or {})

    base["ok"] = bool(conclusion.get("pipeline_ok", base.get("ok", True)))
    base["analysis_id"] = record.analysis_id
    base["audit_reference"] = record.analysis_id
    base["result_fingerprint"] = record.result_fingerprint
    base["input_fingerprint"] = record.input_fingerprint
    base["provenance_persisted"] = True
    base["buffett_authority"] = buffett
    base["recommendation_summary"] = {
        "decision": conclusion.get("recommendation"),
        "score": conclusion.get("recommendation_score"),
        "label": conclusion.get("recommendation_label"),
        "confidence": conclusion.get("recommendation_confidence"),
        "margin_of_safety": valuation.get("margin_of_safety"),
    }
    if conclusion.get("committee_decision") is not None:
        base["committee_summary"] = {
            "decision": conclusion.get("committee_decision"),
            "score": conclusion.get("committee_score"),
            "confidence": conclusion.get("committee_confidence"),
        }
    base["server_valuation"] = {
        "authority": "server",
        "available": bool(valuation.get("available")),
        "status": valuation.get("status") or "unavailable",
        "score": valuation.get("score"),
        "label": valuation.get("label"),
        "current_market_price": valuation.get("market_price"),
        "margin_of_safety": valuation.get("margin_of_safety"),
        "intrinsic_value_per_share": None
        if not valuation.get("available")
        else valuation.get("intrinsic_value_per_share"),
        "reason": valuation.get("reason"),
    }
    # Never allow client valuation stage inventing availability when provenance says no.
    if not valuation.get("available"):
        stages = list(base.get("stage_summaries") or [])
        rewritten: list[Any] = []
        for stage in stages:
            if not isinstance(stage, Mapping):
                rewritten.append(stage)
                continue
            if str(stage.get("stage") or "") != "valuation":
                rewritten.append(dict(stage))
                continue
            item = dict(stage)
            item["has_result"] = False
            item["status"] = "unavailable"
            item["score"] = None
            rewritten.append(item)
        if rewritten:
            base["stage_summaries"] = rewritten
    base["trust_chain"] = {
        "bound_analysis_id": record.analysis_id,
        "result_fingerprint": record.result_fingerprint,
        "input_fingerprint": record.input_fingerprint,
        "authority": "server_provenance",
        "release": dict(record.release or {}),
        "evidence_class_source": "investment_provenance",
    }
    return base


def assert_research_object_bound(
    research_object: Mapping[str, Any],
    record: InvestmentProvenanceRecord,
) -> None:
    audit = research_object.get("audit")
    payload = None
    if isinstance(audit, Mapping):
        payload = audit.get("payload") if isinstance(audit.get("payload"), Mapping) else audit
    bound_id = None
    if isinstance(payload, Mapping):
        bound_id = payload.get("analysis_id") or payload.get("audit_reference")
    meta = research_object.get("metadata")
    if bound_id is None and isinstance(meta, Mapping):
        bound_id = meta.get("analysis_id")
    if bound_id is None:
        # Also accept trust stamp on nested provenance.audit
        prov = research_object.get("provenance")
        if isinstance(prov, Mapping):
            audit_prov = prov.get("audit")
            if isinstance(audit_prov, Mapping):
                bound_id = audit_prov.get("analysis_id")
    if str(bound_id or "").strip() != record.analysis_id:
        raise TrustChainError(
            "research object is not bound to the requested analysis_id",
            error_code="TRUST_CHAIN_OBJECT_MISMATCH",
            status_code=409,
        )
    _reject_unavailable_fabrication_in_section(
        research_object.get("valuation"),
        record,
        section_name="valuation",
    )
    _reject_unavailable_fabrication_in_section(
        research_object.get("margin_of_safety"),
        record,
        section_name="margin_of_safety",
    )


def assert_report_bound(
    report: Mapping[str, Any],
    record: InvestmentProvenanceRecord,
) -> None:
    audit = report.get("audit")
    payload: Mapping[str, Any] | None = None
    if isinstance(audit, Mapping):
        raw = audit.get("payload")
        payload = raw if isinstance(raw, Mapping) else audit
    bound_id = None
    fingerprint = None
    if isinstance(payload, Mapping):
        bound_id = (
            payload.get("analysis_id")
            or payload.get("audit_reference")
            or payload.get("bound_analysis_id")
        )
        source_meta = payload.get("source_metadata")
        if isinstance(source_meta, Mapping):
            bound_id = bound_id or source_meta.get("analysis_id")
            fingerprint = source_meta.get("result_fingerprint")
        trust = payload.get("trust_chain")
        if isinstance(trust, Mapping):
            bound_id = bound_id or trust.get("bound_analysis_id")
            fingerprint = fingerprint or trust.get("result_fingerprint")
    if str(bound_id or "").strip() != record.analysis_id:
        raise TrustChainError(
            "export report is not bound to the requested analysis_id",
            error_code="TRUST_CHAIN_REPORT_MISMATCH",
            status_code=409,
        )
    if (
        fingerprint
        and record.result_fingerprint
        and str(fingerprint) != str(record.result_fingerprint)
    ):
        raise TrustChainError(
            "export report result_fingerprint does not match provenance",
            error_code="TRUST_CHAIN_FINGERPRINT_MISMATCH",
            status_code=409,
        )
    _reject_unavailable_fabrication_in_section(
        report.get("valuation"),
        record,
        section_name="valuation",
    )
    _reject_unavailable_fabrication_in_section(
        report.get("margin_of_safety"),
        record,
        section_name="margin_of_safety",
    )
    _reject_forged_buffett_in_report(report, record)


def _reject_forged_conclusions(
    client: Mapping[str, Any],
    record: InvestmentProvenanceRecord,
) -> None:
    valuation = dict(record.valuation or {})
    buffett = dict(record.buffett or {})
    conclusion = dict(record.conclusion or {})

    client_buffett = client.get("buffett_authority")
    if isinstance(client_buffett, Mapping) and client_buffett:
        for key in (
            "overall_score",
            "overall_label",
            "recommendation",
            "committee_decision",
        ):
            if (
                client_buffett.get(key) is not None
                and buffett.get(key) is not None
                and client_buffett.get(key) != buffett.get(key)
            ):
                raise TrustChainError(
                    "forged Buffett fields rejected",
                    error_code="TRUST_CHAIN_FORGED_BUFFETT",
                    status_code=422,
                )
            if client_buffett.get(key) is not None and buffett.get(key) is None:
                # Client invents Buffett conclusion when server has none.
                if key in {"overall_score", "recommendation", "committee_decision"}:
                    raise TrustChainError(
                        "forged Buffett fields rejected",
                        error_code="TRUST_CHAIN_FORGED_BUFFETT",
                        status_code=422,
                    )

    client_rec = client.get("recommendation_summary")
    if isinstance(client_rec, Mapping):
        if (
            client_rec.get("decision") is not None
            and conclusion.get("recommendation") is not None
            and client_rec.get("decision") != conclusion.get("recommendation")
        ):
            raise TrustChainError(
                "forged recommendation fields rejected",
                error_code="TRUST_CHAIN_FORGED_RECOMMENDATION",
                status_code=422,
            )
        mos = client_rec.get("margin_of_safety")
        if mos is not None and not valuation.get("available"):
            raise TrustChainError(
                "unavailable valuation cannot be exported as a fabricated number",
                error_code="TRUST_CHAIN_FORGED_VALUATION",
                status_code=422,
            )
        if (
            mos is not None
            and valuation.get("margin_of_safety") is not None
            and float(mos) != float(valuation["margin_of_safety"])
        ):
            raise TrustChainError(
                "forged valuation fields rejected",
                error_code="TRUST_CHAIN_FORGED_VALUATION",
                status_code=422,
            )

    server_val = client.get("server_valuation")
    if isinstance(server_val, Mapping):
        iv = server_val.get("intrinsic_value_per_share")
        if iv is not None and not valuation.get("available"):
            raise TrustChainError(
                "unavailable valuation cannot be exported as a fabricated number",
                error_code="TRUST_CHAIN_FORGED_VALUATION",
                status_code=422,
            )


def _section_payload(section: Any) -> Mapping[str, Any] | None:
    if not isinstance(section, Mapping):
        return None
    payload = section.get("payload")
    if isinstance(payload, Mapping):
        return payload
    return section if section.get("available") is not None else None


def _reject_unavailable_fabrication_in_section(
    section: Any,
    record: InvestmentProvenanceRecord,
    *,
    section_name: str,
) -> None:
    valuation = dict(record.valuation or {})
    if valuation.get("available"):
        return
    payload = _section_payload(section)
    if not isinstance(payload, Mapping):
        return
    for key in (
        "intrinsic_value_per_share",
        "margin_of_safety",
        "fair_value",
        "enterprise_value",
        "score",
    ):
        value = payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            raise TrustChainError(
                f"unavailable {section_name} cannot be exported as a fabricated number",
                error_code="TRUST_CHAIN_FORGED_VALUATION",
                status_code=422,
            )


def _reject_forged_buffett_in_report(
    report: Mapping[str, Any],
    record: InvestmentProvenanceRecord,
) -> None:
    buffett = dict(record.buffett or {})
    # Buffett may live under recommendation / explainability / business_quality payloads.
    for name in ("recommendation", "explainability", "business_quality"):
        payload = _section_payload(report.get(name))
        if not isinstance(payload, Mapping):
            continue
        for key in ("overall_score", "buffett_score", "buffett_overall_score"):
            value = payload.get(key)
            if value is None:
                continue
            server = buffett.get("overall_score")
            if server is None:
                raise TrustChainError(
                    "forged Buffett fields rejected",
                    error_code="TRUST_CHAIN_FORGED_BUFFETT",
                    status_code=422,
                )
            if value != server:
                raise TrustChainError(
                    "forged Buffett fields rejected",
                    error_code="TRUST_CHAIN_FORGED_BUFFETT",
                    status_code=422,
                )
