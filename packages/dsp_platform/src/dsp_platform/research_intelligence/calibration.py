"""Confidence Calibration engine (EPIC-011B).

Produces High/Med/Low accuracy, calibration curve, drift, and reliability
metrics from measured outcomes only — never fabricates outcomes.
"""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_intelligence.models import (
    CALIBRATION_BUCKETS,
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    UNAVAILABLE_MESSAGE,
    CalibrationReport,
    OutcomeMeasurement,
    utc_now,
)

__all__ = ["build_calibration_report"]


def _bucket_stats(
    outcomes: tuple[OutcomeMeasurement, ...]
) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for bucket in CALIBRATION_BUCKETS:
        subset = [
            o
            for o in outcomes
            if (o.confidence_label or "").lower() == bucket
            and o.recommendation_accuracy in {"correct", "incorrect"}
        ]
        if not subset:
            stats[bucket] = {
                "sample_size": 0,
                "accuracy": None,
                "message": UNAVAILABLE_MESSAGE,
            }
            continue
        correct = sum(1 for o in subset if o.recommendation_accuracy == "correct")
        stats[bucket] = {
            "sample_size": len(subset),
            "accuracy": correct / len(subset),
            "correct": correct,
            "incorrect": len(subset) - correct,
            "message": None,
        }
    return stats


def _calibration_curve(
    outcomes: tuple[OutcomeMeasurement, ...]
) -> tuple[Mapping[str, Any], ...]:
    # Expected confidence midpoints for institutional buckets
    expected = {"high": 0.85, "medium": 0.55, "low": 0.25}
    points: list[dict[str, Any]] = []
    for bucket in CALIBRATION_BUCKETS:
        subset = [
            o
            for o in outcomes
            if (o.confidence_label or "").lower() == bucket
            and o.recommendation_accuracy in {"correct", "incorrect"}
        ]
        if not subset:
            points.append(
                {
                    "bucket": bucket,
                    "expected_confidence": expected[bucket],
                    "observed_accuracy": None,
                    "gap": None,
                    "sample_size": 0,
                    "message": UNAVAILABLE_MESSAGE,
                }
            )
            continue
        observed = sum(
            1 for o in subset if o.recommendation_accuracy == "correct"
        ) / len(subset)
        points.append(
            {
                "bucket": bucket,
                "expected_confidence": expected[bucket],
                "observed_accuracy": observed,
                "gap": observed - expected[bucket],
                "sample_size": len(subset),
                "message": None,
            }
        )
    return tuple(points)


def _drift(curve: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    gaps = [
        abs(float(p["gap"]))
        for p in curve
        if p.get("gap") is not None
    ]
    if not gaps:
        return {
            "mean_absolute_gap": None,
            "max_absolute_gap": None,
            "status": "unavailable",
            "message": UNAVAILABLE_MESSAGE,
        }
    mean_gap = sum(gaps) / len(gaps)
    max_gap = max(gaps)
    status = "stable"
    if mean_gap > 0.2:
        status = "drifting"
    elif mean_gap > 0.1:
        status = "watch"
    return {
        "mean_absolute_gap": mean_gap,
        "max_absolute_gap": max_gap,
        "status": status,
        "message": None,
    }


def _reliability(
    outcomes: tuple[OutcomeMeasurement, ...], bucket_stats: Mapping[str, Any]
) -> dict[str, Any]:
    measured = [
        o
        for o in outcomes
        if o.recommendation_accuracy in {"correct", "incorrect"}
    ]
    if not measured:
        return {
            "overall_accuracy": None,
            "coverage_ratio": 0.0,
            "brier_proxy": None,
            "message": UNAVAILABLE_MESSAGE,
        }
    overall = sum(
        1 for o in measured if o.recommendation_accuracy == "correct"
    ) / len(measured)
    # Simple reliability proxy: mean squared gap vs bucket expected
    expected = {"high": 0.85, "medium": 0.55, "low": 0.25}
    squares: list[float] = []
    for bucket, stats in bucket_stats.items():
        acc = stats.get("accuracy")
        if acc is None:
            continue
        squares.append((float(acc) - expected.get(bucket, 0.5)) ** 2)
    brier = sum(squares) / len(squares) if squares else None
    return {
        "overall_accuracy": overall,
        "coverage_ratio": len(measured) / max(len(outcomes), 1),
        "brier_proxy": brier,
        "measured_count": len(measured),
        "message": None,
    }


def build_calibration_report(
    outcomes: tuple[OutcomeMeasurement, ...] | list[OutcomeMeasurement],
    *,
    window_months: int,
    result_id: str | None = None,
    created_at: str | None = None,
) -> CalibrationReport:
    outs = tuple(outcomes)
    buckets = _bucket_stats(outs)
    curve = _calibration_curve(outs)
    drift = _drift(curve)
    reliability = _reliability(outs, buckets)
    measured = sum(
        1
        for o in outs
        if o.recommendation_accuracy in {"correct", "incorrect"}
    )
    message = None if measured else UNAVAILABLE_MESSAGE
    return CalibrationReport(
        result_id=result_id or str(uuid.uuid4()),
        schema_version=RI_SCHEMA_VERSION,
        service_version=RI_SERVICE_VERSION,
        created_at=created_at or utc_now().isoformat(),
        window_months=window_months,
        bucket_accuracy=buckets,
        calibration_curve=curve,
        drift=drift,
        reliability=reliability,
        sample_size=measured,
        provenance={
            "source": "research_intelligence",
            "service_version": RI_SERVICE_VERSION,
            "engines_called": False,
            "providers_called": False,
            "measurement_only": True,
        },
        limitations=(
            "Calibration uses caller-supplied or registry-linked outcomes only.",
            "Missing horizon market data yields Data unavailable.",
            "Does not rewrite recommendations or confidence scores.",
        ),
        message=message,
    )
