"""Map a private ResearchPackage onto the public research report contract.

Aggregator only: copies already-computed DSP fields. Does not calculate
scores, valuation, MoS, X/10, entry/exit, scenarios, or expected returns.
Does not call AI, HTTP, or DSP engines.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.research_package.models import (
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    PackageSection,
    ResearchPackage,
)
from dsp_platform.research_report.models import (
    BUFFETT_METHODOLOGY,
    CANONICAL_VALUATION_AUTHORITY,
    PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION,
    SCORE_10_STATUS,
    BuffettAnalysisPublic,
    DspValue,
    EntryExitPublic,
    EvidenceRefPublic,
    ExpectedReturnsPublic,
    FactorScorecardRow,
    FinancialsPublic,
    IdentityPublic,
    IndustryPublic,
    PublicMetric,
    PublicResearchReport,
    PublicResearchReportError,
    QualityFactorPublic,
    RecommendationPublic,
    ReportStatus,
    RiskCategoryPublic,
    RiskPublic,
    ScenariosPublic,
    UnavailableBlock,
    ValuationMethodPublic,
    ValuationPublic,
    ValuationRangePublic,
    empty_ai_narrative,
)

__all__ = ["build_public_research_report"]

_QUALITY_SECTIONS: tuple[tuple[str, str], ...] = (
    ("business_quality", "Business Quality"),
    ("economic_moat", "Economic Moat"),
    ("management_quality", "Management Quality"),
    ("financial_strength", "Financial Strength"),
    ("earnings_quality", "Earnings Quality"),
    ("growth_quality", "Growth Quality"),
)

_SCORE_KEYS: tuple[str, ...] = (
    "overall_business_quality_score",
    "overall_moat_score",
    "overall_management_score",
    "overall_financial_strength_score",
    "overall_earnings_quality_score",
    "overall_growth_quality_score",
)

_RATING_KEYS: tuple[str, ...] = (
    "overall_business_quality_rating",
    "overall_moat_rating",
    "overall_management_rating",
    "overall_financial_strength_rating",
    "overall_earnings_quality_rating",
    "overall_growth_quality_rating",
    "rating",
    "label",
)

_RATIO_FAMILIES: tuple[str, ...] = (
    "profitability",
    "liquidity",
    "leverage",
    "efficiency",
    "cash_flow",
    "shareholder",
)

_INCOME_METRIC_PATHS: tuple[tuple[str, ...], ...] = (
    ("income", "revenue", "revenue"),
    ("income", "profitability", "eps"),
    ("income", "margins", "gross_margin"),
    ("income", "margins", "operating_margin"),
    ("income", "margins", "net_margin"),
    ("income", "growth", "revenue_growth"),
    ("cash_flow", "operating", "operating_cash_flow"),
    ("cash_flow", "free_cash_flow", "free_cash_flow"),
    ("balance_sheet", "leverage", "debt_to_equity"),
)

_ENTRY_EXIT_MESSAGE = (
    "No canonical DSP entry/exit engine is present. "
    "entry_price, entry_zone, exit_price, and target_price are not implemented."
)
_SCENARIO_MESSAGE = (
    "Canonical composition path does not implement bear/base/bull scenarios."
)
_EXPECTED_RETURN_MESSAGE = (
    "Expected return is not implemented. Historical CAGR is not expected return."
)
_INDUSTRY_MESSAGE = (
    "Canonical composition path does not provide industry or peer analysis."
)
_INTERNAL_LIMITATION_MARKERS = (
    "ResearchPackage",
    "must not be returned",
    "private aggregator",
)


def build_public_research_report(research_package: object) -> PublicResearchReport:
    """Project a ResearchPackage into the public client report contract."""
    package = _require_package(research_package)
    quality = {
        attr: _quality_factor(label, getattr(package, attr))
        for attr, label in _QUALITY_SECTIONS
    }
    valuation = _valuation(package)
    report = PublicResearchReport(
        schema_version=PUBLIC_RESEARCH_REPORT_SCHEMA_VERSION,
        methodology_version=package.methodology_version,
        source_pipeline=package.source_pipeline,
        research_status=_research_status(package),
        identity=_identity(package),
        executive_summary=empty_ai_narrative(),
        business_quality=quality["business_quality"],
        economic_moat=quality["economic_moat"],
        management_quality=quality["management_quality"],
        financial_strength=quality["financial_strength"],
        earnings_quality=quality["earnings_quality"],
        growth_quality=quality["growth_quality"],
        factor_scorecard=_factor_scorecard(package, quality),
        buffett_analysis=_buffett(package),
        financials=_financials(package),
        valuation=valuation,
        recommendation=_recommendation(package),
        risk=_risk(package),
        entry_exit=EntryExitPublic(
            entry=UnavailableBlock(
                status="not_implemented", message=_ENTRY_EXIT_MESSAGE
            ),
            exit=UnavailableBlock(
                status="not_implemented", message=_ENTRY_EXIT_MESSAGE
            ),
        ),
        scenarios=ScenariosPublic(
            bear=UnavailableBlock(status="unavailable", message=_SCENARIO_MESSAGE),
            base=UnavailableBlock(status="unavailable", message=_SCENARIO_MESSAGE),
            bull=UnavailableBlock(status="unavailable", message=_SCENARIO_MESSAGE),
        ),
        expected_returns=ExpectedReturnsPublic(
            status="not_implemented",
            value=None,
            message=_EXPECTED_RETURN_MESSAGE,
        ),
        industry=IndustryPublic(
            industry=UnavailableBlock(
                status="unavailable", message=_INDUSTRY_MESSAGE
            ),
            competitors=UnavailableBlock(
                status="unavailable", message=_INDUSTRY_MESSAGE
            ),
        ),
        evidence=_evidence(package),
        limitations=_public_limitations(package),
    )
    report.to_public_dict()
    return report


def _require_package(research_package: object) -> ResearchPackage:
    if isinstance(research_package, ResearchPackage):
        if research_package.source_pipeline != SOURCE_PIPELINE_COMPOSE_INTELLIGENCE:
            raise PublicResearchReportError(
                "Public report requires source_pipeline="
                f"{SOURCE_PIPELINE_COMPOSE_INTELLIGENCE!r}, got "
                f"{research_package.source_pipeline!r}"
            )
        return research_package
    name = type(research_package).__name__
    raise PublicResearchReportError(
        "build_public_research_report requires a compose_intelligence "
        f"ResearchPackage, got {name}."
    )


def _research_status(package: ResearchPackage) -> str:
    statuses = _section_statuses(package)
    if not package.pipeline_ok or "failed" in statuses:
        return ReportStatus.FAILED.value
    if "degraded" in statuses:
        return ReportStatus.DEGRADED.value
    if package.identity.status == "unavailable" and not package.pipeline_ok:
        return ReportStatus.UNAVAILABLE.value
    return ReportStatus.COMPLETE.value


def _section_statuses(package: ResearchPackage) -> set[str]:
    return {
        package.identity.status,
        package.financials.status,
        package.valuation.status,
        package.economic_moat.status,
        package.management_quality.status,
        package.financial_strength.status,
        package.earnings_quality.status,
        package.growth_quality.status,
        package.business_quality.status,
        package.risk.status,
        package.investment_recommendation.status,
        package.buffett_authority.status,
    }


def _identity(package: ResearchPackage) -> IdentityPublic:
    payload = package.identity.payload if package.identity.available else None
    ticker = _as_str(_get(payload, "ticker"))
    company = _as_str(_get(payload, "company") or _get(payload, "company_name"))
    exchange = _as_str(_get(payload, "exchange"))
    status = package.identity.status
    if ticker is None and company is None:
        status = "unavailable"
    return IdentityPublic(
        ticker=ticker,
        company_name=company,
        exchange=exchange,
        status=status,
    )


def _quality_factor(label: str, section: PackageSection) -> QualityFactorPublic:
    payload = section.payload if section.available else None
    score_100 = _copy_existing_score(payload)
    rating = _copy_existing_rating(payload)
    limitations: list[str] = []
    if section.message:
        limitations.append(section.message)
    if score_100 is None:
        limitations.append("Canonical 0-100 score unavailable for this factor.")
    return QualityFactorPublic(
        name=label,
        status=section.status,
        score_100=score_100,
        score_10=None,
        score_10_status=SCORE_10_STATUS,
        rating=rating,
        narrative=empty_ai_narrative(),
        evidence_refs=(
            EvidenceRefPublic(
                id=f"stage:{section.name}",
                kind="pipeline_stage",
                label=label,
            ),
        ),
        limitations=tuple(limitations),
    )


def _factor_scorecard(
    package: ResearchPackage,
    quality: Mapping[str, QualityFactorPublic],
) -> tuple[FactorScorecardRow, ...]:
    rows: list[FactorScorecardRow] = []
    for attr, label in _QUALITY_SECTIONS:
        factor = quality[attr]
        rows.append(
            FactorScorecardRow(
                factor_id=attr,
                label=label,
                status=factor.status,
                score_100=factor.score_100,
                score_10=None,
                score_10_status=SCORE_10_STATUS,
            )
        )
    capital = _capital_allocation_score(package)
    rows.append(
        FactorScorecardRow(
            factor_id="capital_allocation",
            label="Capital Allocation",
            status="succeeded" if capital is not None else "unavailable",
            score_100=capital,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    rows.append(
        FactorScorecardRow(
            factor_id="industry_attractiveness",
            label="Industry Attractiveness",
            status="unavailable",
            score_100=None,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    rows.append(
        FactorScorecardRow(
            factor_id="risk_safety",
            label="Risk / Safety",
            status=package.risk.status,
            score_100=None,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    rows.append(
        FactorScorecardRow(
            factor_id="valuation_attractiveness",
            label="Valuation",
            status="unavailable",
            score_100=None,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    rows.append(
        FactorScorecardRow(
            factor_id="margin_of_safety",
            label="Margin of Safety",
            status=package.valuation.status,
            score_100=None,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    rows.append(
        FactorScorecardRow(
            factor_id="long_term_ownership",
            label="Long-Term Ownership / Compounding",
            status="unavailable",
            score_100=None,
            score_10=None,
            score_10_status=SCORE_10_STATUS,
        )
    )
    return tuple(rows)


def _capital_allocation_score(package: ResearchPackage) -> float | None:
    payload = package.financials.payload if package.financials.available else None
    ratios = _as_mapping(_get(payload, "ratios"))
    capital = _as_mapping(_get(ratios, "capital_allocation"))
    return _as_number(_get(capital, "capital_allocation_score"))


def _buffett(package: ResearchPackage) -> BuffettAnalysisPublic:
    payload = (
        package.buffett_authority.payload
        if package.buffett_authority.available
        else None
    )
    methodology = _as_str(_get(payload, "methodology")) or BUFFETT_METHODOLOGY
    if methodology != BUFFETT_METHODOLOGY:
        methodology = BUFFETT_METHODOLOGY
    authority = _as_str(_get(payload, "authority")) or "server"
    score = _as_number(_get(payload, "overall_score"))
    label = _as_str(_get(payload, "overall_label"))
    limitations: list[str] = []
    if package.buffett_authority.message:
        limitations.append(package.buffett_authority.message)
    limitations.append(
        "Buffett overall score is the business-quality aggregator 0-100 "
        "score. It is not the investment recommendation score."
    )
    return BuffettAnalysisPublic(
        methodology=methodology,
        authority=authority,
        status=package.buffett_authority.status,
        buffett_overall_score_100=score,
        buffett_overall_label=label,
        narrative=empty_ai_narrative(),
        limitations=tuple(limitations),
    )


def _financials(package: ResearchPackage) -> FinancialsPublic:
    payload = package.financials.payload if package.financials.available else None
    metrics = _financial_metrics(payload)
    limitations: list[str] = []
    if package.financials.message:
        limitations.append(package.financials.message)
    if not metrics:
        limitations.append("Canonical financial metrics unavailable.")
    return FinancialsPublic(
        status=package.financials.status,
        metrics=metrics,
        narrative=empty_ai_narrative(),
        limitations=tuple(limitations),
    )


def _financial_metrics(
    payload: Mapping[str, Any] | None,
) -> tuple[PublicMetric, ...]:
    if not isinstance(payload, Mapping):
        return ()
    rows: list[PublicMetric] = []
    seen: set[str] = set()
    for path in _INCOME_METRIC_PATHS:
        value = payload
        for key in path:
            value = _get(value if isinstance(value, Mapping) else None, key)
        number = _as_number(value)
        name = path[-1]
        if name in seen:
            continue
        seen.add(name)
        rows.append(
            PublicMetric(
                name=name,
                value=number,
                status="available" if number is not None else "unavailable",
                source="dsp",
            )
        )
    ratios = _as_mapping(_get(payload, "ratios"))
    if ratios is not None:
        for family in _RATIO_FAMILIES:
            items = ratios.get(family) or ()
            if not isinstance(items, (list, tuple)):
                continue
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                name = _as_str(item.get("name"))
                if name is None or name in seen:
                    continue
                number = _as_number(item.get("value"))
                seen.add(name)
                rows.append(
                    PublicMetric(
                        name=name,
                        value=number,
                        status=(
                            "available" if number is not None else "unavailable"
                        ),
                        source="dsp",
                    )
                )
    return tuple(rows)


def _valuation(package: ResearchPackage) -> ValuationPublic:
    payload = package.valuation.payload if package.valuation.available else None
    intrinsic = _as_mapping(_get(payload, "intrinsic_value")) or {}
    iv = _as_number(intrinsic.get("intrinsic_value_per_share"))
    price = _as_number(intrinsic.get("current_market_price"))
    confidence = _as_number(intrinsic.get("confidence"))
    mos = _as_number(_get(payload, "margin_of_safety"))
    value_range = _as_mapping(_get(payload, "range")) or {}
    methods = _valuation_methods(_get(payload, "methods"))
    dcf = next((row for row in methods if row.method == "dcf"), None)
    if dcf is None:
        dcf = ValuationMethodPublic(
            method="dcf",
            intrinsic_value=None,
            applicable=None,
            status="unavailable",
            source="dsp",
        )
    section_status = package.valuation.status
    limitations: list[str] = []
    if package.valuation.message:
        limitations.append(package.valuation.message)
    if iv is None:
        limitations.append("Canonical intrinsic value unavailable.")
    if mos is None:
        limitations.append("Canonical margin of safety unavailable.")
    limitations.append(
        "Canonical valuation authority is compose_intelligence "
        "valuation_signals. dcf_intelligence, Graham, reverse DCF, and "
        "AI committee valuation are not the primary client valuation."
    )
    range_status = (
        "available"
        if any(
            _as_number(value_range.get(key)) is not None
            for key in ("low", "mid", "high")
        )
        else "unavailable"
    )
    return ValuationPublic(
        authority=CANONICAL_VALUATION_AUTHORITY,
        status=section_status,
        current_price=_dsp_value(price, section_status),
        intrinsic_value_per_share=_dsp_value(iv, section_status),
        valuation_range=ValuationRangePublic(
            low=_as_number(value_range.get("low")),
            mid=_as_number(value_range.get("mid")),
            high=_as_number(value_range.get("high")),
            status=range_status,
            source="dsp",
        ),
        methods=methods,
        dcf=dcf,
        margin_of_safety=_dsp_value(mos, section_status, unit="ratio"),
        confidence=_dsp_value(confidence, section_status),
        narrative=empty_ai_narrative(),
        limitations=tuple(limitations),
    )


def _valuation_methods(raw: object) -> tuple[ValuationMethodPublic, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    rows: list[ValuationMethodPublic] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        iv = _as_number(item.get("intrinsic_value"))
        applicable = item.get("applicable")
        if applicable is not None:
            applicable = bool(applicable)
        method = _as_str(item.get("method"))
        status = "available" if iv is not None else "unavailable"
        rows.append(
            ValuationMethodPublic(
                method=method,
                intrinsic_value=iv,
                applicable=applicable,
                status=status,
                source="dsp",
            )
        )
    return tuple(rows)


def _recommendation(package: ResearchPackage) -> RecommendationPublic:
    payload = (
        package.investment_recommendation.payload
        if package.investment_recommendation.available
        else None
    )
    summary = _as_mapping(_get(payload, "recommendation_summary")) or {}
    action = _as_str(_get(payload, "recommendation")) or _as_str(
        summary.get("decision")
    )
    score = _as_number(_get(payload, "overall_investment_score"))
    if score is None:
        score = _as_number(summary.get("score"))
    confidence = _as_number(_get(payload, "confidence"))
    if confidence is None:
        confidence = _as_number(summary.get("confidence"))
    rationale = _as_str(_get(payload, "decision_summary")) or _as_str(
        _get(payload, "recommendation_text")
    )
    risks = _string_tuple(_get(payload, "risks"))
    limitations: list[str] = []
    if package.investment_recommendation.message:
        limitations.append(package.investment_recommendation.message)
    limitations.append(
        "Investment recommendation score is distinct from Buffett overall "
        "score. AI must not replace the DSP recommendation."
    )
    return RecommendationPublic(
        action=action,
        recommendation_score_100=score,
        confidence=confidence,
        status=package.investment_recommendation.status,
        source="dsp",
        canonical_rationale=rationale,
        narrative=empty_ai_narrative(),
        risks=risks,
        limitations=tuple(limitations),
    )


def _risk(package: ResearchPackage) -> RiskPublic:
    payload = package.risk.payload if package.risk.available else None
    overall = _as_str(_get(payload, "overall_risk_level"))
    categories = _risk_categories(payload)
    limitations = _string_tuple(_get(payload, "limitations"))
    extra: list[str] = list(limitations)
    if package.risk.message:
        extra.append(package.risk.message)
    extra.append(
        "Canonical numeric risk score is unavailable. "
        "No X/10 or 0-100 risk score is invented."
    )
    return RiskPublic(
        overall_risk_level=overall,
        status=package.risk.status,
        score_100=None,
        score_10=None,
        score_10_status=SCORE_10_STATUS,
        categories=categories,
        narrative=empty_ai_narrative(),
        limitations=tuple(extra),
    )


def _risk_categories(
    payload: Mapping[str, Any] | None,
) -> tuple[RiskCategoryPublic, ...]:
    names = (
        "business_risk",
        "financial_risk",
        "regulatory_risk",
        "technology_risk",
        "currency_risk",
        "customer_concentration_risk",
    )
    if not isinstance(payload, Mapping):
        return tuple(
            RiskCategoryPublic(
                category=name,
                available=False,
                level=None,
                status="unavailable",
                message="Risk category unavailable.",
            )
            for name in names
        )
    rows: list[RiskCategoryPublic] = []
    for name in names:
        item = _as_mapping(payload.get(name))
        if item is None:
            rows.append(
                RiskCategoryPublic(
                    category=name,
                    available=False,
                    level=None,
                    status="unavailable",
                    message="Risk category unavailable.",
                )
            )
            continue
        available = bool(item.get("available"))
        rows.append(
            RiskCategoryPublic(
                category=_as_str(item.get("category")) or name,
                available=available,
                level=_as_str(item.get("level")),
                status="available" if available else "unavailable",
                message=_as_str(item.get("message")),
            )
        )
    return tuple(rows)


def _evidence(package: ResearchPackage) -> tuple[EvidenceRefPublic, ...]:
    payload = package.evidence.payload if package.evidence.available else None
    counts = _as_mapping(_get(payload, "evidence_counts")) or {}
    refs: list[EvidenceRefPublic] = []
    for stage in sorted(str(key) for key in counts):
        refs.append(
            EvidenceRefPublic(
                id=f"stage:{stage}",
                kind="pipeline_stage",
                label=stage,
            )
        )
    if package.identity.available:
        refs.append(
            EvidenceRefPublic(
                id="identity",
                kind="identity",
                label="instrument identity",
            )
        )
    refs.append(
        EvidenceRefPublic(
            id="valuation_signals",
            kind="canonical_valuation",
            label=CANONICAL_VALUATION_AUTHORITY,
        )
    )
    return tuple(refs)


def _public_limitations(package: ResearchPackage) -> tuple[str, ...]:
    rows: list[str] = []
    for item in package.limitations:
        if any(marker in item for marker in _INTERNAL_LIMITATION_MARKERS):
            continue
        rows.append(item)
    if package.errors:
        rows.append("Pipeline reported errors; research status is fail-closed.")
    rows.append("X/10 scoring is not implemented.")
    rows.append("Entry/exit prices are not implemented.")
    rows.append("Scenarios are unavailable on the canonical composition path.")
    rows.append("Expected returns are not implemented.")
    rows.append("Industry and competitor analysis is unavailable.")
    return tuple(dict.fromkeys(rows))


def _dsp_value(
    number: float | None, section_status: str, unit: str | None = None
) -> DspValue:
    if number is None:
        status = "unavailable"
        if section_status == "failed":
            status = "failed"
        elif section_status == "not_implemented":
            status = "not_implemented"
        return DspValue(value=None, status=status, source="dsp", unit=unit)
    value_status = "available"
    if section_status == "degraded":
        value_status = "degraded"
    return DspValue(value=number, status=value_status, source="dsp", unit=unit)


def _copy_existing_score(payload: Mapping[str, Any] | None) -> float | None:
    if not isinstance(payload, Mapping):
        return None
    for key in _SCORE_KEYS:
        if key in payload:
            number = _as_number(payload.get(key))
            if number is not None:
                return number
    return _as_number(payload.get("score"))


def _copy_existing_rating(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    for key in _RATING_KEYS:
        text = _as_str(payload.get(key))
        if text is not None:
            return text
    return None


def _get(payload: Mapping[str, Any] | None, key: str) -> Any:
    if not isinstance(payload, Mapping):
        return None
    return payload.get(key)


def _as_mapping(value: object) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return {str(k): value[k] for k in value}
    return None


def _as_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        return _as_number(value.get("value"))
    inner = getattr(value, "value", value)
    if inner is not value and not isinstance(inner, (int, float)):
        return _as_number(inner)
    try:
        return float(inner)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_str(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    rows: list[str] = []
    for item in value:
        text = _as_str(item)
        if text is not None:
            rows.append(text)
    return tuple(rows)
