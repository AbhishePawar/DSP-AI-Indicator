"""Tests for workflow_automation.evaluation — pure comparison logic."""

from __future__ import annotations

from datetime import date

from workflow_automation import AlertStatus
from workflow_automation.evaluation import (
    evaluate_earnings_alert,
    evaluate_price_alert,
    evaluate_research_stale_alert,
    evaluate_valuation_alert,
)


class TestPriceAlert:
    def test_unavailable_without_quote(self) -> None:
        result = evaluate_price_alert(
            direction="above", threshold_price=100.0, current_price=None, symbol="AAPL"
        )
        assert result.status is AlertStatus.UNAVAILABLE

    def test_triggers_above(self) -> None:
        result = evaluate_price_alert(
            direction="above", threshold_price=100.0, current_price=105.0, symbol="AAPL"
        )
        assert result.status is AlertStatus.TRIGGERED

    def test_not_triggered_below_threshold_for_above_direction(self) -> None:
        result = evaluate_price_alert(
            direction="above", threshold_price=100.0, current_price=95.0, symbol="AAPL"
        )
        assert result.status is AlertStatus.NOT_TRIGGERED

    def test_triggers_below(self) -> None:
        result = evaluate_price_alert(
            direction="below", threshold_price=100.0, current_price=95.0, symbol="AAPL"
        )
        assert result.status is AlertStatus.TRIGGERED

    def test_boundary_triggers(self) -> None:
        result = evaluate_price_alert(
            direction="above", threshold_price=100.0, current_price=100.0, symbol="AAPL"
        )
        assert result.status is AlertStatus.TRIGGERED


class TestValuationAlert:
    def test_unavailable_without_class(self) -> None:
        result = evaluate_valuation_alert(
            watch_class="overvalued", current_class=None, symbol="AAPL"
        )
        assert result.status is AlertStatus.UNAVAILABLE

    def test_unavailable_when_current_class_unavailable(self) -> None:
        result = evaluate_valuation_alert(
            watch_class="overvalued", current_class="unavailable", symbol="AAPL"
        )
        assert result.status is AlertStatus.UNAVAILABLE

    def test_triggers_on_match(self) -> None:
        result = evaluate_valuation_alert(
            watch_class="overvalued", current_class="overvalued", symbol="AAPL"
        )
        assert result.status is AlertStatus.TRIGGERED

    def test_not_triggered_on_mismatch(self) -> None:
        result = evaluate_valuation_alert(
            watch_class="overvalued", current_class="undervalued", symbol="AAPL"
        )
        assert result.status is AlertStatus.NOT_TRIGGERED


class TestResearchStaleAlert:
    def test_unavailable_without_last_analysed_at(self) -> None:
        result = evaluate_research_stale_alert(
            last_analysed_at=None, max_age_days=90, symbol="AAPL"
        )
        assert result.status is AlertStatus.UNAVAILABLE

    def test_unavailable_on_unparseable_date(self) -> None:
        result = evaluate_research_stale_alert(
            last_analysed_at="not-a-date", max_age_days=90, symbol="AAPL"
        )
        assert result.status is AlertStatus.UNAVAILABLE

    def test_triggers_when_stale(self) -> None:
        result = evaluate_research_stale_alert(
            last_analysed_at="2024-01-01",
            max_age_days=90,
            symbol="AAPL",
            as_of=date(2024, 6, 1),
        )
        assert result.status is AlertStatus.TRIGGERED
        assert result.observed_value == (date(2024, 6, 1) - date(2024, 1, 1)).days

    def test_not_triggered_when_fresh(self) -> None:
        result = evaluate_research_stale_alert(
            last_analysed_at="2024-01-01",
            max_age_days=90,
            symbol="AAPL",
            as_of=date(2024, 1, 10),
        )
        assert result.status is AlertStatus.NOT_TRIGGERED


class TestEarningsAlert:
    def test_always_unavailable(self) -> None:
        result = evaluate_earnings_alert(symbol="AAPL")
        assert result.status is AlertStatus.UNAVAILABLE
        assert "Data unavailable" in result.message
