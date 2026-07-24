"""Default, provider-agnostic normalizer implementations.

These are ready-to-use reference implementations of the abstract
normalizer interfaces, built entirely out of the reusable
:class:`~data_engine.normalization.pipeline.TransformationPipeline` and
:mod:`data_engine.normalization.validation` building blocks. They
contain zero vendor-specific logic because ``RawMarketBar`` and its
siblings are already provider-neutral by the time a normalizer sees
them — any provider adapter can reuse
:class:`DefaultMarketDataNormalizer` as-is instead of writing its own
validation or transformation logic.

Market-data, fundamentals, and economic defaults are implemented.
Alternative-data defaults remain deferred until a real provider needs them.
"""

from __future__ import annotations

from typing import Any

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.domain.price_series import PriceSeries
from contracts.enums import BarFrequency, EconomicFrequency, StatementPeriodType
from contracts.exceptions import ContractValidationError
from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization.coercion import (
    coerce_date,
    coerce_float,
    coerce_optional_float,
    coerce_timestamp,
)
from data_engine.normalization.normalizers import (
    EconomicDataNormalizer,
    FundamentalNormalizer,
    MarketDataNormalizer,
)
from data_engine.normalization.pipeline import TransformationPipeline
from data_engine.normalization.records import (
    NormalizedBar,
    NormalizedObservation,
    NormalizedStatement,
)
from data_engine.normalization.validation.base import ValidationPipeline
from data_engine.normalization.validation.stages import (
    DuplicateDetectionStage,
    MissingValueValidationStage,
    OHLCConsistencyStage,
    RequiredFieldValidationStage,
    SortingVerificationStage,
    TimestampValidationStage,
    VolumeValidationStage,
)
from data_engine.raw_models.economic import RawEconomicDataPoint, RawEconomicSeries
from data_engine.raw_models.fundamentals import RawFundamentalData
from data_engine.raw_models.market import RawMarketBar, RawMarketSeries

__all__ = [
    "DefaultEconomicNormalizer",
    "DefaultFundamentalNormalizer",
    "DefaultMarketDataNormalizer",
]

_MISSING_VALUE_SENTINELS: frozenset[Any] = frozenset(
    {None, "", ".", "N/A", "n/a", "NA", "null", "NULL", "-"}
)

_FREQUENCY_ALIASES: dict[str, EconomicFrequency] = {
    "daily": EconomicFrequency.DAILY,
    "d": EconomicFrequency.DAILY,
    EconomicFrequency.DAILY.value: EconomicFrequency.DAILY,
    "weekly": EconomicFrequency.WEEKLY,
    "w": EconomicFrequency.WEEKLY,
    EconomicFrequency.WEEKLY.value: EconomicFrequency.WEEKLY,
    "monthly": EconomicFrequency.MONTHLY,
    "m": EconomicFrequency.MONTHLY,
    EconomicFrequency.MONTHLY.value: EconomicFrequency.MONTHLY,
    "quarterly": EconomicFrequency.QUARTERLY,
    "q": EconomicFrequency.QUARTERLY,
    EconomicFrequency.QUARTERLY.value: EconomicFrequency.QUARTERLY,
    "annual": EconomicFrequency.ANNUAL,
    "yearly": EconomicFrequency.ANNUAL,
    "a": EconomicFrequency.ANNUAL,
    EconomicFrequency.ANNUAL.value: EconomicFrequency.ANNUAL,
}

#: Canonical ``FundamentalStatement`` field names populated from
#: ``RawFundamentalData.line_items`` when present.
_STATEMENT_FIELDS: tuple[str, ...] = (
    "revenue",
    "cost_of_revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "cash_and_equivalents",
    "total_debt",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capital_expenditures",
)

#: Provider-neutral aliases accepted in ``line_items`` for each
#: canonical field. Adapters may emit either the canonical name or any
#: alias listed here; the normalizer is the single place that resolves
#: them so vendor adapters stay thin.
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenue", "totalRevenue", "total_revenue"),
    "cost_of_revenue": ("cost_of_revenue", "costOfRevenue", "costOfGoodsSold"),
    "gross_profit": ("gross_profit", "grossProfit"),
    "operating_income": ("operating_income", "operatingIncome", "ebit"),
    "net_income": ("net_income", "netIncome", "netIncomeApplicableToCommonShares"),
    "eps_basic": ("eps_basic", "basicEPS", "basicEps", "epsBasic"),
    "eps_diluted": ("eps_diluted", "dilutedEPS", "dilutedEps", "epsDiluted"),
    "total_assets": ("total_assets", "totalAssets"),
    "total_liabilities": (
        "total_liabilities",
        "totalLiab",
        "totalLiabilities",
        "totalLiabilitiesNetMinorityInterest",
    ),
    "total_equity": (
        "total_equity",
        "totalStockholderEquity",
        "stockholdersEquity",
        "totalEquityGrossMinorityInterest",
    ),
    "cash_and_equivalents": (
        "cash_and_equivalents",
        "cash",
        "cashAndCashEquivalents",
        "cashAndShortTermInvestments",
    ),
    "total_debt": (
        "total_debt",
        "totalDebt",
        "shortLongTermDebtTotal",
        "longTermDebt",
    ),
    "operating_cash_flow": (
        "operating_cash_flow",
        "totalCashFromOperatingActivities",
        "operatingCashFlow",
    ),
    "investing_cash_flow": (
        "investing_cash_flow",
        "totalCashflowsFromInvestingActivities",
        "investingCashFlow",
    ),
    "financing_cash_flow": (
        "financing_cash_flow",
        "totalCashFromFinancingActivities",
        "financingCashFlow",
    ),
    "capital_expenditures": (
        "capital_expenditures",
        "capitalExpenditures",
        "capitalExpenditure",
    ),
}

#: Labels that stay in ``extra_line_items`` (ratios, capital structure
#: market metrics) rather than becoming first-class contract fields —
#: ``FundamentalStatement`` deliberately excludes derived/market figures.
_EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "shares_outstanding": (
        "shares_outstanding",
        "sharesOutstanding",
        "ordinarySharesNumber",
    ),
    "market_capitalization": (
        "market_capitalization",
        "marketCap",
        "market_cap",
    ),
    "enterprise_value": ("enterprise_value", "enterpriseValue"),
    "current_ratio": ("current_ratio", "currentRatio"),
    "debt_to_equity": ("debt_to_equity", "debtToEquity"),
    "return_on_equity": ("return_on_equity", "returnOnEquity"),
    "return_on_assets": ("return_on_assets", "returnOnAssets"),
    "profit_margins": ("profit_margins", "profitMargins"),
    "operating_margins": ("operating_margins", "operatingMargins"),
    "gross_margins": ("gross_margins", "grossMargins"),
}

_PERIOD_TYPE_ALIASES: dict[str, StatementPeriodType] = {
    "annual": StatementPeriodType.ANNUAL,
    "yearly": StatementPeriodType.ANNUAL,
    "fy": StatementPeriodType.ANNUAL,
    "year": StatementPeriodType.ANNUAL,
    StatementPeriodType.ANNUAL.value: StatementPeriodType.ANNUAL,
    "quarterly": StatementPeriodType.QUARTERLY,
    "quarter": StatementPeriodType.QUARTERLY,
    "q": StatementPeriodType.QUARTERLY,
    StatementPeriodType.QUARTERLY.value: StatementPeriodType.QUARTERLY,
    "ttm": StatementPeriodType.TRAILING_TWELVE_MONTHS,
    "trailing": StatementPeriodType.TRAILING_TWELVE_MONTHS,
    "trailing_twelve_months": StatementPeriodType.TRAILING_TWELVE_MONTHS,
    StatementPeriodType.TRAILING_TWELVE_MONTHS.value: (
        StatementPeriodType.TRAILING_TWELVE_MONTHS
    ),
}


def _coerce_bar(raw: RawMarketBar) -> NormalizedBar:
    """Coerce one ``RawMarketBar``'s loosely-typed fields into strict types."""
    return NormalizedBar(
        timestamp=coerce_timestamp(raw.timestamp, provider_id=raw.provider_id),
        open=coerce_float(raw.open, provider_id=raw.provider_id, field_name="open"),
        high=coerce_float(raw.high, provider_id=raw.provider_id, field_name="high"),
        low=coerce_float(raw.low, provider_id=raw.provider_id, field_name="low"),
        close=coerce_float(raw.close, provider_id=raw.provider_id, field_name="close"),
        volume=coerce_float(
            raw.volume,
            provider_id=raw.provider_id,
            field_name="volume",
            required=False,
        ),
        adjusted_close=(
            None
            if raw.adjusted_close is None
            else coerce_float(
                raw.adjusted_close,
                provider_id=raw.provider_id,
                field_name="adjusted_close",
                required=False,
            )
        ),
    )


def _construct_bar(normalized: NormalizedBar) -> PriceBar:
    """Construct a validated ``PriceBar`` from a ``NormalizedBar``."""
    return PriceBar(
        timestamp=normalized.timestamp,
        open=normalized.open,
        high=normalized.high,
        low=normalized.low,
        close=normalized.close,
        volume=normalized.volume,
        adjusted_close=normalized.adjusted_close,
    )


class DefaultMarketDataNormalizer(MarketDataNormalizer):
    """Generic, provider-agnostic ``MarketDataNormalizer``.

    Built entirely on :class:`TransformationPipeline`: raw bars are
    coerced, checked by a raw-level validation pipeline (required
    fields, sentinel values), checked again by a normalized-level
    validation pipeline (timestamp integrity, duplicates, ordering,
    OHLC consistency, volume), then constructed into ``PriceBar``
    instances and assembled into a ``PriceSeries``.

    A provider adapter never needs to subclass or reimplement this
    normalizer — it only needs to populate ``RawMarketBar`` and
    ``RawMarketSeries`` correctly and pass them here.
    """

    def __init__(self, *, frequency: BarFrequency) -> None:
        """Initialize the normalizer.

        Args:
            frequency: The sampling frequency to stamp onto the
                constructed ``PriceSeries``. Raw models carry no
                frequency of their own, since a provider's raw bars
                do not self-describe their sampling frequency.
        """
        self._frequency = frequency
        self._pipeline = (
            TransformationPipeline[RawMarketBar, NormalizedBar, PriceBar](
                coerce=_coerce_bar,
                construct=_construct_bar,
                raw_validation=ValidationPipeline(
                    [
                        RequiredFieldValidationStage(
                            field_names=("timestamp", "open", "high", "low", "close")
                        ),
                        MissingValueValidationStage(
                            field_names=("open", "high", "low", "close")
                        ),
                    ]
                ),
                normalized_validation=ValidationPipeline(
                    [
                        TimestampValidationStage(),
                        DuplicateDetectionStage(key=lambda bar: bar.timestamp),
                        SortingVerificationStage(key=lambda bar: bar.timestamp),
                        OHLCConsistencyStage(),
                        VolumeValidationStage(),
                    ]
                ),
            )
        )

    def normalize(self, raw: RawMarketSeries, instrument: Instrument) -> PriceSeries:
        """Normalize a raw market series into a validated ``PriceSeries``.

        Args:
            raw: The raw, unvalidated price series to normalize.
            instrument: The already-resolved instrument the series
                belongs to.

        Returns:
            A validated ``PriceSeries``.

        Raises:
            data_engine.exceptions.NormalizationError: If any raw bar
                is malformed.
            data_engine.exceptions.TransformationError: If the pipeline
                fails for a reason other than a data-quality issue
                already covered by the configured validation stages.
        """
        bars = self._pipeline.run(raw.bars)
        return PriceSeries(instrument=instrument, frequency=self._frequency, bars=bars)


def _lookup_line_item(
    line_items: dict[str, Any], aliases: tuple[str, ...]
) -> Any:
    """Return the first present raw value among ``aliases``, else ``None``."""
    for alias in aliases:
        if alias in line_items and line_items[alias] is not None:
            return line_items[alias]
    return None


def _coerce_period_type(
    value: Any, *, provider_id: str
) -> StatementPeriodType:
    """Map a raw period-type label onto ``StatementPeriodType``."""
    if isinstance(value, StatementPeriodType):
        return value
    if value is None:
        msg = f"provider '{provider_id}' is missing required field 'period_type'"
        raise MissingFieldError(msg)
    key = str(value).strip().lower()
    mapped = _PERIOD_TYPE_ALIASES.get(key)
    if mapped is None:
        msg = (
            f"provider '{provider_id}' returned an unsupported "
            f"period_type: {value!r}"
        )
        raise InvalidProviderDataError(msg)
    return mapped


def _coerce_statement(
    raw: RawFundamentalData, instrument: Instrument
) -> NormalizedStatement:
    """Coerce one ``RawFundamentalData`` into a ``NormalizedStatement``."""
    period_end = coerce_date(
        raw.period_end, provider_id=raw.provider_id, field_name="period_end"
    )
    period_type = _coerce_period_type(raw.period_type, provider_id=raw.provider_id)

    raw_items = dict(raw.line_items)
    fiscal_year_raw = raw_items.pop("fiscal_year", None)
    if fiscal_year_raw is None:
        fiscal_year_raw = raw_items.pop("fiscalYear", None)
    if fiscal_year_raw is None:
        fiscal_year = period_end.year
    else:
        try:
            fiscal_year = int(fiscal_year_raw)
        except (TypeError, ValueError) as exc:
            msg = (
                f"provider '{raw.provider_id}' returned a non-integer "
                f"fiscal_year: {fiscal_year_raw!r}"
            )
            raise InvalidProviderDataError(msg) from exc

    currency_raw = raw_items.pop("currency", None)
    currency = (
        str(currency_raw).strip().upper()
        if currency_raw is not None and str(currency_raw).strip()
        else instrument.currency.strip().upper()
    )

    line_items: dict[str, float | None] = {}
    consumed: set[str] = set()
    for field_name in _STATEMENT_FIELDS:
        aliases = _FIELD_ALIASES[field_name]
        raw_value = _lookup_line_item(raw_items, aliases)
        for alias in aliases:
            if alias in raw_items:
                consumed.add(alias)
        line_items[field_name] = coerce_optional_float(
            raw_value, provider_id=raw.provider_id, field_name=field_name
        )

    extras: list[tuple[str, float]] = []
    for canonical, aliases in _EXTRA_ALIASES.items():
        raw_value = _lookup_line_item(raw_items, aliases)
        for alias in aliases:
            if alias in raw_items:
                consumed.add(alias)
        coerced = coerce_optional_float(
            raw_value, provider_id=raw.provider_id, field_name=canonical
        )
        if coerced is not None:
            extras.append((canonical, coerced))

    for key, value in raw_items.items():
        if key in consumed or key in {"fiscal_year", "fiscalYear", "currency"}:
            continue
        coerced = coerce_optional_float(
            value, provider_id=raw.provider_id, field_name=key
        )
        if coerced is not None:
            extras.append((str(key), coerced))

    return NormalizedStatement(
        period_end=period_end,
        period_type=period_type,
        fiscal_year=fiscal_year,
        currency=currency,
        line_items=line_items,
        extra_line_items=tuple(extras),
    )


def _construct_statement(
    normalized: NormalizedStatement, instrument: Instrument
) -> FundamentalStatement:
    """Construct a validated ``FundamentalStatement`` from a normalized record."""
    try:
        return FundamentalStatement(
            instrument=instrument,
            period_end=normalized.period_end,
            period_type=normalized.period_type,
            fiscal_year=normalized.fiscal_year,
            currency=normalized.currency,
            revenue=normalized.line_items["revenue"],
            cost_of_revenue=normalized.line_items["cost_of_revenue"],
            gross_profit=normalized.line_items["gross_profit"],
            operating_income=normalized.line_items["operating_income"],
            net_income=normalized.line_items["net_income"],
            eps_basic=normalized.line_items["eps_basic"],
            eps_diluted=normalized.line_items["eps_diluted"],
            total_assets=normalized.line_items["total_assets"],
            total_liabilities=normalized.line_items["total_liabilities"],
            total_equity=normalized.line_items["total_equity"],
            cash_and_equivalents=normalized.line_items["cash_and_equivalents"],
            total_debt=normalized.line_items["total_debt"],
            operating_cash_flow=normalized.line_items["operating_cash_flow"],
            investing_cash_flow=normalized.line_items["investing_cash_flow"],
            financing_cash_flow=normalized.line_items["financing_cash_flow"],
            capital_expenditures=normalized.line_items["capital_expenditures"],
            extra_line_items=normalized.extra_line_items,
        )
    except ContractValidationError as exc:
        msg = f"constructed FundamentalStatement failed contracts validation: {exc}"
        raise InvalidProviderDataError(msg) from exc


class DefaultFundamentalNormalizer(FundamentalNormalizer):
    """Generic, provider-agnostic ``FundamentalNormalizer``.

    Maps ``RawFundamentalData.line_items`` onto
    ``contracts.FundamentalStatement`` fields using a stable alias table,
    parks market/ratio metrics in ``extra_line_items``, and rejects
    malformed identity fields. Adapters only need to populate
    ``RawFundamentalData`` correctly.
    """

    def normalize(
        self, raw: RawFundamentalData, instrument: Instrument
    ) -> FundamentalStatement:
        """Normalize raw fundamental data into a validated statement.

        Args:
            raw: The raw, unvalidated financial statement to normalize.
            instrument: The already-resolved instrument the statement
                belongs to.

        Returns:
            A validated ``FundamentalStatement``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw`` cannot
                be converted into a valid ``FundamentalStatement``.
        """
        if not raw.provider_id.strip():
            msg = "provider_id must not be empty"
            raise InvalidProviderDataError(msg)

        RequiredFieldValidationStage(
            field_names=("provider_id", "period_end", "period_type")
        ).validate([raw])

        normalized = _coerce_statement(raw, instrument)
        return _construct_statement(normalized, instrument)


def _coerce_frequency(value: Any, *, provider_id: str) -> EconomicFrequency:
    """Map a raw frequency label onto ``EconomicFrequency``."""
    if isinstance(value, EconomicFrequency):
        return value
    if value is None:
        msg = f"provider '{provider_id}' is missing required field 'frequency'"
        raise MissingFieldError(msg)
    key = str(value).strip().lower()
    mapped = _FREQUENCY_ALIASES.get(key)
    if mapped is None:
        msg = (
            f"provider '{provider_id}' returned an unsupported "
            f"frequency: {value!r}"
        )
        raise InvalidProviderDataError(msg)
    return mapped


def _is_missing_observation_value(value: Any) -> bool:
    """Return whether a raw observation value is a known missing sentinel."""
    if value in _MISSING_VALUE_SENTINELS:
        return True
    if isinstance(value, str) and value.strip() in _MISSING_VALUE_SENTINELS:
        return True
    return False


class DefaultEconomicNormalizer(EconomicDataNormalizer):
    """Generic, provider-agnostic ``EconomicDataNormalizer``.

    Skips provider missing-value sentinels (e.g. FRED's ``"."``), coerces
    dates and numerics, sorts chronologically ascending, and constructs
    a validated ``contracts.EconomicSeries``. Adapters only need to
    populate ``RawEconomicSeries`` correctly.
    """

    def normalize(self, raw: RawEconomicSeries) -> EconomicSeries:
        """Normalize a raw economic series into a validated ``EconomicSeries``.

        Args:
            raw: The raw, unvalidated economic series to normalize.

        Returns:
            A validated ``EconomicSeries``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw`` cannot
                be converted into a valid ``EconomicSeries``.
        """
        if not raw.provider_id.strip():
            msg = "provider_id must not be empty"
            raise InvalidProviderDataError(msg)
        if raw.indicator_code is None or str(raw.indicator_code).strip() == "":
            msg = (
                f"provider '{raw.provider_id}' is missing required field "
                f"'indicator_code'"
            )
            raise MissingFieldError(msg)
        if raw.country is None or str(raw.country).strip() == "":
            msg = (
                f"provider '{raw.provider_id}' is missing required field 'country'"
            )
            raise MissingFieldError(msg)

        frequency = _coerce_frequency(raw.frequency, provider_id=raw.provider_id)
        indicator_code = str(raw.indicator_code).strip().upper()
        country = str(raw.country).strip().upper()
        indicator_name = (
            str(raw.indicator_name).strip()
            if raw.indicator_name is not None and str(raw.indicator_name).strip()
            else indicator_code
        )
        unit = (
            str(raw.unit).strip()
            if raw.unit is not None and str(raw.unit).strip()
            else None
        )

        observations: list[NormalizedObservation] = []
        for index, point in enumerate(raw.points):
            if not isinstance(point, RawEconomicDataPoint):
                msg = (
                    f"provider '{raw.provider_id}' returned a non-observation "
                    f"at index {index}"
                )
                raise InvalidProviderDataError(msg)
            if _is_missing_observation_value(point.value):
                # Provider "no observation for this date" — skip, don't fail.
                continue
            if point.observation_date is None:
                msg = (
                    f"provider '{raw.provider_id}' observation at index "
                    f"{index} is missing observation_date"
                )
                raise MissingFieldError(msg)
            try:
                observation_date = coerce_date(
                    point.observation_date,
                    provider_id=raw.provider_id,
                    field_name="observation_date",
                )
                value = coerce_float(
                    point.value,
                    provider_id=raw.provider_id,
                    field_name="value",
                )
            except (MissingFieldError, InvalidProviderDataError):
                raise
            observations.append(
                NormalizedObservation(observation_date=observation_date, value=value)
            )

        if not observations:
            msg = (
                f"provider '{raw.provider_id}' returned no usable observations "
                f"for '{indicator_code}'"
            )
            raise InvalidProviderDataError(msg)

        # Deduplicate by date (last write wins), then sort ascending.
        by_date: dict[Any, NormalizedObservation] = {
            item.observation_date: item for item in observations
        }
        ordered = tuple(
            sorted(by_date.values(), key=lambda item: item.observation_date)
        )

        DuplicateDetectionStage(key=lambda item: item.observation_date).validate(
            ordered
        )
        SortingVerificationStage(key=lambda item: item.observation_date).validate(
            ordered
        )

        points = tuple(
            EconomicDataPoint(
                observation_date=item.observation_date, value=item.value
            )
            for item in ordered
        )
        try:
            return EconomicSeries(
                indicator_code=indicator_code,
                indicator_name=indicator_name,
                country=country,
                frequency=frequency,
                points=points,
                unit=unit,
            )
        except ContractValidationError as exc:
            msg = f"constructed EconomicSeries failed contracts validation: {exc}"
            raise InvalidProviderDataError(msg) from exc

