"""Boundary tests for Management Quality helpers."""

from __future__ import annotations

from management_quality.rules import mean_present
from management_quality.signals import assessment_score_01, ratio_value, safe_getattr


def test_helpers() -> None:
    assert mean_present([]) is None
    assert mean_present([None, 0.5, 1.0]) == 0.75
    assert safe_getattr(None, "a") is None
    assert assessment_score_01(None, "x") is None

    class Ratio:
        def __init__(self, name: str, value: float) -> None:
            self.name = name
            self.value = value

    assert ratio_value((Ratio("roic", 0.2),), "roic") == 0.2
