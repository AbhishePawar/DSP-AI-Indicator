"""Composition routes — HTTP → DSPPlatform.compose_intelligence only."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from api_platform.api.composition_schemas import (
    AnalyseRequest,
    AnalyseResponse,
    ValidateResponse,
)
from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    resolve_access_token,
)
from api_platform.api.mappers import (
    CompositionApiError,
    map_pipeline_payload,
    map_platform_result,
)
from api_platform.api.validation import validate_analyse_request
from dsp_platform import CompositionInputError, build_composition_request
from dsp_platform.investment_provenance import (
    InvestmentProvenanceError,
    InvestmentProvenanceForbidden,
    build_investment_provenance,
    get_investment_provenance_store,
    new_analysis_id,
)

router = APIRouter(tags=["composition"])


@router.post("/analyse", response_model=AnalyseResponse)
def analyse(
    body: AnalyseRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> AnalyseResponse:
    """Run the platform composition pipeline; return public PipelineResult DTO.

    Authentication policy (intentional — P1-12):
    - Route itself does not hard-require JWT so Research Mode / fixture journeys
      remain usable when ``DSP_ENABLE_SECURITY`` is off (development).
    - When ``DSP_ENABLE_SECURITY`` is on, security middleware requires auth +
      ``ANALYZE_COMPANY`` before this handler runs.
    - Optional JWT stamps ownership on durable provenance; unowned provenance
      is not world-readable. Institutional export / provenance GET require an
      authenticated owner (or matching org) — public analyse cannot escalate
      into another principal's export trust chain.
    """
    correlation_id = getattr(request.state, "request_id", None)
    errors = validate_analyse_request(body)
    if errors:
        raise CompositionApiError(
            "request validation failed",
            error_code="VALIDATION_ERROR",
            status_code=422,
            validation_errors=errors,
            correlation_id=correlation_id,
        )

    try:
        composition_request = build_composition_request(
            ticker=body.ticker,
            company=body.company,
            exchange=body.exchange,
            current_market_price=body.current_market_price,
            financial_statements=body.financial_statements.model_dump(),
            valuation_signals=(
                body.valuation_signals.model_dump()
                if body.valuation_signals is not None
                else None
            ),
            stop_on_stage_failure=body.stop_on_stage_failure,
        )
    except CompositionInputError as exc:
        raise CompositionApiError(
            "invalid composition input",
            error_code="COMPOSITION_INPUT_ERROR",
            status_code=422,
            validation_errors=[str(exc)],
            correlation_id=correlation_id,
            detail=str(exc),
        ) from None

    platform_result = state.platform.compose_intelligence(composition_request)
    pipeline = platform_result.payload
    if pipeline is None:
        raise CompositionApiError(
            "composition returned no payload",
            error_code="COMPOSITION_EMPTY",
            status_code=502,
            correlation_id=correlation_id,
        )

    public_payload = map_pipeline_payload(pipeline)
    response = map_platform_result(
        platform_result,
        api_version=state.api_version,
        correlation_id=correlation_id,
        public_payload=public_payload,
    )

    if not platform_result.ok:
        failed = getattr(getattr(pipeline, "metadata", None), "failed_stage", None)
        # Still return 200 with ok=False for graceful degradation payloads;
        # structured errors remain in payload.errors / metadata.
        response.errors = list(response.errors) + [
            f"pipeline degraded; failed_stage={failed}"
        ]

    # P1-06 — durable investment provenance (server-authored only).
    _persist_investment_provenance(
        response=response,
        public_payload=public_payload if isinstance(public_payload, dict) else {},
        body=body,
        pipeline=pipeline,
        request=request,
        correlation_id=correlation_id,
    )

    # EPIC-011B — best-effort immutable snapshot capture AFTER pipeline completes.
    # Never alters engines, recommendation logic, or the analyse response contract.
    try:
        if os.getenv("DSP_RI_AUTO_CAPTURE", "1").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            capture_payload = (
                public_payload if isinstance(public_payload, dict) else {}
            )
            state.platform.capture_research_intelligence_snapshot(
                capture_payload,
                ticker=body.ticker,
                company=body.company or None,
                exchange=body.exchange,
                allow_duplicate=True,
            )
    except Exception:  # noqa: BLE001
        pass

    return response


def _actor_org_id(actor: dict[str, Any] | None) -> str | None:
    """Org from server-validated JWT only — never from client query params."""
    if not actor:
        return None
    user = actor.get("user") if isinstance(actor.get("user"), dict) else {}
    claims = user.get("claims") if isinstance(user.get("claims"), dict) else {}
    for key in ("org_id", "organization_id", "tenant_id"):
        raw = user.get(key) or claims.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


@router.get("/analyse/provenance/{analysis_id}")
def get_analyse_provenance(
    analysis_id: str,
    request: Request,
) -> dict[str, Any]:
    """P1-06 — retrieve durable investment provenance by analysis_id."""
    store = get_investment_provenance_store()
    store.ensure_fresh()
    actor = _optional_actor(request)
    try:
        record = store.get(
            analysis_id,
            actor_user_id=actor.get("user_id") if actor else None,
            org_id=_actor_org_id(actor),
        )
    except InvestmentProvenanceForbidden as exc:
        raise CompositionApiError(
            str(exc),
            error_code="PROVENANCE_FORBIDDEN",
            status_code=403,
            correlation_id=getattr(request.state, "request_id", None),
        ) from None
    if record is None:
        raise CompositionApiError(
            "investment provenance not found",
            error_code="PROVENANCE_NOT_FOUND",
            status_code=404,
            correlation_id=getattr(request.state, "request_id", None),
        )
    return {
        "ok": True,
        "capability": "investment_provenance",
        "audit_reference": record.analysis_id,
        "provenance": record.to_dict(),
        "api_version": "v1",
    }


@router.get("/analyse/provenance")
def list_analyse_provenance(
    request: Request,
    ticker: str = Query(min_length=1, max_length=32),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """P1-06 — list durable investment provenance rows for a ticker."""
    store = get_investment_provenance_store()
    store.ensure_fresh()
    actor = _optional_actor(request)
    rows = store.list_by_ticker(
        ticker,
        actor_user_id=actor.get("user_id") if actor else None,
        org_id=_actor_org_id(actor),
        limit=limit,
    )
    return {
        "ok": True,
        "capability": "investment_provenance",
        "ticker": ticker.strip().upper(),
        "count": len(rows),
        "items": [r.to_dict() for r in rows],
        "api_version": "v1",
    }


@router.post("/validate", response_model=ValidateResponse)
def validate_payload(
    body: AnalyseRequest,
    state: ApiState = Depends(get_api_state),
) -> ValidateResponse:
    """Validate analyse request shape only — no pipeline execution."""
    errors = validate_analyse_request(body)
    warnings: list[str] = []
    if body.exchange is None:
        warnings.append("exchange not provided")
    if body.current_market_price is not None or (
        body.valuation_signals is not None
        and body.valuation_signals.current_market_price is not None
    ):
        warnings.append(
            "price-only valuation path may run when ValuationEngine inputs "
            "are unavailable; client IV/MoS conclusions are never accepted"
        )
    return ValidateResponse(
        ok=len(errors) == 0,
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        api_version=state.api_version,
    )


def _persist_investment_provenance(
    *,
    response: AnalyseResponse,
    public_payload: dict[str, Any],
    body: AnalyseRequest,
    pipeline: Any,
    request: Request,
    correlation_id: str | None,
) -> None:
    """Append durable lineage; fail closed in production on persistence errors."""
    analysis_id = new_analysis_id()
    actor = _optional_actor(request)
    # P0-05 / P1-07 — owner from server-validated JWT only. Never stamp org
    # from client headers (forgeable). Org filter applies on owned reads when set.
    owner_user_id = actor.get("user_id") if actor else None
    # Org from server-validated JWT claims only — never client query/headers.
    org_id = None
    if actor:
        user = actor.get("user") if isinstance(actor.get("user"), dict) else {}
        claims = user.get("claims") if isinstance(user.get("claims"), dict) else {}
        for key in ("org_id", "organization_id", "tenant_id"):
            raw = user.get(key) or claims.get(key)
            if raw is not None and str(raw).strip():
                org_id = str(raw).strip()
                break
    fs_digest = {
        "period": body.financial_statements.period.model_dump(),
        "income_keys": sorted(
            (body.financial_statements.income_statement or {}).keys()
        ),
        "balance_keys": sorted(
            (body.financial_statements.balance_sheet or {}).keys()
        ),
        "cash_flow_keys": sorted(
            (body.financial_statements.cash_flow or {}).keys()
        ),
        "statement_metadata": dict(
            body.financial_statements.statement_metadata or {}
        ),
    }
    auth_trace = getattr(pipeline, "authenticated_valuation_trace", None)
    record = build_investment_provenance(
        public_payload=public_payload,
        ticker=body.ticker,
        company=body.company or "",
        exchange=body.exchange,
        correlation_id=correlation_id,
        analysis_id=analysis_id,
        owner_user_id=owner_user_id,
        org_id=org_id,
        authenticated_valuation_trace=auth_trace,
        financial_statements_digest=fs_digest,
    )
    store = get_investment_provenance_store()
    production = (os.environ.get("DSP_ENVIRONMENT") or "").lower() == "production"
    if production and type(store).__name__ == "InMemoryInvestmentProvenanceStore":
        raise CompositionApiError(
            "investment provenance persistence failed — "
            "auditable conclusion not claimed",
            error_code="AUDIT_PERSISTENCE_FAILED",
            status_code=503,
            validation_errors=[
                "P1-06: production requires durable DatabasePort provenance store"
            ],
            correlation_id=correlation_id,
        )
    try:
        store.append(record)
    except InvestmentProvenanceError as exc:
        if production:
            raise CompositionApiError(
                "investment provenance persistence failed — "
                "auditable conclusion not claimed",
                error_code="AUDIT_PERSISTENCE_FAILED",
                status_code=503,
                validation_errors=[str(exc)],
                correlation_id=correlation_id,
                detail=str(exc),
            ) from None
        response.provenance_persisted = False
        response.limitations = list(response.limitations) + [
            "P1-06: investment provenance not persisted (degraded non-production mode)"
        ]
        return
    except Exception as exc:  # noqa: BLE001
        if production:
            raise CompositionApiError(
                "investment provenance persistence failed — "
                "auditable conclusion not claimed",
                error_code="AUDIT_PERSISTENCE_FAILED",
                status_code=503,
                validation_errors=[str(exc)],
                correlation_id=correlation_id,
                detail=str(exc),
            ) from None
        response.provenance_persisted = False
        response.limitations = list(response.limitations) + [
            "P1-06: investment provenance not persisted (degraded non-production mode)"
        ]
        return

    response.analysis_id = analysis_id
    response.audit_reference = analysis_id
    response.provenance_persisted = True
    # Pydantic may copy payload on assignment — update the response object.
    payload = dict(response.payload or {})
    payload["analysis_id"] = analysis_id
    payload["audit_reference"] = analysis_id
    payload["provenance_persisted"] = True
    response.payload = payload
    public_payload["analysis_id"] = analysis_id
    public_payload["audit_reference"] = analysis_id
    public_payload["provenance_persisted"] = True


def _optional_actor(request: Request) -> dict[str, Any] | None:
    token = resolve_access_token(request)
    if not token:
        return None
    try:
        from auth import get_auth_service

        auth = get_auth_service()
        user = auth.current_user(token)
        uid = str(user.get("user_id") or "").strip()
        if not uid:
            return None
        return {"user_id": uid, "user": user}
    except Exception:  # noqa: BLE001
        return None

