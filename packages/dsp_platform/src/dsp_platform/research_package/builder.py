"""Build a private ResearchPackage from compose_intelligence outputs.

Architecture decision (STEP 4A / 4B):
    ResearchObject remains a separate EPIC-R001 pass-through (HTTP-exposed
    via /research/object, includes timestamps). ResearchPackage is NOT a
    wrapper around ResearchObject and is not built as
    PipelineResult → ResearchObject → ResearchPackage.

    Canonical path:
        CompositionRequest
            → PlatformOrchestrator.execute / DSPPlatform.compose_intelligence
            → PipelineResult
            → build_research_package
            → ResearchPackage (private)

The builder is an aggregator. It copies existing pipeline outputs and the
existing ``pipeline_result_public_dict`` projections (Buffett authority,
server valuation, source evidence). It does not calculate DCF, Graham,
MoS, ratios, Buffett scores, or BUY/SELL/HOLD.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from dsp_platform.composition.adapters import pipeline_result_public_dict
from dsp_platform.composition.authenticated_valuation import DATA_UNAVAILABLE
from dsp_platform.composition.models import (
    CompositionRequest,
    PipelineResult,
    StageOutcome,
    StageStatus,
)
from dsp_platform.composition.versions import COMPOSITION_PIPELINE_VERSION
from dsp_platform.external_evidence.models import (
    ExternalEvidenceValidationError,
    ValidatedExternalEvidencePackage,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    normalize_identity_token,
    validate_external_evidence_identity,
)
from dsp_platform.research_package.models import (
    ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE,
    RESEARCH_PACKAGE_SCHEMA_VERSION,
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    PackageSection,
    ResearchPackage,
    ResearchPackageSourceError,
    SectionStatus,
    freeze_mapping,
    strip_private_fields,
)

__all__ = ["attach_validated_external_evidence", "build_research_package"]

_STAGE_ATTR = {
    "financial": "financial_analysis",
    "valuation": "valuation",
    "economic_moat": "economic_moat",
    "management_quality": "management_quality",
    "financial_strength": "financial_strength",
    "earnings_quality": "earnings_quality",
    "growth_quality": "growth_quality",
    "risk": "risk",
    "business_quality_aggregator": "business_quality",
    "investment_recommendation": "investment_recommendation",
    "investment_committee": "investment_committee",
}


def build_research_package(
    pipeline_result: object,
    *,
    request: CompositionRequest | None = None,
) -> ResearchPackage:
    """Aggregate a private ResearchPackage from a composition PipelineResult.

    Args:
        pipeline_result: Output of ``compose_intelligence`` /
            ``PlatformOrchestrator.execute``. ``DecisionPack`` and other
            legacy ``analyze_decision_pack`` objects are rejected.
        request: Optional composition request used only for identity and
            statement pass-through. Not used to recalculate engines.
    """
    result = _require_pipeline_result(pipeline_result)
    public = pipeline_result_public_dict(result)
    methodology = str(
        result.metadata.pipeline_version or COMPOSITION_PIPELINE_VERSION
    )
    by_stage = {row.stage: row for row in result.stages}

    identity = _identity_section(request)
    market_data = _market_data_section(result, public)
    financial_statements = _financial_statements_section(request)
    financials = _stage_section(
        name="financials",
        stage="financial",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.financial_analysis),
    )
    valuation = _valuation_section(result, public, by_stage, methodology)
    economic_moat = _stage_section(
        name="economic_moat",
        stage="economic_moat",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.economic_moat),
    )
    management_quality = _stage_section(
        name="management_quality",
        stage="management_quality",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.management_quality),
    )
    financial_strength = _stage_section(
        name="financial_strength",
        stage="financial_strength",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.financial_strength),
    )
    earnings_quality = _stage_section(
        name="earnings_quality",
        stage="earnings_quality",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.earnings_quality),
    )
    growth_quality = _stage_section(
        name="growth_quality",
        stage="growth_quality",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.growth_quality),
    )
    business_quality = _stage_section(
        name="business_quality",
        stage="business_quality_aggregator",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.business_quality),
    )
    risk = _stage_section(
        name="risk",
        stage="risk",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_engine_payload(result.risk),
    )
    investment_recommendation = _stage_section(
        name="investment_recommendation",
        stage="investment_recommendation",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_recommendation_payload(result, public),
    )
    investment_committee = _stage_section(
        name="investment_committee",
        stage="investment_committee",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=_committee_payload(result, public),
    )
    buffett_authority = _mapping_section(
        name="buffett_authority",
        status=_buffett_status(public),
        payload=_as_mapping(public.get("buffett_authority")),
        provenance={
            "stage": "buffett_authority",
            "source": "pipeline_result_public_dict",
            "methodology": "existing_pipeline_stages",
            "methodology_version": methodology,
            "calculation": False,
        },
        message=None
        if _as_mapping(public.get("buffett_authority")) is not None
        else DATA_UNAVAILABLE,
    )
    evidence = _evidence_section(result, public, methodology)
    entry_exit = _mapping_section(
        name="entry_exit",
        status=SectionStatus.NOT_IMPLEMENTED.value,
        payload=None,
        provenance={
            "stage": None,
            "source": "none",
            "methodology_version": methodology,
            "calculation": False,
            "canonical_engine": False,
        },
        message=ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE,
    )

    limitations = tuple(result.limitations) + (
        "ResearchPackage is a private aggregator of compose_intelligence outputs.",
        "ResearchPackage must not be returned to a client.",
        ENTRY_EXIT_NOT_IMPLEMENTED_MESSAGE,
    )
    return ResearchPackage(
        schema_version=RESEARCH_PACKAGE_SCHEMA_VERSION,
        methodology_version=methodology,
        source_pipeline=SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
        identity=identity,
        market_data=market_data,
        financial_statements=financial_statements,
        financials=financials,
        valuation=valuation,
        economic_moat=economic_moat,
        management_quality=management_quality,
        financial_strength=financial_strength,
        earnings_quality=earnings_quality,
        growth_quality=growth_quality,
        business_quality=business_quality,
        risk=risk,
        investment_recommendation=investment_recommendation,
        investment_committee=investment_committee,
        buffett_authority=buffett_authority,
        evidence=evidence,
        entry_exit=entry_exit,
        limitations=limitations,
        errors=tuple(result.errors),
        pipeline_ok=bool(result.ok),
    )


def attach_validated_external_evidence(
    package: ResearchPackage,
    evidence: ValidatedExternalEvidencePackage,
) -> ResearchPackage:
    """Return a new ResearchPackage with validated external evidence attached.

    Existing compose_intelligence callers are unchanged: ``build_research_package``
    still defaults ``external_evidence`` to None. This helper does not run
    engines, search, or AI.
    """
    if not isinstance(package, ResearchPackage):
        raise ResearchPackageSourceError(
            "attach_validated_external_evidence requires a ResearchPackage"
        )
    if not isinstance(evidence, ValidatedExternalEvidencePackage):
        raise ExternalEvidenceValidationError(
            "external evidence must be a ValidatedExternalEvidencePackage"
        )
    if dict(evidence.canonical_calculation_inputs()):
        raise ExternalEvidenceValidationError(
            "external evidence cannot supply DSP calculation inputs"
        )
    package_symbol, package_exchange = _package_identity_tokens(package)
    validate_external_evidence_identity(evidence.subject)
    if normalize_identity_token(evidence.subject.symbol) != package_symbol:
        raise ExternalEvidenceValidationError(
            "identity mismatch: evidence subject symbol "
            f"{evidence.subject.symbol!r} != ResearchPackage ticker "
            f"{package_symbol!r}"
        )
    evidence_exchange = normalize_identity_token(evidence.subject.exchange) or None
    if package_exchange and evidence_exchange and package_exchange != evidence_exchange:
        raise ExternalEvidenceValidationError(
            "identity mismatch: exchange disagreement "
            f"({package_exchange!r} vs {evidence_exchange!r}); "
            "NSE/BSE are not converted"
        )
    for record in evidence.records:
        assert_identities_compatible(evidence.subject, record.identity)
    return replace(package, external_evidence=evidence)


def _package_identity_tokens(package: ResearchPackage) -> tuple[str, str | None]:
    payload = package.identity.payload
    if not isinstance(payload, Mapping):
        raise ExternalEvidenceValidationError(
            "cannot attach external evidence: ResearchPackage identity "
            "is unavailable"
        )
    ticker = normalize_identity_token(str(payload.get("ticker") or ""))
    if not ticker:
        raise ExternalEvidenceValidationError(
            "cannot attach external evidence: ResearchPackage ticker "
            "is unavailable"
        )
    exchange_raw = payload.get("exchange")
    exchange = normalize_identity_token(str(exchange_raw or "")) or None
    return ticker, exchange


def _require_pipeline_result(pipeline_result: object) -> PipelineResult:
    if isinstance(pipeline_result, PipelineResult):
        return pipeline_result
    name = type(pipeline_result).__name__
    raise ResearchPackageSourceError(
        "ResearchPackage must be built from compose_intelligence "
        f"PipelineResult, not {name}. analyze_decision_pack / DecisionPack "
        "is rejected."
    )


def _outcome(by_stage: Mapping[str, StageOutcome], stage: str) -> StageOutcome | None:
    return by_stage.get(stage)


def _status_for_stage(
    by_stage: Mapping[str, StageOutcome], stage: str, payload: Any
) -> str:
    outcome = _outcome(by_stage, stage)
    if outcome is not None:
        status = outcome.status
        return status.value if isinstance(status, StageStatus) else str(status)
    if payload is None:
        return SectionStatus.UNAVAILABLE.value
    return SectionStatus.SUCCEEDED.value


def _available(status: str, payload: Any) -> bool:
    return payload is not None and status in {
        StageStatus.SUCCEEDED.value,
        StageStatus.DEGRADED.value,
    }


def _stage_section(
    *,
    name: str,
    stage: str,
    result: PipelineResult,
    by_stage: Mapping[str, StageOutcome],
    methodology: str,
    payload: Mapping[str, Any] | None,
) -> PackageSection:
    status = _status_for_stage(by_stage, stage, payload)
    outcome = _outcome(by_stage, stage)
    evidence_count = result.metadata.evidence_counts.get(stage)
    message = None
    if not _available(status, payload):
        message = DATA_UNAVAILABLE
        if outcome is not None and outcome.error:
            message = outcome.error
    return PackageSection(
        name=name,
        status=status,
        available=_available(status, payload),
        payload=freeze_mapping(payload),
        provenance=freeze_mapping(
            {
                "stage": stage,
                "source": "compose_intelligence",
                "methodology_version": methodology,
                "calculation_status": status,
                "has_result": getattr(result, _STAGE_ATTR.get(stage, ""), None)
                is not None,
                "evidence_count": evidence_count,
                "error": outcome.error if outcome is not None else None,
                "warnings": list(outcome.warnings) if outcome is not None else [],
            }
        )
        or {},
        message=message,
    )


def _mapping_section(
    *,
    name: str,
    status: str,
    payload: Mapping[str, Any] | None,
    provenance: Mapping[str, Any],
    message: str | None,
) -> PackageSection:
    cleaned = strip_private_fields(dict(payload)) if payload is not None else None
    return PackageSection(
        name=name,
        status=status,
        available=_available(status, cleaned),
        payload=freeze_mapping(cleaned) if isinstance(cleaned, dict) else None,
        provenance=freeze_mapping(dict(provenance)) or {},
        message=message,
    )


def _identity_section(request: CompositionRequest | None) -> PackageSection:
    if request is None:
        return _mapping_section(
            name="identity",
            status=SectionStatus.UNAVAILABLE.value,
            payload=None,
            provenance={"stage": None, "source": "composition_request"},
            message=DATA_UNAVAILABLE,
        )
    ticker = str(request.ticker or "").strip().upper() or None
    company = str(request.company or "").strip() or None
    exchange = None
    if request.exchange:
        exchange = str(request.exchange).strip().upper() or None
    if ticker is None and company is None:
        return _mapping_section(
            name="identity",
            status=SectionStatus.UNAVAILABLE.value,
            payload=None,
            provenance={"stage": None, "source": "composition_request"},
            message=DATA_UNAVAILABLE,
        )
    return _mapping_section(
        name="identity",
        status=SectionStatus.SUCCEEDED.value,
        payload={"ticker": ticker, "company": company, "exchange": exchange},
        provenance={"stage": None, "source": "composition_request"},
        message=None,
    )


def _market_data_section(
    result: PipelineResult, public: Mapping[str, Any]
) -> PackageSection:
    server = _as_mapping(public.get("server_valuation")) or {}
    signals = result.valuation_signals
    price = _copy_number(getattr(signals, "current_market_price", None))
    if price is None:
        price = _copy_number(server.get("current_market_price"))
    if price is None:
        return _mapping_section(
            name="market_data",
            status=SectionStatus.UNAVAILABLE.value,
            payload=None,
            provenance={
                "stage": "valuation",
                "source": "valuation_signals",
            },
            message=DATA_UNAVAILABLE,
        )
    valuation_outcome = next(
        (row for row in result.stages if row.stage == "valuation"), None
    )
    status = (
        valuation_outcome.status.value
        if valuation_outcome is not None
        else SectionStatus.SUCCEEDED.value
    )
    if status not in {StageStatus.SUCCEEDED.value, StageStatus.DEGRADED.value}:
        status = SectionStatus.DEGRADED.value
    return _mapping_section(
        name="market_data",
        status=status,
        payload={"current_market_price": price, "authority": "server"},
        provenance={
            "stage": "valuation",
            "source": "valuation_signals",
            "field": "current_market_price",
        },
        message=None,
    )


def _financial_statements_section(
    request: CompositionRequest | None,
) -> PackageSection:
    statements = getattr(request, "financial_statements", None) if request else None
    payload = _engine_payload(statements)
    if payload is None:
        return _mapping_section(
            name="financial_statements",
            status=SectionStatus.UNAVAILABLE.value,
            payload=None,
            provenance={"stage": "financial", "source": "composition_request"},
            message=DATA_UNAVAILABLE,
        )
    return _mapping_section(
        name="financial_statements",
        status=SectionStatus.SUCCEEDED.value,
        payload=payload,
        provenance={"stage": "financial", "source": "composition_request"},
        message=None,
    )


def _valuation_section(
    result: PipelineResult,
    public: Mapping[str, Any],
    by_stage: Mapping[str, StageOutcome],
    methodology: str,
) -> PackageSection:
    signals = result.valuation_signals
    server = _as_mapping(public.get("server_valuation"))
    methods = _valuation_methods(result.valuation)
    value_range = _valuation_range(result.valuation)
    iv_per_share = _copy_number(getattr(signals, "intrinsic_value_per_share", None))
    if iv_per_share is None and server is not None:
        iv_per_share = _copy_number(server.get("intrinsic_value_per_share"))
    price = _copy_number(getattr(signals, "current_market_price", None))
    if price is None and server is not None:
        price = _copy_number(server.get("current_market_price"))
    mos = _copy_number(getattr(signals, "margin_of_safety", None))
    premium = _copy_number(getattr(signals, "premium_discount", None))
    confidence = _copy_number(getattr(signals, "confidence", None))
    if confidence is None and server is not None:
        confidence = _copy_number(server.get("confidence"))
    payload = {
        "methods": methods,
        "range": value_range,
        "intrinsic_value": {
            "intrinsic_value_per_share": iv_per_share,
            "current_market_price": price,
            "confidence": confidence,
        },
        "margin_of_safety": mos,
        "premium_discount": premium,
        "server_valuation": dict(server) if server is not None else None,
    }
    return _stage_section(
        name="valuation",
        stage="valuation",
        result=result,
        by_stage=by_stage,
        methodology=methodology,
        payload=payload,
    )


def _valuation_methods(valuation_payload: object) -> list[dict[str, Any]] | None:
    estimates = getattr(valuation_payload, "estimates", None)
    if estimates is None:
        return None
    rows: list[dict[str, Any]] = []
    for estimate in estimates:
        method = getattr(estimate, "method", None)
        method_value = getattr(method, "value", method)
        rows.append(
            {
                "method": str(method_value) if method_value is not None else None,
                "intrinsic_value": getattr(estimate, "intrinsic_value", None),
                "applicable": getattr(estimate, "applicable", None),
                "formula": getattr(estimate, "formula", None),
            }
        )
    return rows


def _valuation_range(valuation_payload: object) -> dict[str, Any] | None:
    value_range = getattr(valuation_payload, "valuation_range", None)
    if value_range is None:
        return None
    return {
        "low": getattr(value_range, "low", None),
        "mid": getattr(value_range, "mid", None),
        "high": getattr(value_range, "high", None),
    }


def _recommendation_payload(
    result: PipelineResult, public: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    engine = _engine_payload(result.investment_recommendation)
    summary = _as_mapping(public.get("recommendation_summary"))
    if engine is None and summary is None:
        return None
    payload: dict[str, Any] = {}
    if engine is not None:
        payload.update(engine)
    if summary is not None:
        payload["recommendation_summary"] = dict(summary)
    return payload


def _committee_payload(
    result: PipelineResult, public: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    engine = _engine_payload(result.investment_committee)
    summary = _as_mapping(public.get("committee_summary"))
    if engine is None and summary is None:
        return None
    payload: dict[str, Any] = {}
    if engine is not None:
        payload.update(engine)
    if summary is not None:
        payload["committee_summary"] = dict(summary)
    return payload


def _buffett_status(public: Mapping[str, Any]) -> str:
    authority = _as_mapping(public.get("buffett_authority"))
    if authority is None:
        return SectionStatus.UNAVAILABLE.value
    overall_status = authority.get("overall_status")
    if isinstance(overall_status, str) and overall_status:
        return overall_status
    if authority.get("overall_score") is None:
        return SectionStatus.UNAVAILABLE.value
    return SectionStatus.SUCCEEDED.value


def _evidence_section(
    result: PipelineResult,
    public: Mapping[str, Any],
    methodology: str,
) -> PackageSection:
    source_evidence = _as_mapping(public.get("source_evidence"))
    payload = {
        "source_evidence": (
            dict(source_evidence) if source_evidence is not None else None
        ),
        "evidence_counts": dict(result.metadata.evidence_counts),
        "stage_summaries": list(public.get("stage_summaries") or []),
        "authenticated_valuation_trace_present": (
            result.authenticated_valuation_trace is not None
        ),
    }
    status = (
        SectionStatus.SUCCEEDED.value
        if source_evidence is not None or result.metadata.evidence_counts
        else SectionStatus.UNAVAILABLE.value
    )
    return _mapping_section(
        name="evidence",
        status=status,
        payload=payload,
        provenance={
            "stage": None,
            "source": "pipeline_result_public_dict",
            "methodology_version": methodology,
        },
        message=None,
    )


def _engine_payload(obj: object | None) -> dict[str, Any] | None:
    if obj is None:
        return None
    to_dict = getattr(obj, "to_dict", None)
    if not callable(to_dict):
        return None
    try:
        raw = to_dict()
    except Exception:  # noqa: BLE001 — pass-through only; never invent
        return None
    if not isinstance(raw, dict):
        return None
    cleaned = strip_private_fields(raw)
    return cleaned if isinstance(cleaned, dict) else None


def _as_mapping(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        cleaned = strip_private_fields(value)
        return cleaned if isinstance(cleaned, dict) else None
    return None


def _copy_number(value: object) -> float | None:
    """Copy a numeric engine value. Does not compute ratios or MoS."""
    if value is None or isinstance(value, bool):
        return None
    inner = getattr(value, "value", value)
    if inner is not value and not isinstance(inner, (int, float)):
        return _copy_number(inner)
    try:
        return float(inner)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
