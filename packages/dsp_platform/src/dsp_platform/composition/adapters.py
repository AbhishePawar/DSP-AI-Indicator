"""Public composition input adapters — JSON-friendly → CompositionRequest.

Used by the HTTP layer so ``api_platform`` never imports analytical packages.
No scoring or recommendation logic lives here.
"""

from __future__ import annotations

from typing import Any, Mapping

from financial import FinancialStatements
from investment_recommendation import ValuationSignals

from dsp_platform.composition.models import CompositionRequest, PipelineResult
from dsp_platform.composition.pipeline import EXECUTION_ORDER, PipelineStage
from dsp_platform.composition.versions import COMPOSITION_PIPELINE_VERSION

__all__ = [
    "build_composition_request",
    "composition_capability_manifest",
    "composition_package_versions",
    "pipeline_result_public_dict",
]


class CompositionInputError(ValueError):
    """Invalid composition input payload (validation before orchestration)."""


def build_composition_request(
    *,
    ticker: str = "",
    company: str = "",
    current_market_price: float | None = None,
    financial_statements: Mapping[str, Any] | None = None,
    valuation_signals: Mapping[str, Any] | None = None,
    stop_on_stage_failure: bool = False,
) -> CompositionRequest:
    """Build a ``CompositionRequest`` from JSON-compatible mappings.

    Raises:
        CompositionInputError: when required financial statement fields are
            missing or malformed.
    """
    statements_obj: FinancialStatements | None = None
    if financial_statements is not None:
        try:
            statements_obj = FinancialStatements.from_dict(dict(financial_statements))
        except Exception as exc:  # noqa: BLE001 — map to public input error
            raise CompositionInputError(
                f"invalid financial_statements: {exc}"
            ) from exc

    signals_obj: ValuationSignals | None = None
    if valuation_signals is not None:
        try:
            signals_obj = ValuationSignals(
                intrinsic_value_per_share=_opt_float(
                    valuation_signals.get("intrinsic_value_per_share")
                ),
                current_market_price=_opt_float(
                    valuation_signals.get("current_market_price")
                ),
                margin_of_safety=_opt_float(valuation_signals.get("margin_of_safety")),
                premium_discount=_opt_float(valuation_signals.get("premium_discount")),
                confidence=float(valuation_signals.get("confidence", 0.55)),
            )
        except CompositionInputError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CompositionInputError(
                f"invalid valuation_signals: {exc}"
            ) from exc

    return CompositionRequest(
        financial_statements=statements_obj,
        current_market_price=current_market_price,
        valuation_signals=signals_obj,
        company=str(company or ""),
        ticker=str(ticker or "").strip().upper(),
        stop_on_stage_failure=bool(stop_on_stage_failure),
    )


def composition_package_versions() -> dict[str, str]:
    """Best-effort public package versions for composition stages."""
    names = (
        "financial",
        "valuation",
        "economic_moat",
        "management_quality",
        "financial_strength",
        "earnings_quality",
        "growth_quality",
        "business_quality_aggregator",
        "investment_recommendation",
        "investment_committee",
        "business_quality",
    )
    # "risk" is a dsp_platform-native structural aggregation stage (see
    # composition/risk_view.py), not an external engine package.
    out: dict[str, str] = {}
    for name in names:
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", None)
            if version is not None:
                out[name] = str(version)
        except Exception:  # noqa: BLE001
            continue
    return out


def composition_capability_manifest() -> dict[str, Any]:
    """Static capability description for /capabilities (no execution)."""
    stages = [s.value for s in EXECUTION_ORDER]
    return {
        "pipeline_version": COMPOSITION_PIPELINE_VERSION,
        "pipeline_stages": stages,
        "analytical_modules": stages,
        "supported_reports": [
            "financial_analysis",
            "valuation",
            "economic_moat",
            "management_quality",
            "financial_strength",
            "earnings_quality",
            "growth_quality",
            "risk",
            "business_quality",
            "investment_recommendation",
            "investment_committee",
            "buffett_authority",
            "pipeline_result",
        ],
        "package_versions": composition_package_versions(),
        "authority": {
            "buffett_analysis": "server",
            "client_buffett_overrides": "rejected",
        },
    }


def pipeline_result_public_dict(result: PipelineResult) -> dict[str, Any]:
    """Stable public dict for API DTOs — never returns raw domain objects."""
    from dsp_platform.investment_provenance import source_evidence_from_trace

    base = result.to_dict()
    summaries: list[dict[str, Any]] = []
    by_stage = {s.stage: s for s in result.stages}
    for stage in EXECUTION_ORDER:
        outcome = by_stage.get(stage.value)
        payload = getattr(result, _attr_for_stage(stage), None)
        summaries.append(_stage_summary(stage.value, payload, outcome))
    base["stage_summaries"] = summaries
    base["recommendation_summary"] = _decision_summary(result.investment_recommendation)
    base["committee_summary"] = _decision_summary(result.investment_committee)
    base["buffett_authority"] = _buffett_authority_summary(result, summaries)
    # P1-06 — public source evidence for lineage (secrets redacted in builder).
    base["source_evidence"] = source_evidence_from_trace(
        result.authenticated_valuation_trace
    )
    # Server-computed valuation display fields (never from client request).
    signals = result.valuation_signals
    if signals is not None:
        base["server_valuation"] = {
            "authority": "server",
            "intrinsic_value_per_share": _opt_float(
                getattr(signals, "intrinsic_value_per_share", None)
            ),
            "current_market_price": _opt_float(
                getattr(signals, "current_market_price", None)
            ),
            "confidence": _opt_float(getattr(signals, "confidence", None)),
        }
    else:
        base["server_valuation"] = {
            "authority": "server",
            "intrinsic_value_per_share": None,
            "current_market_price": None,
            "confidence": None,
        }
    base["risk"] = (
        result.risk.to_dict() if hasattr(result.risk, "to_dict") else None
    )
    return base


def _buffett_authority_summary(
    result: PipelineResult, summaries: list[dict[str, Any]]
) -> dict[str, Any]:
    """P1-05 — server-authoritative Buffett / investment-quality surface.

    Aggregates existing pipeline stage scores only. Does not invent a new
    Buffett methodology or recompute fundamentals.
    """
    by_stage = {s["stage"]: s for s in summaries}
    factors = {
        "economic_moat": _factor_from_stage(by_stage.get("economic_moat")),
        "management_quality": _factor_from_stage(by_stage.get("management_quality")),
        "financial_strength": _factor_from_stage(by_stage.get("financial_strength")),
        "earnings_quality": _factor_from_stage(by_stage.get("earnings_quality")),
        "growth_quality": _factor_from_stage(by_stage.get("growth_quality")),
        "business_quality": _factor_from_stage(
            by_stage.get("business_quality_aggregator")
        ),
        "valuation": _factor_from_stage(by_stage.get("valuation")),
        "investment_recommendation": _factor_from_stage(
            by_stage.get("investment_recommendation")
        ),
    }
    bq = factors["business_quality"]
    rec = _decision_summary(result.investment_recommendation)
    committee = _decision_summary(result.investment_committee)
    buffett_reviewer = _buffett_reviewer_from_committee(result.investment_committee)
    return {
        "authority": "server",
        "methodology": "existing_pipeline_stages",
        "client_overrides_accepted": False,
        "factors": factors,
        "overall_score": bq.get("score"),
        "overall_label": bq.get("label"),
        "overall_status": bq.get("status"),
        "recommendation": (rec or {}).get("decision"),
        "recommendation_score": (rec or {}).get("score"),
        "committee_decision": (committee or {}).get("decision"),
        "buffett_reviewer": buffett_reviewer,
    }


def _factor_from_stage(summary: dict[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return {
            "score": None,
            "label": None,
            "decision": None,
            "confidence": None,
            "status": "unavailable",
            "available": False,
        }
    status = str(summary.get("status") or "unavailable")
    score = summary.get("score")
    available = bool(
        summary.get("has_result")
        and status in {"succeeded", "degraded"}
        and score is not None
    )
    return {
        "score": score if available else None,
        "label": summary.get("label") if available else None,
        "decision": summary.get("decision") if available else None,
        "confidence": summary.get("confidence") if available else None,
        "status": status if available else "unavailable",
        "available": available,
    }


def _buffett_reviewer_from_committee(payload: object | None) -> dict[str, Any] | None:
    if payload is None or not hasattr(payload, "to_dict"):
        return None
    try:
        raw = payload.to_dict()
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(raw, dict):
        return None
    reviewers = raw.get("reviewers") or []
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            continue
        role = str(reviewer.get("role") or "").lower()
        if "buffett" not in role:
            continue
        score = reviewer.get("score")
        if isinstance(score, dict):
            score = score.get("value")
        confidence = reviewer.get("confidence")
        if isinstance(confidence, dict):
            confidence = confidence.get("value")
        opinion = reviewer.get("opinion")
        if isinstance(opinion, dict):
            opinion = opinion.get("value") or opinion.get("decision")
        return {
            "role": reviewer.get("role"),
            "opinion": opinion,
            "score": score,
            "confidence": confidence,
            "available": score is not None,
        }
    return None


def _attr_for_stage(stage: PipelineStage) -> str:
    mapping = {
        PipelineStage.FINANCIAL: "financial_analysis",
        PipelineStage.VALUATION: "valuation",
        PipelineStage.ECONOMIC_MOAT: "economic_moat",
        PipelineStage.MANAGEMENT_QUALITY: "management_quality",
        PipelineStage.FINANCIAL_STRENGTH: "financial_strength",
        PipelineStage.EARNINGS_QUALITY: "earnings_quality",
        PipelineStage.GROWTH_QUALITY: "growth_quality",
        PipelineStage.RISK: "risk",
        PipelineStage.BUSINESS_QUALITY_AGGREGATOR: "business_quality",
        PipelineStage.INVESTMENT_RECOMMENDATION: "investment_recommendation",
        PipelineStage.INVESTMENT_COMMITTEE: "investment_committee",
    }
    return mapping[stage]


def _stage_summary(
    stage: str, payload: object | None, outcome: object | None
) -> dict[str, Any]:
    status = getattr(outcome, "status", None)
    status_val = getattr(status, "value", str(status) if status else "unknown")
    score = _opt_float(getattr(payload, "score", None) if payload else None)
    if score is None and payload is not None:
        # BQ aggregator exposes the assessed float separately from Score object.
        score = _opt_float(getattr(payload, "overall_business_quality_score", None))
    return {
        "stage": stage,
        "status": status_val,
        "has_result": payload is not None,
        "score": score,
        "label": _opt_str(getattr(payload, "label", None) if payload else None)
        or _opt_str(getattr(payload, "rating", None) if payload else None)
        or _opt_str(
            getattr(payload, "overall_business_quality_rating", None)
            if payload
            else None
        ),
        "decision": _opt_str(getattr(payload, "decision", None) if payload else None)
        or _opt_str(getattr(payload, "action", None) if payload else None)
        or _opt_str(getattr(payload, "recommendation", None) if payload else None),
        "confidence": _opt_float(
            getattr(payload, "confidence", None) if payload else None
        ),
        "error": getattr(outcome, "error", None) if outcome else None,
        "warnings": list(getattr(outcome, "warnings", ()) or ()),
    }


def _decision_summary(payload: object | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    summary: dict[str, Any] = {
        "decision": _opt_str(getattr(payload, "decision", None))
        or _opt_str(getattr(payload, "action", None))
        or _opt_str(getattr(payload, "recommendation", None)),
        "confidence": _opt_float(getattr(payload, "confidence", None)),
        "score": _opt_float(getattr(payload, "score", None)),
        "label": _opt_str(getattr(payload, "label", None)),
    }
    if hasattr(payload, "to_dict") and callable(payload.to_dict):
        try:
            raw = payload.to_dict()
            if isinstance(raw, dict):
                # Keep only JSON-safe scalar / shallow keys for stability.
                for key in (
                    "decision",
                    "action",
                    "recommendation",
                    "confidence",
                    "score",
                    "label",
                    "margin_of_safety",
                    "consensus",
                    "rationale",
                ):
                    if key not in raw:
                        continue
                    if summary.get(key) is not None:
                        continue
                    if key in {"confidence", "score", "margin_of_safety"}:
                        summary[key] = _opt_float(raw[key])
                    else:
                        summary[key] = _opt_str(raw[key]) or raw[key]
        except Exception:  # noqa: BLE001
            pass
    return summary


def _opt_float(value: object) -> float | None:
    """Coerce engine Score/Confidence wrappers and plain numbers to float."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, dict):
        return _opt_float(value.get("value"))
    if hasattr(value, "value") and not isinstance(value, (str, bytes, int, float)):
        return _opt_float(getattr(value, "value"))
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _opt_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("value", "label", "decision", "action", "recommendation"):
            if key in value and value[key] is not None:
                return _opt_str(value[key])
        return None
    # Enum / score wrappers expose ``.value``; prefer string enums only.
    inner = getattr(value, "value", value)
    if inner is not value and not isinstance(inner, (str, bytes)):
        # Numeric Score.value — not a label.
        return None
    text = str(inner).strip()
    return text if text else None
