"""Deterministic execution pipeline for EPIC-001 composition."""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from business_quality import BusinessQualityEngine
from business_quality_aggregator import BusinessQualityAggregatorEngine
from earnings_quality import EarningsQualityEngine
from economic_moat import EconomicEngine
from financial import FinancialEngine
from financial_strength import FinancialStrengthEngine
from growth_quality import GrowthQualityEngine
from investment_committee import InvestmentCommitteeEngine
from investment_recommendation import (
    InvestmentRecommendationEngine,
    ValuationSignals,
)
from management_quality import ManagementEngine
from valuation import ValuationEngine

from dsp_platform.composition.authenticated_valuation import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationBundle,
    AuthenticatedValuationError,
    load_authenticated_valuation_bundle,
    production_requires_authenticated_bundle,
    signals_from_assessment,
    to_financial_statements,
)
from dsp_platform.composition.collectors import EvidenceCollector, TimingCollector, timed
from dsp_platform.composition.context import ExecutionContext
from dsp_platform.composition.errors import CompositionStageError
from dsp_platform.composition.models import (
    ExecutionMetadata,
    ExecutionTraceEntry,
    PipelineResult,
    StageOutcome,
    StageStatus,
)
from dsp_platform.composition.risk_view import build_company_risk_view
from dsp_platform.composition.versions import COMPOSITION_PIPELINE_VERSION

__all__ = ["EXECUTION_ORDER", "PipelineStage", "run_execution_pipeline"]

_AUTH_BUNDLE_KEY = "authenticated_valuation_bundle"
_AUTH_ERROR_KEY = "authenticated_valuation_error"
_AUTH_STATEMENTS_KEY = "authenticated_financial_statements"


class PipelineStage(str, Enum):
    FINANCIAL = "financial"
    VALUATION = "valuation"
    ECONOMIC_MOAT = "economic_moat"
    MANAGEMENT_QUALITY = "management_quality"
    FINANCIAL_STRENGTH = "financial_strength"
    EARNINGS_QUALITY = "earnings_quality"
    GROWTH_QUALITY = "growth_quality"
    RISK = "risk"
    BUSINESS_QUALITY_AGGREGATOR = "business_quality_aggregator"
    INVESTMENT_RECOMMENDATION = "investment_recommendation"
    INVESTMENT_COMMITTEE = "investment_committee"


EXECUTION_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.FINANCIAL,
    PipelineStage.VALUATION,
    PipelineStage.ECONOMIC_MOAT,
    PipelineStage.MANAGEMENT_QUALITY,
    PipelineStage.FINANCIAL_STRENGTH,
    PipelineStage.EARNINGS_QUALITY,
    PipelineStage.GROWTH_QUALITY,
    PipelineStage.RISK,
    PipelineStage.BUSINESS_QUALITY_AGGREGATOR,
    PipelineStage.INVESTMENT_RECOMMENDATION,
    PipelineStage.INVESTMENT_COMMITTEE,
)

_PKG = {
    PipelineStage.FINANCIAL: ("financial", FinancialEngine),
    PipelineStage.VALUATION: ("valuation", ValuationEngine),
    PipelineStage.ECONOMIC_MOAT: ("economic_moat", EconomicEngine),
    PipelineStage.MANAGEMENT_QUALITY: ("management_quality", ManagementEngine),
    PipelineStage.FINANCIAL_STRENGTH: ("financial_strength", FinancialStrengthEngine),
    PipelineStage.EARNINGS_QUALITY: ("earnings_quality", EarningsQualityEngine),
    PipelineStage.GROWTH_QUALITY: ("growth_quality", GrowthQualityEngine),
    # Structural aggregation stage native to dsp_platform — see risk_view.py.
    # Not a delegated external engine package (see composition/risk_view.py
    # module docstring for why risk/quantitative_risk packages are not used).
    PipelineStage.RISK: ("dsp_platform", None),
    PipelineStage.BUSINESS_QUALITY_AGGREGATOR: (
        "business_quality_aggregator",
        BusinessQualityAggregatorEngine,
    ),
    PipelineStage.INVESTMENT_RECOMMENDATION: (
        "investment_recommendation",
        InvestmentRecommendationEngine,
    ),
    PipelineStage.INVESTMENT_COMMITTEE: (
        "investment_committee",
        InvestmentCommitteeEngine,
    ),
}


def _pkg_version(name: str) -> str | None:
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", None)
        return str(version) if version is not None else None
    except Exception:
        return None


def _confidence(obj: object | None) -> float | None:
    if obj is None:
        return None
    conf = getattr(obj, "confidence", None)
    if conf is None:
        return None
    value = getattr(conf, "value", conf)
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _preload_authenticated_valuation_bundle(ctx: ExecutionContext) -> None:
    """P1-01 — attempt server-side authenticated quote + statements load."""
    ticker = str(ctx.request.ticker or "").strip().upper()
    if not ticker:
        return
    try:
        bundle = load_authenticated_valuation_bundle(ticker)
    except AuthenticatedValuationError as exc:
        ctx.results[_AUTH_ERROR_KEY] = str(exc) or DATA_UNAVAILABLE
        return
    except Exception as exc:  # noqa: BLE001 — map provider faults to unavailable
        ctx.results[_AUTH_ERROR_KEY] = f"{DATA_UNAVAILABLE} ({type(exc).__name__})"
        return
    ctx.results[_AUTH_BUNDLE_KEY] = bundle
    try:
        ctx.results[_AUTH_STATEMENTS_KEY] = to_financial_statements(bundle)
    except AuthenticatedValuationError as exc:
        ctx.results[_AUTH_ERROR_KEY] = str(exc) or DATA_UNAVAILABLE
        ctx.results.pop(_AUTH_BUNDLE_KEY, None)


def run_execution_pipeline(
    ctx: ExecutionContext,
    *,
    platform_version: str,
    stop_on_stage_failure: bool | None = None,
) -> PipelineResult:
    """Run the canonical composition order using public package engines only."""
    stop = (
        ctx.request.stop_on_stage_failure
        if stop_on_stage_failure is None
        else stop_on_stage_failure
    )
    timing = TimingCollector()
    evidence = EvidenceCollector()
    outcomes: list[StageOutcome] = []

    _preload_authenticated_valuation_bundle(ctx)

    handlers: dict[PipelineStage, Callable[[], Any]] = {
        PipelineStage.FINANCIAL: lambda: _stage_financial(ctx),
        PipelineStage.VALUATION: lambda: _stage_valuation(ctx),
        PipelineStage.ECONOMIC_MOAT: lambda: _stage_domain(
            ctx, "economic_moat", EconomicEngine().analyze
        ),
        PipelineStage.MANAGEMENT_QUALITY: lambda: _stage_domain(
            ctx, "management_quality", ManagementEngine().analyze
        ),
        PipelineStage.FINANCIAL_STRENGTH: lambda: _stage_domain(
            ctx, "financial_strength", FinancialStrengthEngine().analyze
        ),
        PipelineStage.EARNINGS_QUALITY: lambda: _stage_domain(
            ctx, "earnings_quality", EarningsQualityEngine().analyze
        ),
        PipelineStage.GROWTH_QUALITY: lambda: _stage_domain(
            ctx, "growth_quality", GrowthQualityEngine().analyze
        ),
        PipelineStage.RISK: lambda: _stage_risk(ctx),
        PipelineStage.BUSINESS_QUALITY_AGGREGATOR: lambda: _stage_aggregator(ctx),
        PipelineStage.INVESTMENT_RECOMMENDATION: lambda: _stage_recommendation(ctx),
        PipelineStage.INVESTMENT_COMMITTEE: lambda: _stage_committee(ctx),
    }

    for stage in EXECUTION_ORDER:
        pkg_name, _ = _PKG[stage]
        version = _pkg_version(pkg_name)
        if version:
            ctx.package_versions[pkg_name] = version
        try:
            with timed() as box:
                result, warnings, status = handlers[stage]()
            elapsed = box[0] if box else 0.0
            timing.record(stage.value, elapsed)
            evidence.record(stage.value, result)
            ctx.confidence_summary[stage.value] = _confidence(result)
            for warning in warnings:
                ctx.warnings.append(warning)
            ctx.results[stage.value] = result
            outcomes.append(
                StageOutcome(
                    stage=stage.value,
                    status=status,
                    result=result,
                    warnings=tuple(warnings),
                )
            )
            ctx.trace.append(
                ExecutionTraceEntry(
                    stage=stage.value,
                    status=status,
                    elapsed_ms=round(elapsed, 3),
                    package=pkg_name,
                    package_version=version,
                    message="ok" if status is StageStatus.SUCCEEDED else status.value,
                )
            )
        except Exception as exc:  # noqa: BLE001 — structured stage isolation
            elapsed = 0.0
            msg = f"{type(exc).__name__}: {exc}"
            ctx.errors.append(f"{stage.value}: {msg}")
            if ctx.failed_stage is None:
                ctx.failed_stage = stage.value
            outcomes.append(
                StageOutcome(
                    stage=stage.value,
                    status=StageStatus.FAILED,
                    error=msg,
                )
            )
            ctx.trace.append(
                ExecutionTraceEntry(
                    stage=stage.value,
                    status=StageStatus.FAILED,
                    elapsed_ms=elapsed,
                    package=pkg_name,
                    package_version=version,
                    error=msg,
                )
            )
            if stop:
                raise CompositionStageError(stage.value, msg) from exc

    ctx.evidence_counts.update(evidence.counts)
    ok = ctx.failed_stage is None
    metadata = ExecutionMetadata(
        pipeline_version=COMPOSITION_PIPELINE_VERSION,
        platform_version=platform_version,
        execution_order=tuple(s.value for s in EXECUTION_ORDER),
        package_versions=dict(ctx.package_versions),
        evidence_counts=dict(ctx.evidence_counts),
        confidence_summary=dict(ctx.confidence_summary),
        warnings=tuple(ctx.warnings),
        total_elapsed_ms=round(timing.total_ms, 3),
        ok=ok,
        failed_stage=ctx.failed_stage,
    )
    return PipelineResult(
        ok=ok,
        metadata=metadata,
        trace=tuple(ctx.trace),
        stages=tuple(outcomes),
        financial_analysis=ctx.results.get(PipelineStage.FINANCIAL.value),
        valuation=ctx.results.get(PipelineStage.VALUATION.value),
        valuation_signals=ctx.results.get("valuation_signals"),
        economic_moat=ctx.results.get(PipelineStage.ECONOMIC_MOAT.value),
        management_quality=ctx.results.get(PipelineStage.MANAGEMENT_QUALITY.value),
        financial_strength=ctx.results.get(PipelineStage.FINANCIAL_STRENGTH.value),
        earnings_quality=ctx.results.get(PipelineStage.EARNINGS_QUALITY.value),
        growth_quality=ctx.results.get(PipelineStage.GROWTH_QUALITY.value),
        risk=ctx.results.get(PipelineStage.RISK.value),
        business_quality_analysis=ctx.results.get("business_quality_analysis"),
        business_quality=ctx.results.get(
            PipelineStage.BUSINESS_QUALITY_AGGREGATOR.value
        ),
        investment_recommendation=ctx.results.get(
            PipelineStage.INVESTMENT_RECOMMENDATION.value
        ),
        investment_committee=ctx.results.get(PipelineStage.INVESTMENT_COMMITTEE.value),
        authenticated_valuation_trace=ctx.results.get(
            "authenticated_valuation_trace"
        ),
        errors=tuple(ctx.errors),
    )


def _stage_financial(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    warnings: list[str] = []
    if ctx.request.financial_analysis is not None:
        # Also ensure BQ analysis input exists early
        bq = BusinessQualityEngine().analyze(ctx.request.financial_analysis)
        ctx.results["business_quality_analysis"] = bq
        warnings.append("financial_analysis provided — FinancialEngine skipped")
        return ctx.request.financial_analysis, warnings, StageStatus.DEGRADED

    # P1-01 — prefer authenticated server statements over client payload.
    auth_statements = ctx.results.get(_AUTH_STATEMENTS_KEY)
    if auth_statements is not None:
        fa = FinancialEngine().analyze_financials(auth_statements)
        bq = BusinessQualityEngine().analyze(fa)
        ctx.results["business_quality_analysis"] = bq
        ctx.package_versions["business_quality"] = (
            _pkg_version("business_quality") or ""
        )
        warnings.append(
            "P1-01: financial stage used authenticated server statements"
        )
        return fa, warnings, StageStatus.SUCCEEDED

    ticker = str(ctx.request.ticker or "").strip()
    auth_err = ctx.results.get(_AUTH_ERROR_KEY)
    if production_requires_authenticated_bundle() and ticker:
        raise ValueError(str(auth_err) if auth_err else DATA_UNAVAILABLE)

    if ctx.request.financial_statements is None:
        raise ValueError(
            str(auth_err)
            if auth_err
            else "financial_statements or financial_analysis is required"
        )

    fa = FinancialEngine().analyze_financials(ctx.request.financial_statements)
    bq = BusinessQualityEngine().analyze(fa)
    ctx.results["business_quality_analysis"] = bq
    ctx.package_versions["business_quality"] = _pkg_version("business_quality") or ""
    return fa, warnings, StageStatus.SUCCEEDED


def _stage_valuation(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    """Compute valuation signals for downstream recommendation stages.

    P0-02 — Client-supplied investment conclusions are never authoritative.
    ``valuation_signals`` / ``overall_valuation`` on the request may supply a
    market *price* input only; intrinsic value, MoS, premium/discount, and
    confidence are ignored so clients cannot skip ``ValuationEngine`` or set
    IV/MoS/recommendation outcomes.

    P1-01 — When authenticated quote + statements are available for the
    request ticker, ``ValuationEngine`` runs on the server bundle. Production
    fails closed with ``Data unavailable.`` when that bundle cannot be built.
    """
    warnings: list[str] = []
    price = ctx.request.current_market_price

    if ctx.request.overall_valuation is not None:
        warnings.append(
            "client overall_valuation ignored — investment conclusions are "
            "server-authoritative (P0-02)"
        )

    if ctx.request.valuation_signals is not None:
        warnings.append(
            "client valuation_signals ignored for investment conclusions "
            "(P0-02); ValuationEngine / authenticated path used instead"
        )
        if price is None:
            price = ctx.request.valuation_signals.current_market_price

    bundle = ctx.results.get(_AUTH_BUNDLE_KEY)
    if isinstance(bundle, AuthenticatedValuationBundle):
        assessment = ValuationEngine().analyze(
            bundle.financial_snapshot,
            bundle.market_snapshot,
        )
        signals = signals_from_assessment(
            assessment,
            current_market_price=bundle.current_market_price,
            shares_outstanding=bundle.shares_outstanding,
        )
        ctx.results["valuation_signals"] = signals
        ctx.results["authenticated_valuation_trace"] = bundle.to_trace_dict()
        warnings.append(
            "P1-01: ValuationEngine used authenticated server data bundle"
        )
        return assessment, warnings, StageStatus.SUCCEEDED

    auth_err = ctx.results.get(_AUTH_ERROR_KEY)
    if production_requires_authenticated_bundle() and str(
        ctx.request.ticker or ""
    ).strip():
        raise ValueError(str(auth_err) if auth_err else DATA_UNAVAILABLE)

    if ctx.request.financial_snapshot is not None:
        assessment = ValuationEngine().analyze(
            ctx.request.financial_snapshot,  # type: ignore[arg-type]
            ctx.request.market_snapshot,  # type: ignore[arg-type]
        )
        mid = None
        vr = getattr(assessment, "valuation_range", None)
        if vr is not None:
            mid = getattr(vr, "mid", None)
        if price is None:
            raise ValueError("current_market_price is required with financial_snapshot")
        # P1-04 — company-level mid is NOT IV/share. Without authoritative shares
        # (authenticated path), do not fabricate per-share IV or MoS.
        signals = ValuationSignals(
            intrinsic_value_per_share=None,
            current_market_price=float(price),
            confidence=0.55 if mid is not None else 0.25,
        )
        ctx.results["valuation_signals"] = signals
        warnings.append(
            "valuation used request financial_snapshot (non-authenticated path)"
        )
        warnings.append(
            "P1-04: company-level IV not converted to per-share without "
            "authenticated shares — MoS unavailable"
        )
        return assessment, warnings, StageStatus.SUCCEEDED

    if price is None:
        raise ValueError(
            str(auth_err)
            if auth_err
            else (
                "current_market_price is required when ValuationEngine inputs "
                "are unavailable; client valuation conclusions are not accepted"
            )
        )
    # Graceful degradation (non-production): price-only signals (IV unknown)
    signals = ValuationSignals(
        intrinsic_value_per_share=None,
        current_market_price=float(price),
        confidence=0.25,
    )
    ctx.results["valuation_signals"] = signals
    warnings.append(
        "valuation degraded: no authenticated IV source — "
        "ValuationSignals price-only"
    )
    if auth_err:
        warnings.append(f"authenticated valuation unavailable: {auth_err}")
    return signals, warnings, StageStatus.DEGRADED


def _stage_domain(
    ctx: ExecutionContext,
    key: str,
    analyze: Callable[[Any, Any], Any],
) -> tuple[Any, list[str], StageStatus]:
    fa = ctx.results.get(PipelineStage.FINANCIAL.value)
    bq = ctx.results.get("business_quality_analysis")
    if fa is None or bq is None:
        raise ValueError(f"{key} requires financial_analysis and business_quality_analysis")
    return analyze(fa, bq), [], StageStatus.SUCCEEDED


def _stage_risk(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    """Aggregate already-computed engine ratings into the Risk section.

    Structural mapping only — see ``composition.risk_view`` for the fixed
    rating -> risk-level tables. Requires ``financial_strength`` to have run
    (economic_moat is optional; its category degrades gracefully when absent).
    """
    financial_strength = ctx.results.get(PipelineStage.FINANCIAL_STRENGTH.value)
    if financial_strength is None:
        raise ValueError("risk requires financial_strength")
    economic_moat = ctx.results.get(PipelineStage.ECONOMIC_MOAT.value)
    warnings: list[str] = []
    if economic_moat is None:
        warnings.append("business_risk unavailable — economic_moat did not run")
    view = build_company_risk_view(
        financial_strength=financial_strength, economic_moat=economic_moat
    )
    status = (
        StageStatus.SUCCEEDED
        if view.categories_available == view.categories_total
        else StageStatus.DEGRADED
    )
    return view, warnings, status


def _stage_aggregator(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    required = (
        PipelineStage.ECONOMIC_MOAT.value,
        PipelineStage.MANAGEMENT_QUALITY.value,
        PipelineStage.FINANCIAL_STRENGTH.value,
        PipelineStage.EARNINGS_QUALITY.value,
        PipelineStage.GROWTH_QUALITY.value,
    )
    missing = [k for k in required if ctx.results.get(k) is None]
    if missing:
        raise ValueError(f"aggregator missing domain outputs: {missing}")
    result = BusinessQualityAggregatorEngine().analyze(
        economic_moat=ctx.results[PipelineStage.ECONOMIC_MOAT.value],
        management_quality=ctx.results[PipelineStage.MANAGEMENT_QUALITY.value],
        financial_strength=ctx.results[PipelineStage.FINANCIAL_STRENGTH.value],
        earnings_quality=ctx.results[PipelineStage.EARNINGS_QUALITY.value],
        growth_quality=ctx.results[PipelineStage.GROWTH_QUALITY.value],
    )
    return result, [], StageStatus.SUCCEEDED


def _stage_recommendation(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    signals = ctx.results.get("valuation_signals")
    bq = ctx.results.get(PipelineStage.BUSINESS_QUALITY_AGGREGATOR.value)
    if signals is None or bq is None:
        raise ValueError("recommendation requires valuation_signals and aggregator")
    for key in (
        PipelineStage.ECONOMIC_MOAT.value,
        PipelineStage.MANAGEMENT_QUALITY.value,
        PipelineStage.FINANCIAL_STRENGTH.value,
        PipelineStage.EARNINGS_QUALITY.value,
        PipelineStage.GROWTH_QUALITY.value,
    ):
        if ctx.results.get(key) is None:
            raise ValueError(f"recommendation missing {key}")
    result = InvestmentRecommendationEngine().analyze(
        valuation=signals,
        business_quality=bq,
        economic_moat=ctx.results[PipelineStage.ECONOMIC_MOAT.value],
        management_quality=ctx.results[PipelineStage.MANAGEMENT_QUALITY.value],
        financial_strength=ctx.results[PipelineStage.FINANCIAL_STRENGTH.value],
        earnings_quality=ctx.results[PipelineStage.EARNINGS_QUALITY.value],
        growth_quality=ctx.results[PipelineStage.GROWTH_QUALITY.value],
    )
    return result, [], StageStatus.SUCCEEDED


def _stage_committee(
    ctx: ExecutionContext,
) -> tuple[Any, list[str], StageStatus]:
    ir = ctx.results.get(PipelineStage.INVESTMENT_RECOMMENDATION.value)
    signals = ctx.results.get("valuation_signals")
    bq = ctx.results.get(PipelineStage.BUSINESS_QUALITY_AGGREGATOR.value)
    if ir is None or signals is None or bq is None:
        raise ValueError("committee requires recommendation, signals, aggregator")
    result = InvestmentCommitteeEngine().analyze(
        recommendation=ir,
        business_quality=bq,
        economic_moat=ctx.results[PipelineStage.ECONOMIC_MOAT.value],
        management_quality=ctx.results[PipelineStage.MANAGEMENT_QUALITY.value],
        financial_strength=ctx.results[PipelineStage.FINANCIAL_STRENGTH.value],
        earnings_quality=ctx.results[PipelineStage.EARNINGS_QUALITY.value],
        growth_quality=ctx.results[PipelineStage.GROWTH_QUALITY.value],
        valuation=signals,
    )
    return result, [], StageStatus.SUCCEEDED
