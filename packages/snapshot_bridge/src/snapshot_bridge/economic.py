"""EconomicSnapshot construction from contracts EconomicSeries."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date

from contracts.domain.economic_series import EconomicSeries
from core.exceptions import ValidationError
from economic import EconomicSnapshot
from snapshot_bridge.derivation import (
    latest_as_of,
    normalize_liquidity,
    percent_level_to_decimal,
    period_change,
    yoy_growth,
)
from snapshot_bridge.exceptions import SnapshotBridgeError

__all__ = ["EconomicSnapshotBuilder"]

_CODE_ALIASES: dict[str, str] = {
    "GDP": "GDP",
    "CPI": "CPI",
    "INFLATION": "CPI",
    "INTEREST_RATE": "INTEREST_RATE",
    "FEDFUNDS": "INTEREST_RATE",
    "PMI": "PMI",
    "M2": "M2",
    "MONEY_SUPPLY": "M2",
    "LIQUIDITY": "M2",
    "UNEMPLOYMENT": "UNEMPLOYMENT",
    "UNRATE": "UNEMPLOYMENT",
    "INDPRO": "INDPRO",
    "INDUSTRIAL_PRODUCTION": "INDPRO",
}


def _index_series(
    series_by_code: Mapping[str, EconomicSeries],
) -> dict[str, EconomicSeries]:
    """Normalize keys to canonical platform codes."""
    indexed: dict[str, EconomicSeries] = {}
    for key, series in series_by_code.items():
        canonical = _CODE_ALIASES.get(key.strip().upper())
        if canonical is None:
            canonical = _CODE_ALIASES.get(series.indicator_code.strip().upper())
        if canonical is None:
            continue
        indexed[canonical] = series
    return indexed


def _latest_level(series: EconomicSeries | None) -> float | None:
    if series is None or not series.points:
        return None
    return series.points[-1].value


class EconomicSnapshotBuilder:
    """Bridge ``EconomicSeries`` maps into ``EconomicSnapshot``.

    Derives point-in-time fields the Economic Engine expects:

    * ``gdp_growth`` — YoY growth of GDP levels (decimal)
    * ``cpi_inflation`` — YoY growth of CPI index (decimal)
    * ``interest_rate`` — latest FEDFUNDS as decimal
    * ``interest_rate_change`` — latest − prior (decimal)
    * ``unemployment`` — latest UNRATE as decimal
    * ``pmi`` — latest PMI index (unchanged scale)
    * ``liquidity_indicator`` — M2 YoY growth mapped to ``[0, 1]``

    Missing series leave the corresponding field ``None`` (graceful
    degradation). ``currency_trend`` is not derived from FRED catalogs
    today and remains ``None``.
    """

    @staticmethod
    def build(
        series_by_code: Mapping[str, EconomicSeries],
        *,
        country: str = "US",
        as_of: date | None = None,
    ) -> EconomicSnapshot:
        """Assemble a validated ``EconomicSnapshot``.

        Args:
            series_by_code: Mapping of platform indicator codes (or
                aliases) to ``EconomicSeries``. Empty mapping is allowed
                — every optional field will be ``None``.
            country: ISO country stamped onto the snapshot.
            as_of: Snapshot date. Defaults to the latest observation
                date across available series; required when no series
                are provided.

        Returns:
            Engine-native ``EconomicSnapshot``.

        Raises:
            SnapshotBridgeError: If ``as_of`` cannot be determined or
                the engine rejects the constructed snapshot.
        """
        indexed = _index_series(series_by_code)
        resolved_as_of = as_of or latest_as_of(list(indexed.values()))
        if resolved_as_of is None:
            msg = (
                "as_of is required when no economic series with "
                "observations are provided"
            )
            raise SnapshotBridgeError(msg)

        gdp = indexed.get("GDP")
        cpi = indexed.get("CPI")
        rates = indexed.get("INTEREST_RATE")
        unemployment = indexed.get("UNEMPLOYMENT")
        pmi = indexed.get("PMI")
        m2 = indexed.get("M2")

        rate_level = percent_level_to_decimal(_latest_level(rates))
        # FEDFUNDS levels are percent; consecutive difference is in
        # percentage points (e.g. 5.50 − 5.25 = 0.25 pp → 0.0025 decimal).
        rate_change_pp = period_change(rates)
        rate_change = (
            rate_change_pp / 100.0 if rate_change_pp is not None else None
        )

        try:
            return EconomicSnapshot(
                as_of=resolved_as_of,
                gdp_growth=yoy_growth(gdp),
                cpi_inflation=yoy_growth(cpi),
                interest_rate=rate_level,
                interest_rate_change=rate_change,
                unemployment=percent_level_to_decimal(_latest_level(unemployment)),
                pmi=_latest_level(pmi),
                currency_trend=None,
                liquidity_indicator=normalize_liquidity(m2),
                country=country,
            )
        except ValidationError as exc:
            msg = f"failed to build EconomicSnapshot: {exc}"
            raise SnapshotBridgeError(msg) from exc
