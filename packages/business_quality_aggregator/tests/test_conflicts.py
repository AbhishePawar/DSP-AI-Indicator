"""Conflict resolution and adapter boundary tests."""

from __future__ import annotations

from types import SimpleNamespace

from business_quality_aggregator.adapters import (
    component_score_01,
    safe_score_value,
)
from business_quality_aggregator.conflicts import CONFLICT_PENALTY_CAP, resolve_conflicts


def _scored(value: float | None) -> SimpleNamespace:
    return SimpleNamespace(
        score=SimpleNamespace(value=value),
        components=(),
        confidence=SimpleNamespace(value=0.7, basis="mock"),
    )


def _with_components(value: float, components: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(
        score=SimpleNamespace(value=value),
        components=components,
        confidence=SimpleNamespace(value=0.7, basis="mock"),
    )


def test_helpers() -> None:
    assert safe_score_value(None) is None
    assert safe_score_value(_scored(55.0)) == 55.0
    assert component_score_01(None, "x") is None


def test_strong_moat_weak_balance_sheet_conflict() -> None:
    result = resolve_conflicts(
        raw_score=70.0,
        economic_moat=_scored(80.0),
        management_quality=_scored(60.0),
        financial_strength=_scored(40.0),
        earnings_quality=_scored(60.0),
        growth_quality=_scored(60.0),
    )
    assert any(
        a.rule_id == "strong_moat_weak_balance_sheet" for a in result.adjustments
    )
    assert result.total_penalty > 0
    assert result.adjusted_score is not None
    assert result.adjusted_score < 70.0


def test_strong_growth_poor_cash_generation() -> None:
    fs = _with_components(
        60.0,
        [
            SimpleNamespace(
                dimension=SimpleNamespace(value="cash_flow_quality"),
                score=SimpleNamespace(value=30.0),
            )
        ],
    )
    result = resolve_conflicts(
        raw_score=72.0,
        economic_moat=_scored(60.0),
        management_quality=_scored(60.0),
        financial_strength=fs,
        earnings_quality=_scored(60.0),
        growth_quality=_scored(80.0),
    )
    assert any(
        a.rule_id == "strong_growth_poor_cash_generation" for a in result.adjustments
    )


def test_outstanding_growth_deteriorating_margins() -> None:
    eq = _with_components(
        60.0,
        [
            SimpleNamespace(
                dimension=SimpleNamespace(value="margin_stability"),
                score=SimpleNamespace(value=30.0),
            )
        ],
    )
    result = resolve_conflicts(
        raw_score=75.0,
        economic_moat=_scored(60.0),
        management_quality=_scored(60.0),
        financial_strength=_scored(60.0),
        earnings_quality=eq,
        growth_quality=_scored(85.0),
    )
    assert any(
        a.rule_id == "outstanding_growth_deteriorating_margins"
        for a in result.adjustments
    )


def test_conflict_penalty_cap() -> None:
    """Multiple conflicts cannot exceed documented cap."""
    fs = _with_components(
        40.0,
        [
            SimpleNamespace(
                dimension=SimpleNamespace(value="cash_flow_quality"),
                score=SimpleNamespace(value=20.0),
            ),
            SimpleNamespace(
                dimension=SimpleNamespace(value="liquidity"),
                score=SimpleNamespace(value=20.0),
            ),
            SimpleNamespace(
                dimension=SimpleNamespace(value="profitability_stability"),
                score=SimpleNamespace(value=80.0),
            ),
        ],
    )
    mq = _with_components(
        80.0,
        [
            SimpleNamespace(
                dimension=SimpleNamespace(value="capital_allocation"),
                score=SimpleNamespace(value=20.0),
            )
        ],
    )
    eq = _with_components(
        40.0,
        [
            SimpleNamespace(
                dimension=SimpleNamespace(value="margin_stability"),
                score=SimpleNamespace(value=20.0),
            )
        ],
    )
    result = resolve_conflicts(
        raw_score=80.0,
        economic_moat=_scored(85.0),
        management_quality=mq,
        financial_strength=fs,
        earnings_quality=eq,
        growth_quality=_scored(85.0),
    )
    assert result.total_penalty <= CONFLICT_PENALTY_CAP
