"""Analysis routes — HTTP → DSPPlatform.analyze_company only."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import AnalyzeCompanyRequest, ApiResponse
from api_platform.api.tenant_isolation import stamp_report_owner
from contracts import Instrument
from contracts.enums import AssetClass

try:
    from llm_adapters.orchestrator import UserResearchRequest
except ImportError:  # pragma: no cover - optional during partial installs
    UserResearchRequest = None  # type: ignore[misc, assignment]

router = APIRouter(tags=["analysis"])


def _asset_class(value: str) -> AssetClass:
    cleaned = value.strip().lower()
    try:
        return AssetClass(cleaned)
    except ValueError as exc:
        msg = f"unsupported asset_class: {value!r}"
        raise ApiValidationError(msg) from exc


@router.post("/analyze/company", response_model=ApiResponse)
def analyze_company(
    body: AnalyzeCompanyRequest,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> ApiResponse:
    """Delegate single-company analysis to ``DSPPlatform.analyze_company``.

    P1-07 — reports are stamped with the authenticated owner only.
    """
    if body.end < body.start:
        raise ApiValidationError("end date must be on or after start date")

    owner = str(auth.get("user_id") or "").strip()
    if not owner:
        raise ApiValidationError("authentication required")

    instrument = Instrument(
        symbol=body.symbol.strip().upper(),
        asset_class=_asset_class(body.asset_class),
        currency=body.currency.strip().upper(),
    )
    request = state.platform.make_request(
        instrument,
        body.start,
        body.end,
        include_fundamentals=body.include_fundamentals,
        include_economic=body.include_economic,
        include_valuation=body.include_valuation,
        allow_partial=body.allow_partial,
    )
    result = state.platform.analyze_company(
        request, as_decision_pack=body.as_decision_pack
    )

    report_id = f"rpt-{uuid4().hex[:12]}"
    state.reports.put(
        report_id,
        stamp_report_owner(
            {
                "capability": result.capability,
                "payload": result.payload,
                "ok": result.ok,
            },
            owner,
        ),
    )

    serialized_result = _serialize_payload(result.payload)
    limitations = list(result.limitations)
    payload = {
        "report_id": report_id,
        "result": serialized_result,
    }

    # Run the private, methodology-driven research loop against the same
    # deterministic DSP backend. Only its client-safe pack is allowed to cross
    # this boundary; prompts, provider identities, and raw responses stay in
    # the orchestrator's private result.
    research_pack: object | None = None
    if state.research_orchestrator is not None and UserResearchRequest is not None:
        try:
            research = state.research_orchestrator.run(
                UserResearchRequest(
                    symbol=instrument.symbol,
                    question="Explain the validated company analysis.",
                    exchange=instrument.asset_class.value,
                    request_id=report_id,
                )
            )
            research_pack = research.to_public().to_dict()
            if research.status.value != "accepted":
                limitations.append("AI research validation failed closed; deterministic result returned.")
        except Exception:  # noqa: BLE001 — deterministic analysis remains available
            limitations.append("AI research unavailable; deterministic result returned.")

    # AI is an explanation layer over the already validated DSP result. The
    # service owns provider routing, dual-provider verification, fallback, and
    # prompt privacy; the HTTP response receives only client-safe narrative.
    if state.copilot_service is not None and result.ok:
        try:
            explanation = state.copilot_service.complete(
                question_id="company_analysis",
                freeform=(
                    "Explain the validated company analysis concisely. "
                    "Do not invent or alter financial facts."
                ),
                    request={"symbol": instrument.symbol},
                    response={
                        "result": serialized_result,
                        "validated_research": research_pack,
                    },
                )
            payload["explanation"] = {
                "content": explanation.content,
                "citations": explanation.citations,
                "unavailable": explanation.unavailable,
            }
            limitations.extend(explanation.limitations)
        except Exception:  # noqa: BLE001 — analysis remains available without AI
            limitations.append("AI explanation unavailable; deterministic result returned.")

    return ApiResponse(
        ok=result.ok,
        capability=result.capability,
        payload=payload,
        limitations=limitations,
        errors=list(result.errors),
        api_version=state.api_version,
        platform_version=result.metadata.version,
    )


def _serialize_payload(payload: object) -> object:
    if payload is None:
        return None
    if hasattr(payload, "model_dump"):
        return payload.model_dump()  # type: ignore[no-any-return]
    if hasattr(payload, "__dict__"):
        data = {k: v for k, v in vars(payload).items() if not k.startswith("_")}
        # Best-effort JSON-friendly projection for frozen dataclasses.
        out: dict[str, object] = {}
        for key, value in data.items():
            if hasattr(value, "value"):
                out[key] = value.value
            elif hasattr(value, "symbol"):
                out[key] = {
                    "symbol": getattr(value, "symbol", None),
                    "asset_class": getattr(
                        getattr(value, "asset_class", None), "value", None
                    ),
                    "currency": getattr(value, "currency", None),
                }
            else:
                try:
                    out[key] = value
                except Exception:  # noqa: BLE001
                    out[key] = repr(value)
        return out
    return repr(payload)
