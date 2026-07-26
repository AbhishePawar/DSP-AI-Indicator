"""Boundary tests for Earnings Quality helpers."""

from __future__ import annotations

from earnings_quality.rules import _map_ratio, mean_present
from earnings_quality.signals import assessment_score_01, safe_getattr


def test_helpers() -> None:
    assert mean_present([]) is None
    assert mean_present([None, 0.5, 1.0]) == 0.75
    assert _map_ratio(None, good=1.0, bad=0.0) is None
    assert _map_ratio(1.0, good=1.0, bad=0.0) == 1.0
    assert safe_getattr(None, "a") is None
    assert assessment_score_01(None, "x") is None
