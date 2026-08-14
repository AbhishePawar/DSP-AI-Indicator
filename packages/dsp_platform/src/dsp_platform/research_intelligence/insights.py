"""Research Intelligence insight aggregation (EPIC-011B)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from dsp_platform.research_intelligence.models import (
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    OutcomeMeasurement,
    ResearchInsightBundle,
    ResearchSnapshot,
    utc_now,
)

__all__ = ["build_insight_bundle"]


def _perf_rows(
    snapshots: tuple[ResearchSnapshot, ...],
    outcomes: tuple[OutcomeMeasurement, ...],
) -> list[dict[str, Any]]:
    by_id = {s.research_id: s for s in snapshots}
    rows: list[dict[str, Any]] = []
    for o in outcomes:
        if o.recommendation_accuracy not in {"correct", "incorrect"}:
            continue
        if o.price_change_pct is None:
            continue
        snap = by_id.get(o.research_id)
        rows.append(
            {
                "research_id": o.research_id,
                "symbol": snap.symbol if snap else None,
                "company": snap.company if snap else None,
                "sector": snap.sector if snap else None,
                "industry": snap.industry if snap else None,
                "recommendation": o.recommendation,
                "price_change_pct": o.price_change_pct,
                "recommendation_accuracy": o.recommendation_accuracy,
                "success_failure": o.success_failure,
            }
        )
    return rows


def _group_accuracy(
    snapshots: tuple[ResearchSnapshot, ...],
    outcomes: tuple[OutcomeMeasurement, ...],
    field: str,
) -> tuple[dict[str, Any], ...]:
    by_id = {s.research_id: s for s in snapshots}
    groups: dict[str, list[OutcomeMeasurement]] = defaultdict(list)
    for o in outcomes:
        if o.recommendation_accuracy not in {"correct", "incorrect"}:
            continue
        snap = by_id.get(o.research_id)
        key = (getattr(snap, field, None) if snap else None) or "unknown"
        groups[str(key)].append(o)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups.keys()):
        group = groups[key]
        correct = sum(1 for o in group if o.recommendation_accuracy == "correct")
        rows.append(
            {
                field: key,
                "sample_size": len(group),
                "accuracy": correct / len(group),
            }
        )
    return tuple(rows)


def build_insight_bundle(
    snapshots: tuple[ResearchSnapshot, ...] | list[ResearchSnapshot],
    outcomes: tuple[OutcomeMeasurement, ...] | list[OutcomeMeasurement],
    *,
    window_months: int,
    result_id: str | None = None,
    created_at: str | None = None,
    top_n: int = 5,
) -> ResearchInsightBundle:
    snaps = tuple(snapshots)
    outs = tuple(o for o in outcomes if o.window_months == window_months)
    rows = _perf_rows(snaps, outs)
    ranked = sorted(rows, key=lambda r: float(r["price_change_pct"]), reverse=True)
    best = tuple(ranked[:top_n])
    worst = tuple(list(reversed(ranked[-top_n:])) if ranked else ())

    # Coverage gaps: snapshots without measurable outcomes
    measured_ids = {
        o.research_id
        for o in outs
        if o.recommendation_accuracy in {"correct", "incorrect"}
    }
    gaps = tuple(
        {
            "research_id": s.research_id,
            "symbol": s.symbol,
            "company": s.company,
            "reason": UNAVAILABLE_MESSAGE,
            "detail": "Horizon market data unavailable for outcome measurement.",
        }
        for s in snaps
        if s.research_id not in measured_ids
    )

    sector_perf = _group_accuracy(snaps, outs, "sector")
    industry_perf = _group_accuracy(snaps, outs, "industry")

    drift_signals: list[dict[str, Any]] = []
    if not rows:
        drift_signals.append(
            {
                "signal": "insufficient_outcomes",
                "status": "unavailable",
                "message": UNAVAILABLE_MESSAGE,
            }
        )
    else:
        incorrect_rate = sum(
            1 for r in rows if r["recommendation_accuracy"] == "incorrect"
        ) / len(rows)
        if incorrect_rate > 0.5:
            drift_signals.append(
                {
                    "signal": "elevated_error_rate",
                    "status": "drifting",
                    "incorrect_rate": incorrect_rate,
                    "message": None,
                }
            )
        else:
            drift_signals.append(
                {
                    "signal": "error_rate",
                    "status": "stable",
                    "incorrect_rate": incorrect_rate,
                    "message": None,
                }
            )

    message = None if rows else UNAVAILABLE_MESSAGE
    return ResearchInsightBundle(
        result_id=result_id or str(uuid.uuid4()),
        schema_version=RI_SCHEMA_VERSION,
        service_version=RI_SERVICE_VERSION,
        created_at=created_at or utc_now().isoformat(),
        window_months=window_months,
        best_performers=best,
        worst_performers=worst,
        coverage_gaps=gaps,
        sector_performance=sector_perf,
        industry_performance=industry_perf,
        drift_signals=tuple(drift_signals),
        provenance={
            "source": "research_intelligence",
            "service_version": RI_SERVICE_VERSION,
            "engines_called": False,
            "providers_called": False,
            "measurement_only": True,
        },
        limitations=(
            "Insights summarize measured outcomes only; no live price fabrication.",
            "Coverage gaps report honest Data unavailable for missing horizons.",
        ),
        message=message,
    )
