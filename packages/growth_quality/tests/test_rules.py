"""Boundary tests for Growth Quality helpers."""

from __future__ import annotations

from growth_quality.rules import _map_growth, mean_present
from growth_quality.signals import assessment_score_01, safe_getattr


def test_helpers() -> None:
    assert mean_present([]) is None
    assert mean_present([None, 0.5, 1.0]) == 0.75
    assert _map_growth(None) is None
    assert _map_growth(0.12) is not None
    assert safe_getattr(None, "a") is None
    assert assessment_score_01(None, "x") is None
