"""Concrete Yahoo Finance fundamentals adapter.

This is the platform's first real ``FundamentalsDataPort`` integration.
It is the only class that knows Yahoo Finance's quoteSummary modules,
field labels, and nested ``{raw, fmt}`` value shape. Everything
downstream (``DefaultFundamentalNormalizer``, ``FundamentalsDataService``,
the Fundamental Engine) only ever sees ``contracts.FundamentalStatement``.

Scope: annual and quarterly as-reported income / balance / cash-flow
statements plus optional key statistics (shares outstanding, market
capitalization, enterprise value, common ratios) parked in
``extra_line_items``. Trailing-twelve-month retrieval is supported via
Yahoo's ``financialData`` / ``defaultKeyStatistics`` modules as a
single synthetic statement when historical TTM series are unavailable.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import StatementPeriodType
from data_engine.adapters import BaseAdapter
from data_engine.adapters.yahoo_finance.http_client import (
    JsonHttpClient,
    UrllibJsonHttpClient,
)
from data_engine.exceptions import (
    DataEngineError,
    InvalidProviderDataError,
    TransformationError,
)
from data_engine.normalization import DefaultFundamentalNormalizer, FundamentalNormalizer
from data_engine.ports import FundamentalsDataPort
from data_engine.raw_models import RawFundamentalData

__all__ = ["YahooFinanceFundamentalsAdapter"]

_DEFAULT_BASE_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary"
_PROVIDER_ID = "yahoo_finance_fundamentals"

_ANNUAL_MODULES = (
    "incomeStatementHistory",
    "balanceSheetHistory",
    "cashflowStatementHistory",
    "defaultKeyStatistics",
    "financialData",
)
_QUARTERLY_MODULES = (
    "incomeStatementHistoryQuarterly",
    "balanceSheetHistoryQuarterly",
    "cashflowStatementHistoryQuarterly",
    "defaultKeyStatistics",
    "financialData",
)
_TTM_MODULES = ("defaultKeyStatistics", "financialData", "incomeStatementHistory")

#: Yahoo statement-object field → canonical / alias line-item key used by
#: ``DefaultFundamentalNormalizer``.
_STATEMENT_FIELD_MAP: Mapping[str, str] = {
    "totalRevenue": "totalRevenue",
    "costOfRevenue": "costOfRevenue",
    "grossProfit": "grossProfit",
    "operatingIncome": "operatingIncome",
    "netIncome": "netIncome",
    "basicEPS": "basicEPS",
    "dilutedEPS": "dilutedEPS",
    "totalAssets": "totalAssets",
    "totalLiab": "totalLiab",
    "totalLiabilitiesNetMinorityInterest": "totalLiabilities",
    "totalStockholderEquity": "totalStockholderEquity",
    "stockholdersEquity": "stockholdersEquity",
    "cash": "cash",
    "cashAndCashEquivalents": "cashAndCashEquivalents",
    "shortLongTermDebtTotal": "shortLongTermDebtTotal",
    "longTermDebt": "longTermDebt",
    "totalDebt": "totalDebt",
    "totalCashFromOperatingActivities": "totalCashFromOperatingActivities",
    "operatingCashFlow": "operatingCashFlow",
    "totalCashflowsFromInvestingActivities": "totalCashflowsFromInvestingActivities",
    "investingCashFlow": "investingCashFlow",
    "totalCashFromFinancingActivities": "totalCashFromFinancingActivities",
    "financingCashFlow": "financingCashFlow",
    "capitalExpenditures": "capitalExpenditures",
    "capitalExpenditure": "capitalExpenditure",
}

_KEY_STAT_MAP: Mapping[str, str] = {
    "sharesOutstanding": "sharesOutstanding",
    "enterpriseValue": "enterpriseValue",
    "currentRatio": "currentRatio",
    "debtToEquity": "debtToEquity",
    "returnOnEquity": "returnOnEquity",
    "returnOnAssets": "returnOnAssets",
    "profitMargins": "profitMargins",
    "operatingMargins": "operatingMargins",
    "grossMargins": "grossMargins",
    "marketCap": "marketCap",
    "totalRevenue": "totalRevenue",
    "totalCash": "cashAndCashEquivalents",
    "totalDebt": "totalDebt",
    "ebitda": "ebitda",
    "revenuePerShare": "revenuePerShare",
}


def _unwrap(value: Any) -> Any:
    """Unwrap Yahoo's ``{raw, fmt}`` objects; pass other values through."""
    if isinstance(value, Mapping) and "raw" in value:
        return value.get("raw")
    return value


def _period_end_key(end_date: Any) -> str | None:
    """Stable string key for grouping statements that share a period end."""
    raw = _unwrap(end_date)
    if raw is None:
        return None
    return str(raw)


class YahooFinanceFundamentalsAdapter(BaseAdapter, FundamentalsDataPort):
    """Retrieves as-reported financial statements from Yahoo Finance.

    Responsibilities, and nothing more:

    1. Build the Yahoo Finance quoteSummary request for a symbol and
       period type and fetch it via an injected :class:`JsonHttpClient`.
    2. Map income / balance / cash-flow rows (plus optional key stats)
       onto provider-neutral :class:`RawFundamentalData` instances.
    3. Hand each raw statement to a :class:`FundamentalNormalizer` and
       return the validated ``contracts.FundamentalStatement`` tuple,
       ordered most-recent-first.
    """

    def __init__(
        self,
        *,
        http_client: JsonHttpClient | None = None,
        normalizer: FundamentalNormalizer | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize the adapter.

        Args:
            http_client: The HTTP client to use. Defaults to
                :class:`UrllibJsonHttpClient`. Tests should inject a
                fake implementation instead of relying on this default.
            normalizer: The normalizer used to convert raw responses
                into ``contracts`` objects. Defaults to
                :class:`DefaultFundamentalNormalizer`.
            base_url: Base URL of the Yahoo Finance quoteSummary
                endpoint. Overridable for testing.
            timeout_seconds: Timeout passed to the default HTTP client.
                Ignored if ``http_client`` is provided explicitly.
        """
        self._http_client = http_client or UrllibJsonHttpClient(
            timeout_seconds=timeout_seconds
        )
        self._normalizer = normalizer or DefaultFundamentalNormalizer()
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        """Return the canonical id this adapter registers under."""
        return _PROVIDER_ID

    def get_fundamental_statements(
        self,
        instrument: Instrument,
        period_type: StatementPeriodType,
        *,
        limit: int | None = None,
    ) -> tuple[FundamentalStatement, ...]:
        """Retrieve financial statements for an instrument.

        Args:
            instrument: The instrument to retrieve statements for.
            period_type: Annual, quarterly, or trailing-twelve-month.
            limit: Optional maximum number of most-recent periods.
                ``None`` means no limit. Negative values are rejected.

        Returns:
            Financial statements ordered from most recent to oldest.

        Raises:
            DataEngineError: If ``limit`` is negative.
            ProviderRequestError: If the HTTP request fails.
            InvalidProviderDataError: If Yahoo's response is malformed
                or contains no usable statements.
            TransformationError: If normalization fails unexpectedly.
        """
        if limit is not None and limit < 0:
            msg = f"limit must be non-negative, got {limit}"
            raise DataEngineError(msg)

        payload = self._fetch_quote_summary(instrument.symbol, period_type)
        raw_statements = self._to_raw_statements(payload, instrument, period_type)

        if not raw_statements:
            msg = (
                f"yahoo_finance_fundamentals returned no usable statements "
                f"for '{instrument.symbol}' ({period_type.value})"
            )
            raise InvalidProviderDataError(msg)

        statements: list[FundamentalStatement] = []
        for raw in raw_statements:
            try:
                statements.append(self._normalizer.normalize(raw, instrument))
            except DataEngineError:
                raise
            except Exception as exc:
                msg = (
                    f"failed to normalize yahoo_finance_fundamentals data "
                    f"for '{instrument.symbol}': {exc}"
                )
                raise TransformationError(msg) from exc

        statements.sort(key=lambda item: item.period_end, reverse=True)
        if limit is not None:
            statements = statements[:limit]
        return tuple(statements)

    def _fetch_quote_summary(
        self, symbol: str, period_type: StatementPeriodType
    ) -> Mapping[str, Any]:
        """Fetch the raw quoteSummary JSON payload for ``symbol``."""
        modules = self._modules_for(period_type)
        params = {"modules": ",".join(modules)}
        try:
            return self._http_client.get_json(
                f"{self._base_url}/{symbol}", params=params
            )
        except DataEngineError:
            raise
        except Exception as exc:
            msg = f"yahoo_finance_fundamentals request failed for '{symbol}': {exc}"
            raise DataEngineError(msg) from exc

    @staticmethod
    def _modules_for(period_type: StatementPeriodType) -> tuple[str, ...]:
        if period_type is StatementPeriodType.ANNUAL:
            return _ANNUAL_MODULES
        if period_type is StatementPeriodType.QUARTERLY:
            return _QUARTERLY_MODULES
        if period_type is StatementPeriodType.TRAILING_TWELVE_MONTHS:
            return _TTM_MODULES
        msg = f"unsupported StatementPeriodType: {period_type!r}"
        raise DataEngineError(msg)

    def _to_raw_statements(
        self,
        payload: Mapping[str, Any],
        instrument: Instrument,
        period_type: StatementPeriodType,
    ) -> tuple[RawFundamentalData, ...]:
        """Map a quoteSummary payload onto provider-neutral raw statements."""
        quote_summary = (
            payload.get("quoteSummary") if isinstance(payload, Mapping) else None
        )
        if not isinstance(quote_summary, Mapping):
            msg = (
                f"yahoo_finance_fundamentals returned an unexpected payload "
                f"shape for '{instrument.symbol}'"
            )
            raise InvalidProviderDataError(msg)

        error = quote_summary.get("error")
        if error:
            msg = (
                f"yahoo_finance_fundamentals reported an error for "
                f"'{instrument.symbol}': {error}"
            )
            raise InvalidProviderDataError(msg)

        results = quote_summary.get("result") or []
        if not results:
            msg = (
                f"yahoo_finance_fundamentals returned no quoteSummary result "
                f"for '{instrument.symbol}'"
            )
            raise InvalidProviderDataError(msg)

        result = results[0]
        if not isinstance(result, Mapping):
            msg = (
                f"yahoo_finance_fundamentals returned a malformed result for "
                f"'{instrument.symbol}'"
            )
            raise InvalidProviderDataError(msg)

        if period_type is StatementPeriodType.TRAILING_TWELVE_MONTHS:
            ttm = self._build_ttm_raw(result, instrument)
            return (ttm,) if ttm is not None else ()

        by_period: dict[str, dict[str, Any]] = {}
        self._merge_history(
            by_period,
            self._history_rows(result, "incomeStatementHistory", "incomeStatementHistory"),
        )
        self._merge_history(
            by_period,
            self._history_rows(
                result, "incomeStatementHistoryQuarterly", "incomeStatementHistory"
            ),
        )
        self._merge_history(
            by_period,
            self._history_rows(result, "balanceSheetHistory", "balanceSheetStatements"),
        )
        self._merge_history(
            by_period,
            self._history_rows(
                result, "balanceSheetHistoryQuarterly", "balanceSheetStatements"
            ),
        )
        self._merge_history(
            by_period,
            self._history_rows(
                result, "cashflowStatementHistory", "cashflowStatements"
            ),
        )
        self._merge_history(
            by_period,
            self._history_rows(
                result, "cashflowStatementHistoryQuarterly", "cashflowStatements"
            ),
        )

        key_stats = self._flatten_module(result.get("defaultKeyStatistics"))
        financial_data = self._flatten_module(result.get("financialData"))
        shared_extras = {**key_stats, **financial_data}

        raw_list: list[RawFundamentalData] = []
        for period_key, line_items in by_period.items():
            enriched = dict(line_items)
            # Attach market / ratio metrics to the most recent period only
            # once we know ordering — for now attach to every period; the
            # normalizer parks them in extra_line_items without breaking
            # as-reported identity fields.
            enriched.update(shared_extras)
            raw_list.append(
                RawFundamentalData(
                    provider_id=_PROVIDER_ID,
                    symbol=instrument.symbol,
                    period_end=int(period_key)
                    if period_key.isdigit()
                    else period_key,
                    period_type=period_type,
                    line_items=enriched,
                )
            )
        return tuple(raw_list)

    @staticmethod
    def _history_rows(
        result: Mapping[str, Any], module_name: str, list_key: str
    ) -> Sequence[Mapping[str, Any]]:
        module = result.get(module_name)
        if not isinstance(module, Mapping):
            return ()
        rows = module.get(list_key) or ()
        if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
            return ()
        return tuple(row for row in rows if isinstance(row, Mapping))

    def _merge_history(
        self,
        by_period: MutableMapping[str, dict[str, Any]],
        rows: Sequence[Mapping[str, Any]],
    ) -> None:
        for row in rows:
            key = _period_end_key(row.get("endDate"))
            if key is None:
                continue
            bucket = by_period.setdefault(key, {})
            for yahoo_field, alias in _STATEMENT_FIELD_MAP.items():
                if yahoo_field not in row:
                    continue
                unwrapped = _unwrap(row.get(yahoo_field))
                if unwrapped is None:
                    continue
                # Prefer the first non-null value seen for a field; later
                # modules (e.g. cash flow after income) fill gaps only.
                if alias not in bucket or bucket[alias] is None:
                    bucket[alias] = unwrapped

    def _flatten_module(self, module: Any) -> dict[str, Any]:
        if not isinstance(module, Mapping):
            return {}
        flat: dict[str, Any] = {}
        for yahoo_field, alias in _KEY_STAT_MAP.items():
            if yahoo_field not in module:
                continue
            unwrapped = _unwrap(module.get(yahoo_field))
            if unwrapped is not None:
                flat[alias] = unwrapped
        return flat

    def _build_ttm_raw(
        self, result: Mapping[str, Any], instrument: Instrument
    ) -> RawFundamentalData | None:
        """Build a single TTM raw statement from current financial metrics."""
        financial_data = self._flatten_module(result.get("financialData"))
        key_stats = self._flatten_module(result.get("defaultKeyStatistics"))
        line_items = {**key_stats, **financial_data}
        if not line_items:
            return None

        # Prefer the most recent annual endDate as the TTM anchor when
        # available; otherwise leave period_end as a sentinel the
        # normalizer will reject unless we supply a value — use today
        # via the latest annual row's endDate if present.
        period_end: Any = None
        annual_rows = self._history_rows(
            result, "incomeStatementHistory", "incomeStatementHistory"
        )
        if annual_rows:
            period_end = _unwrap(annual_rows[0].get("endDate"))
        if period_end is None:
            return None

        return RawFundamentalData(
            provider_id=_PROVIDER_ID,
            symbol=instrument.symbol,
            period_end=period_end,
            period_type=StatementPeriodType.TRAILING_TWELVE_MONTHS,
            line_items=line_items,
        )
