"""Summary builders for Business Quality Aggregator (F3.7).

Pure packaging of existing BusinessQualityAnalysis fields — no new analytics.
"""

from __future__ import annotations

from typing import Iterable

from business_quality.business_quality_models import (
    BusinessQualityAnalysis,
    OverallRating,
)
from business_quality.business_quality_report_models import (
    ConfidenceSummary,
    ModuleBreakdownEntry,
)
from business_quality.scoring import Confidence

__all__ = [
    "MODULE_ORDER",
    "build_confidence_summary",
    "build_executive_summary",
    "build_module_breakdown",
    "build_recommended_interpretation",
    "dedupe_ordered",
    "extract_evidence",
    "extract_limitations",
    "extract_signals",
    "extract_strengths",
    "extract_weaknesses",
    "source_module_names",
]

MODULE_ORDER: tuple[tuple[str, str], ...] = (
    ("earnings_quality", "Earnings Quality"),
    ("capital_allocation", "Capital Allocation"),
    ("business_characteristics", "Business Characteristics"),
    ("competitive_position", "Competitive Position"),
)


def dedupe_ordered(items: Iterable[str]) -> tuple[str, ...]:
    """Deduplicate strings while preserving first-seen order."""
    return tuple(dict.fromkeys(s for s in items if s))


def build_executive_summary(analysis: BusinessQualityAnalysis) -> str:
    """Compose a short executive summary from existing analysis fields."""
    rating = analysis.overall_rating
    rating_text = rating.value if rating is not None else "unknown"
    score = analysis.overall_score
    score_text = (
        f"{score.value:.1f}"
        if score is not None and score.value is not None
        else "n/a"
    )
    conf = analysis.overall_confidence.value
    headline = ""
    if analysis.overall_assessment is not None and analysis.overall_assessment.headline:
        headline = analysis.overall_assessment.headline
    elif analysis.summary.headline:
        headline = analysis.summary.headline
    if headline:
        return (
            f"{headline} Overall score={score_text}; "
            f"rating={rating_text}; confidence={conf}."
        )
    return (
        f"Business quality rating={rating_text}; score={score_text}; "
        f"confidence={conf}."
    )


def build_recommended_interpretation(analysis: BusinessQualityAnalysis) -> str:
    """Map existing overall rating to a standardized interpretation string."""
    rating = analysis.overall_rating
    if rating is OverallRating.EXCELLENT:
        return (
            "Business quality indicators are excellent across composed modules; "
            "interpret as high structural quality within available financial evidence."
        )
    if rating is OverallRating.STRONG:
        return (
            "Business quality indicators are strong; minor module weaknesses may "
            "exist but overall composition is favorable."
        )
    if rating is OverallRating.GOOD:
        return (
            "Business quality indicators are good; review module breakdown for "
            "specific strengths and residual risks."
        )
    if rating is OverallRating.AVERAGE:
        return (
            "Business quality indicators are average; treat as mixed evidence and "
            "inspect module-level flags before drawing conclusions."
        )
    if rating is OverallRating.WEAK:
        return (
            "Business quality indicators are weak; prioritize critical and warning "
            "signals in the module breakdown."
        )
    if rating is OverallRating.POOR:
        return (
            "Business quality indicators are poor; elevated risks dominate the "
            "composed assessment under available evidence."
        )
    return (
        "Business quality rating is unavailable or incomplete; rely on module "
        "breakdown and evidence summary only."
    )


def extract_strengths(analysis: BusinessQualityAnalysis) -> tuple[str, ...]:
    parts: list[str] = []
    if analysis.overall_assessment is not None:
        parts.extend(analysis.overall_assessment.strengths)
    parts.extend(analysis.summary.strengths)
    return dedupe_ordered(parts)


def extract_weaknesses(analysis: BusinessQualityAnalysis) -> tuple[str, ...]:
    parts: list[str] = []
    if analysis.overall_assessment is not None:
        parts.extend(analysis.overall_assessment.weaknesses)
    parts.extend(analysis.summary.weaknesses)
    return dedupe_ordered(parts)


def extract_signals(
    analysis: BusinessQualityAnalysis,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return (key_risks, positive_signals, warning_signals) from overall_flags."""
    risks: list[str] = []
    positives: list[str] = []
    warnings: list[str] = []
    flags = analysis.overall_flags
    if flags is not None:
        for f in flags.critical:
            risks.append(f"{f.source}:{f.value}")
        for f in flags.positive:
            positives.append(f"{f.source}:{f.value}")
        for f in flags.warning:
            warnings.append(f"{f.source}:{f.value}")
    return (
        dedupe_ordered(risks),
        dedupe_ordered(positives),
        dedupe_ordered(warnings),
    )


def extract_evidence(analysis: BusinessQualityAnalysis) -> tuple[str, ...]:
    parts: list[str] = []
    if analysis.overall_assessment is not None:
        parts.extend(analysis.overall_assessment.evidence_summary)
    parts.extend(analysis.summary.key_observations)
    for title, block in (
        ("eq", analysis.earnings_quality),
        ("ca", analysis.capital_allocation),
        ("bc", analysis.business_characteristics),
        ("cp", analysis.competitive_position),
    ):
        if block is None:
            continue
        for item in getattr(block, "evidence", ())[:3]:
            parts.append(f"{title}:{item}")
    return dedupe_ordered(parts)


def extract_limitations(analysis: BusinessQualityAnalysis) -> tuple[str, ...]:
    parts: list[str] = [
        "Report aggregates BusinessQualityAnalysis only; no new financial calculations.",
        "No peer comparison, valuation, forecasting, or provider data.",
    ]
    if analysis.overall_assessment is not None:
        parts.extend(analysis.overall_assessment.limitations)
    return dedupe_ordered(parts)


def build_module_breakdown(
    analysis: BusinessQualityAnalysis,
) -> tuple[ModuleBreakdownEntry, ...]:
    weights = analysis.weights_used.as_dict() if analysis.weights_used else {}
    modules = {
        "earnings_quality": analysis.earnings_quality,
        "capital_allocation": analysis.capital_allocation,
        "business_characteristics": analysis.business_characteristics,
        "competitive_position": analysis.competitive_position,
    }
    entries: list[ModuleBreakdownEntry] = []
    for name, label in MODULE_ORDER:
        mod = modules.get(name)
        if mod is None:
            entries.append(
                ModuleBreakdownEntry(
                    name=name,
                    label=label,
                    weight=weights.get(name),
                    present=False,
                )
            )
            continue
        score_obj = getattr(mod, "overall_score", None)
        score_val = getattr(score_obj, "value", None) if score_obj is not None else None
        rating = getattr(mod, "overall_rating", None)
        conf = getattr(mod, "confidence", None)
        entries.append(
            ModuleBreakdownEntry(
                name=name,
                label=label,
                rating=getattr(rating, "value", None) if rating is not None else None,
                score=score_val,
                confidence=getattr(conf, "value", None) if conf is not None else None,
                weight=weights.get(name),
                present=True,
            )
        )
    return tuple(entries)


def build_confidence_summary(analysis: BusinessQualityAnalysis) -> ConfidenceSummary:
    module_pairs: list[tuple[str, str]] = []
    for name, label in MODULE_ORDER:
        mod = getattr(analysis, name, None)
        if mod is None:
            continue
        conf = getattr(mod, "confidence", None)
        if conf is None:
            continue
        module_pairs.append((name, getattr(conf, "value", str(conf))))
    overall = analysis.overall_confidence
    if not isinstance(overall, Confidence):
        overall = Confidence.INSUFFICIENT
    if module_pairs:
        explanation = (
            f"Overall confidence={overall.value} from module confidences: "
            + ", ".join(f"{m}={c}" for m, c in module_pairs)
            + "."
        )
    else:
        explanation = (
            f"Overall confidence={overall.value}; module confidence details unavailable."
        )
    return ConfidenceSummary(
        overall=overall,
        module_confidences=tuple(module_pairs),
        explanation=explanation,
    )


def source_module_names(analysis: BusinessQualityAnalysis) -> tuple[str, ...]:
    """Deterministic list of present module names."""
    present: list[str] = []
    for name, _ in MODULE_ORDER:
        if getattr(analysis, name, None) is not None:
            present.append(name)
    return tuple(present)
