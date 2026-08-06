"""Serde helpers for Research Intelligence (EPIC-011B)."""

from __future__ import annotations

from typing import Any

from dsp_platform.research_intelligence.models import (
    CalibrationReport,
    OutcomeMeasurement,
    PerformanceDashboard,
    ResearchInsightBundle,
    ResearchSnapshot,
)

__all__ = [
    "calibration_to_dict",
    "dashboard_to_dict",
    "insights_to_dict",
    "outcome_to_dict",
    "snapshot_to_dict",
]


def snapshot_to_dict(snapshot: ResearchSnapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def outcome_to_dict(outcome: OutcomeMeasurement) -> dict[str, Any]:
    return outcome.to_dict()


def calibration_to_dict(report: CalibrationReport) -> dict[str, Any]:
    return report.to_dict()


def dashboard_to_dict(dashboard: PerformanceDashboard) -> dict[str, Any]:
    return dashboard.to_dict()


def insights_to_dict(bundle: ResearchInsightBundle) -> dict[str, Any]:
    return bundle.to_dict()
