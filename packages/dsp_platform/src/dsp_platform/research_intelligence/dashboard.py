"""Research Performance Dashboard aggregation (EPIC-011B)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Mapping

from dsp_platform.research_intelligence.calibration import build_calibration_report
from dsp_platform.research_intelligence.models import (
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    OutcomeMeasurement,
    PerformanceDashboard,
    ResearchSnapshot,
    utc_now,
)
from dsp_platform.research_intelligence.outcomes import normalize_recommendation_stance

__all__ = ["build_performance_dashboard"]


def _rate(correct: int, total: int) -> float | None:
    if total <= 0:
        return None
    return correct / total


def build_performance_dashboard(
    snapshots: tuple[ResearchSnapshot, ...] | list[ResearchSnapshot],
    outcomes: tuple[OutcomeMeasurement, ...] | list[OutcomeMeasurement],
    *,
    window_months: int,
    result_id: str | None = None,
    created_at: str | None = None,
) -> PerformanceDashboard:
    snaps = tuple(snapshots)
    outs = tuple(o for o in outcomes if o.window_months == window_months)
    measured = [
        o for o in outs if o.recommendation_accuracy in {"correct", "incorrect"}
    ]
    correct = sum(1 for o in measured if o.recommendation_accuracy == "correct")
    overall = _rate(correct, len(measured))
    rec_acc = overall

    iv_errors = [
        abs(float(o.iv_gap_at_horizon))
        for o in outs
        if o.iv_gap_at_horizon is not None
    ]
    iv_error: Any = (
        sum(iv_errors) / len(iv_errors) if iv_errors else UNAVAILABLE_MESSAGE
    )

    mos_vals = [
        float(s.margin_of_safety)
        for s in snaps
        if s.margin_of_safety is not None
    ]
    avg_mos: Any = sum(mos_vals) / len(mos_vals) if mos_vals else UNAVAILABLE_MESSAGE

    cal = build_calibration_report(
        outs,
        window_months=window_months,
        result_id=f"cal-{result_id or 'dash'}",
        created_at=created_at,
    )

    bull = [
        o
        for o in measured
        if normalize_recommendation_stance(o.recommendation) == "bullish"
    ]
    bear = [
        o
        for o in measured
        if normalize_recommendation_stance(o.recommendation) == "bearish"
    ]
    bull_success: Any = (
        _rate(
            sum(1 for o in bull if o.recommendation_accuracy == "correct"),
            len(bull),
        )
        if bull
        else UNAVAILABLE_MESSAGE
    )
    bear_success: Any = (
        _rate(
            sum(1 for o in bear if o.recommendation_accuracy == "correct"),
            len(bear),
        )
        if bear
        else UNAVAILABLE_MESSAGE
    )

    # FP: bullish + incorrect; FN: bearish + incorrect (directional framing)
    fp = sum(
        1
        for o in measured
        if normalize_recommendation_stance(o.recommendation) == "bullish"
        and o.recommendation_accuracy == "incorrect"
    )
    fn = sum(
        1
        for o in measured
        if normalize_recommendation_stance(o.recommendation) == "bearish"
        and o.recommendation_accuracy == "incorrect"
    )
    false_positives: Any = fp if measured else UNAVAILABLE_MESSAGE
    false_negatives: Any = fn if measured else UNAVAILABLE_MESSAGE

    by_sector: dict[str, list[ResearchSnapshot]] = defaultdict(list)
    for s in snaps:
        by_sector[s.sector or "unknown"].append(s)

    coverage = {
        "snapshot_count": len(snaps),
        "outcome_count": len(outs),
        "measured_count": len(measured),
        "unavailable_outcome_count": sum(
            1 for o in outs if o.message == UNAVAILABLE_MESSAGE
        ),
        "symbols": sorted({s.symbol for s in snaps if s.symbol}),
        "sectors": sorted(by_sector.keys()),
        "coverage_ratio": (
            len(measured) / len(outs) if outs else 0.0
        ),
    }

    # Trend: group measured outcomes by snapshot timestamp month prefix
    trend_map: dict[str, list[OutcomeMeasurement]] = defaultdict(list)
    snap_ts = {s.research_id: s.timestamp for s in snaps}
    for o in measured:
        ts = snap_ts.get(o.research_id, "")[:7] or "unknown"
        trend_map[ts].append(o)
    trends: list[dict[str, Any]] = []
    for period in sorted(trend_map.keys()):
        group = trend_map[period]
        c = sum(1 for o in group if o.recommendation_accuracy == "correct")
        trends.append(
            {
                "period": period,
                "sample_size": len(group),
                "accuracy": c / len(group) if group else None,
            }
        )

    message = None if measured else UNAVAILABLE_MESSAGE
    return PerformanceDashboard(
        result_id=result_id or str(uuid.uuid4()),
        schema_version=RI_SCHEMA_VERSION,
        service_version=RI_SERVICE_VERSION,
        created_at=created_at or utc_now().isoformat(),
        window_months=window_months,
        overall_accuracy=overall if overall is not None else UNAVAILABLE_MESSAGE,
        recommendation_accuracy=rec_acc if rec_acc is not None else UNAVAILABLE_MESSAGE,
        iv_error=iv_error,
        avg_mos=avg_mos,
        calibration_summary={
            "bucket_accuracy": dict(cal.bucket_accuracy),
            "drift": dict(cal.drift),
            "reliability": dict(cal.reliability),
            "sample_size": cal.sample_size,
        },
        bull_success=bull_success,
        bear_success=bear_success,
        false_positives=false_positives,
        false_negatives=false_negatives,
        holding_horizon_months=window_months,
        coverage=coverage,
        trends=tuple(trends),
        provenance={
            "source": "research_intelligence",
            "service_version": RI_SERVICE_VERSION,
            "engines_called": False,
            "providers_called": False,
            "measurement_only": True,
        },
        limitations=(
            "Dashboard aggregates registry snapshots and measured outcomes only.",
            "Missing horizon prices remain Data unavailable.",
            "No valuation or recommendation engines invoked.",
        ),
        message=message,
    )
