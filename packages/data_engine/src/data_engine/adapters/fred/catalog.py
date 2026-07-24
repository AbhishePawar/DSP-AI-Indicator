"""FRED series catalog: platform indicator codes → FRED series metadata.

This is the only module that knows which FRED ``series_id`` backs each
platform-agnostic indicator code. Adapters outside FRED must not import
these ids; other providers maintain their own catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.enums import EconomicFrequency
from data_engine.exceptions import DataEngineError

__all__ = [
    "CANONICAL_INDICATOR_CODES",
    "FredSeriesSpec",
    "resolve_fred_series",
    "supported_indicator_codes",
]


@dataclass(frozen=True, slots=True)
class FredSeriesSpec:
    """Metadata for one FRED-backed platform indicator.

    Attributes:
        platform_code: Canonical, provider-agnostic indicator code
            (e.g. ``"GDP"``, ``"CPI"``).
        fred_series_id: FRED series identifier (e.g. ``"GDP"``,
            ``"CPIAUCSL"``).
        indicator_name: Human-readable name stamped onto
            ``EconomicSeries``.
        frequency: Observation frequency of the FRED series.
        unit: Optional unit of measure.
        country: ISO country this catalog entry applies to (FRED
            entries in this package are US-focused).
    """

    platform_code: str
    fred_series_id: str
    indicator_name: str
    frequency: EconomicFrequency
    unit: str | None = None
    country: str = "US"


_CATALOG: dict[str, FredSeriesSpec] = {
    "GDP": FredSeriesSpec(
        platform_code="GDP",
        fred_series_id="GDP",
        indicator_name="Gross Domestic Product",
        frequency=EconomicFrequency.QUARTERLY,
        unit="billions_of_dollars",
    ),
    "CPI": FredSeriesSpec(
        platform_code="CPI",
        fred_series_id="CPIAUCSL",
        indicator_name="Consumer Price Index for All Urban Consumers",
        frequency=EconomicFrequency.MONTHLY,
        unit="index_1982_84_100",
    ),
    "INFLATION": FredSeriesSpec(
        platform_code="CPI",
        fred_series_id="CPIAUCSL",
        indicator_name="Consumer Price Index for All Urban Consumers",
        frequency=EconomicFrequency.MONTHLY,
        unit="index_1982_84_100",
    ),
    "INTEREST_RATE": FredSeriesSpec(
        platform_code="INTEREST_RATE",
        fred_series_id="FEDFUNDS",
        indicator_name="Federal Funds Effective Rate",
        frequency=EconomicFrequency.MONTHLY,
        unit="percent",
    ),
    "FEDFUNDS": FredSeriesSpec(
        platform_code="INTEREST_RATE",
        fred_series_id="FEDFUNDS",
        indicator_name="Federal Funds Effective Rate",
        frequency=EconomicFrequency.MONTHLY,
        unit="percent",
    ),
    "PMI": FredSeriesSpec(
        platform_code="PMI",
        fred_series_id="NAPM",
        indicator_name="ISM Manufacturing: PMI Composite Index",
        frequency=EconomicFrequency.MONTHLY,
        unit="index",
    ),
    "M2": FredSeriesSpec(
        platform_code="M2",
        fred_series_id="M2SL",
        indicator_name="M2 Money Stock",
        frequency=EconomicFrequency.MONTHLY,
        unit="billions_of_dollars",
    ),
    "MONEY_SUPPLY": FredSeriesSpec(
        platform_code="M2",
        fred_series_id="M2SL",
        indicator_name="M2 Money Stock",
        frequency=EconomicFrequency.MONTHLY,
        unit="billions_of_dollars",
    ),
    "LIQUIDITY": FredSeriesSpec(
        platform_code="M2",
        fred_series_id="M2SL",
        indicator_name="M2 Money Stock",
        frequency=EconomicFrequency.MONTHLY,
        unit="billions_of_dollars",
    ),
    "UNEMPLOYMENT": FredSeriesSpec(
        platform_code="UNEMPLOYMENT",
        fred_series_id="UNRATE",
        indicator_name="Unemployment Rate",
        frequency=EconomicFrequency.MONTHLY,
        unit="percent",
    ),
    "UNRATE": FredSeriesSpec(
        platform_code="UNEMPLOYMENT",
        fred_series_id="UNRATE",
        indicator_name="Unemployment Rate",
        frequency=EconomicFrequency.MONTHLY,
        unit="percent",
    ),
    "INDPRO": FredSeriesSpec(
        platform_code="INDPRO",
        fred_series_id="INDPRO",
        indicator_name="Industrial Production Index",
        frequency=EconomicFrequency.MONTHLY,
        unit="index_2017_100",
    ),
    "INDUSTRIAL_PRODUCTION": FredSeriesSpec(
        platform_code="INDPRO",
        fred_series_id="INDPRO",
        indicator_name="Industrial Production Index",
        frequency=EconomicFrequency.MONTHLY,
        unit="index_2017_100",
    ),
}

CANONICAL_INDICATOR_CODES: frozenset[str] = frozenset(
    {
        "GDP",
        "CPI",
        "INTEREST_RATE",
        "PMI",
        "M2",
        "UNEMPLOYMENT",
        "INDPRO",
    }
)


def supported_indicator_codes() -> tuple[str, ...]:
    """Return sorted canonical platform indicator codes this catalog covers."""
    return tuple(sorted(CANONICAL_INDICATOR_CODES))


def resolve_fred_series(indicator_code: str, country: str) -> FredSeriesSpec:
    """Resolve a platform indicator code to a FRED series specification.

    Args:
        indicator_code: Provider-agnostic or alias code (case-insensitive).
        country: ISO 3166-1 alpha-2 country code.

    Returns:
        The matching :class:`FredSeriesSpec`.

    Raises:
        DataEngineError: If ``country`` is not supported by this catalog,
            or ``indicator_code`` is unknown.
    """
    normalized_country = country.strip().upper()
    if normalized_country != "US":
        msg = (
            f"fred adapter currently supports country 'US' only, "
            f"got {country!r}"
        )
        raise DataEngineError(msg)

    key = indicator_code.strip().upper()
    spec = _CATALOG.get(key)
    if spec is None:
        supported = ", ".join(supported_indicator_codes())
        msg = (
            f"unsupported economic indicator_code {indicator_code!r}; "
            f"supported canonical codes: {supported}"
        )
        raise DataEngineError(msg)
    return spec
