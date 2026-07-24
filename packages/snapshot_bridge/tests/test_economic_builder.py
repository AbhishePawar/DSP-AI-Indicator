"""Tests for EconomicSnapshotBuilder and derivation helpers."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.enums import EconomicFrequency
from economic.models import EconomicSnapshot
from snapshot_bridge import EconomicSnapshotBuilder, SnapshotBridgeError
from snapshot_bridge.derivation import (
    normalize_liquidity,
    percent_level_to_decimal,
    period_change,
    yoy_growth,
)


def _series(
    code: str,
    points: list[tuple[date, float]],
    *,
    frequency: EconomicFrequency = EconomicFrequency.MONTHLY,
    unit: str | None = None,
) -> EconomicSeries:
    return EconomicSeries(
        indicator_code=code,
        indicator_name=code,
        country="US",
        frequency=frequency,
        points=tuple(
            EconomicDataPoint(observation_date=d, value=v) for d, v in points
        ),
        unit=unit,
    )


class TestDerivation:
    def test_yoy_growth(self) -> None:
        series = _series(
            "GDP",
            [
                (date(2022, 1, 1), 100.0),
                (date(2022, 4, 1), 101.0),
                (date(2022, 7, 1), 102.0),
                (date(2022, 10, 1), 103.0),
                (date(2023, 1, 1), 110.0),
            ],
            frequency=EconomicFrequency.QUARTERLY,
        )
        assert yoy_growth(series) == pytest.approx(0.10)

    def test_yoy_growth_insufficient_history(self) -> None:
        series = _series("GDP", [(date(2023, 1, 1), 100.0)])
        assert yoy_growth(series) is None

    def test_percent_level_to_decimal(self) -> None:
        assert percent_level_to_decimal(5.33) == pytest.approx(0.0533)
        assert percent_level_to_decimal(0.04) == pytest.approx(0.04)
        assert percent_level_to_decimal(None) is None

    def test_period_change(self) -> None:
        series = _series(
            "INTEREST_RATE",
            [(date(2023, 1, 1), 5.00), (date(2023, 2, 1), 5.25)],
        )
        assert period_change(series) == pytest.approx(0.25)

    def test_normalize_liquidity(self) -> None:
        # +5% YoY → (0.05 + 0.02) / 0.14 ≈ 0.5
        series = _series(
            "M2",
            [(date(2022, 1, 1), 100.0), (date(2023, 1, 1), 105.0)],
        )
        score = normalize_liquidity(series)
        assert score is not None
        assert 0.0 <= score <= 1.0
        assert score == pytest.approx((0.05 + 0.02) / 0.14)


class TestEconomicSnapshotBuilder:
    def test_full_derivation(self) -> None:
        series_map = {
            "GDP": _series(
                "GDP",
                [
                    (date(2022, 1, 1), 100.0),
                    (date(2023, 1, 1), 103.0),
                ],
                frequency=EconomicFrequency.QUARTERLY,
            ),
            "CPI": _series(
                "CPI",
                [
                    (date(2022, 6, 1), 100.0),
                    (date(2023, 6, 1), 103.0),
                ],
            ),
            "INTEREST_RATE": _series(
                "INTEREST_RATE",
                [
                    (date(2023, 5, 1), 5.00),
                    (date(2023, 6, 1), 5.25),
                ],
                unit="percent",
            ),
            "PMI": _series("PMI", [(date(2023, 6, 1), 52.0)]),
            "M2": _series(
                "M2",
                [(date(2022, 6, 1), 100.0), (date(2023, 6, 1), 108.0)],
            ),
            "UNEMPLOYMENT": _series(
                "UNEMPLOYMENT", [(date(2023, 6, 1), 3.7)], unit="percent"
            ),
        }

        snapshot = EconomicSnapshotBuilder.build(series_map, country="US")

        assert isinstance(snapshot, EconomicSnapshot)
        assert snapshot.as_of == date(2023, 6, 1)
        assert snapshot.gdp_growth == pytest.approx(0.03)
        assert snapshot.cpi_inflation == pytest.approx(0.03)
        assert snapshot.interest_rate == pytest.approx(0.0525)
        assert snapshot.interest_rate_change == pytest.approx(0.0025)
        assert snapshot.pmi == pytest.approx(52.0)
        assert snapshot.unemployment == pytest.approx(0.037)
        assert snapshot.liquidity_indicator is not None
        assert 0.0 <= snapshot.liquidity_indicator <= 1.0
        assert snapshot.currency_trend is None

    def test_partial_data_graceful(self) -> None:
        snapshot = EconomicSnapshotBuilder.build(
            {"PMI": _series("PMI", [(date(2023, 1, 1), 48.0)])},
            country="US",
        )
        assert snapshot.pmi == pytest.approx(48.0)
        assert snapshot.gdp_growth is None
        assert snapshot.cpi_inflation is None
        assert snapshot.interest_rate is None
        assert snapshot.liquidity_indicator is None

    def test_empty_requires_as_of(self) -> None:
        with pytest.raises(SnapshotBridgeError, match="as_of"):
            EconomicSnapshotBuilder.build({})

    def test_empty_with_explicit_as_of(self) -> None:
        snapshot = EconomicSnapshotBuilder.build(
            {}, country="US", as_of=date(2024, 1, 1)
        )
        assert snapshot.as_of == date(2024, 1, 1)
        assert snapshot.gdp_growth is None

    def test_alias_keys(self) -> None:
        snapshot = EconomicSnapshotBuilder.build(
            {
                "INFLATION": _series(
                    "CPI",
                    [(date(2022, 1, 1), 100.0), (date(2023, 1, 1), 102.0)],
                ),
                "FEDFUNDS": _series(
                    "INTEREST_RATE", [(date(2023, 1, 1), 4.0)]
                ),
            }
        )
        assert snapshot.cpi_inflation == pytest.approx(0.02)
        assert snapshot.interest_rate == pytest.approx(0.04)

    def test_deterministic(self) -> None:
        series_map = {
            "PMI": _series("PMI", [(date(2023, 1, 1), 50.0)]),
        }
        assert EconomicSnapshotBuilder.build(
            series_map
        ) == EconomicSnapshotBuilder.build(series_map)
