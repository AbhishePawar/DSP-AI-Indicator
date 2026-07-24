"""Analysis routes — HTTP → DSPPlatform.analyze_company only."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import AnalyzeCompanyRequest, ApiResponse
from contracts import Instrument
from contracts.enums import AssetClass

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
) -> ApiResponse:
    """Delegate single-company analysis to ``DSPPlatform.analyze_company``."""
    if body.end < body.start:
        raise ApiValidationError("end date must be on or after start date")

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
        {
            "capability": result.capability,
            "payload": result.payload,
            "ok": result.ok,
        },
    )

    payload = {
        "report_id": report_id,
        "result": _serialize_payload(result.payload),
    }
    return ApiResponse(
        ok=result.ok,
        capability=result.capability,
        payload=payload,
        limitations=list(result.limitations),
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
        data = {
            k: v
            for k, v in vars(payload).items()
            if not k.startswith("_")
        }
        # Best-effort JSON-friendly projection for frozen dataclasses.
        out: dict[str, object] = {}
        for key, value in data.items():
            if hasattr(value, "value"):
                out[key] = getattr(value, "value")
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
