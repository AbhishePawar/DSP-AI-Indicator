"""P1-01 — authenticated data → authoritative valuation inputs.

Builds a validated server-side bundle from authenticated quote + statement
providers, then maps it into ``fundamental.FinancialSnapshot`` for
``ValuationEngine``. No fabricated data. No client investment conclusions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
import math
from typing import Any

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, StatementPeriodType
from data_engine.connector_framework.production_profile import (
    assert_production_investment_connectors_configured,
    is_production_environment,
)
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    AuthenticatedStatementPeriod,
    StatementField,
)
from data_engine.financial_statement.service import (
    FinancialStatementService,
    StatementQuery,
)
from data_engine.market_quote.models import AuthenticatedMarketQuote, QuoteField
from data_engine.market_quote.service import MarketQuoteService
from data_engine import is_approved_source
from dsp_platform.composition.financial_integrity import (
    FinancialIntegrityError,
    assert_balance_sheet_integrity,
    assert_cash_flow_integrity,
    assert_duplicate_periods,
    assert_eps_share_integrity,
    assert_profitability_sanity,
    assert_share_count_integrity,
    assert_statement_basis,
    assert_unit_homogeneous,
    normalize_periods_to_actual,
)
from financial import (
    BalanceSheet,
    CashFlowStatement,
    CurrencyRef,
    FinancialPeriod,
    FinancialStatements,
    IncomeStatement,
    PeriodType,
    UnitScale,
)
from financial.metadata import StatementMetadata
from fundamental import FinancialSnapshot
from investment_recommendation import ValuationSignals
from valuation import MarketSnapshot, ValuationAssessment, ValuationConfidence

__all__ = [
    "AuthenticatedValuationBundle",
    "AuthenticatedValuationError",
    "ShareCountResearchEvidence",
    "DATA_UNAVAILABLE",
    "load_authenticated_valuation_bundle",
    "production_investment_connectors",
    "signals_from_assessment",
    "to_financial_statements",
]

DATA_UNAVAILABLE = "Data unavailable."

_PERIOD_TYPE_MAP = {
    "annual": StatementPeriodType.ANNUAL,
    "quarterly": StatementPeriodType.QUARTERLY,
    "ttm": StatementPeriodType.TRAILING_TWELVE_MONTHS,
}

_CONFIDENCE_FLOAT = {
    ValuationConfidence.HIGH: 0.85,
    ValuationConfidence.MEDIUM: 0.65,
    ValuationConfidence.LOW: 0.45,
    ValuationConfidence.INSUFFICIENT: 0.25,
}


class AuthenticatedValuationError(ValueError):
    """Authenticated valuation inputs missing, mismatched, or invalid."""

    def __init__(self, message: str = DATA_UNAVAILABLE) -> None:
        super().__init__(message if message else DATA_UNAVAILABLE)


@dataclass(frozen=True, slots=True)
class ShareCountResearchEvidence:
    """A share count returned by a research adapter, with auditable evidence."""

    ticker: str
    company_name: str
    metric: str
    shares_outstanding: float
    source_id: str
    source: str
    evidence_url: str
    as_of: str
    unit: str


ShareCountResearcher = Callable[
    [str, str | None, str | None], ShareCountResearchEvidence | None
]


def _normalise_research_company_name(value: str | None) -> str:
    """Normalise legal suffixes for exact company-identity checks."""
    raw = str(value or "").upper().replace("&", " AND ")
    tokens = raw.replace(".", " ").replace(",", " ").split()
    suffixes = {
        "LIMITED",
        "LTD",
        "PRIVATE",
        "PVT",
        "COMPANY",
        "CO",
        "INCORPORATED",
        "INC",
        "CORPORATION",
        "CORP",
    }
    while tokens and tokens[-1].strip().upper() in suffixes:
        tokens.pop()
    normalised_tokens = [
        "".join(char for char in token if char.isalnum()) for token in tokens
    ]
    return " ".join(normalised_tokens).strip()


def _resolve_researched_shares(
    ticker: str,
    company_name: str | None,
    exchange: str | None,
    researcher: ShareCountResearcher | None,
) -> tuple[float, dict[str, Any]]:
    """Use AI/web research only as a sourced fallback; reject ungrounded output."""
    if researcher is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (authenticated shares outstanding unavailable; "
            "share-count research adapter is not configured)"
        )
    try:
        evidence = researcher(ticker, company_name, exchange)
    except Exception as exc:  # noqa: BLE001 — research failure must degrade safely
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share-count research failed: {type(exc).__name__})"
        ) from exc
    if not isinstance(evidence, ShareCountResearchEvidence):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share-count research returned no validated evidence)"
        )
    if str(evidence.ticker or "").strip().upper() != ticker:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched share-count ticker mismatch)"
        )
    evidence_company = _normalise_research_company_name(evidence.company_name)
    requested_company = _normalise_research_company_name(company_name)
    if not evidence_company or (
        requested_company and evidence_company != requested_company
    ):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched share-count company identity mismatch)"
        )
    if str(evidence.metric or "").strip().lower() != "issued_equity_shares":
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched metric is not issued equity shares)"
        )
    shares = evidence.shares_outstanding
    if isinstance(shares, bool) or not isinstance(shares, (int, float)):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched share count is not numeric)"
        )
    if (
        not math.isfinite(float(shares))
        or float(shares) <= 0
        or not float(shares).is_integer()
    ):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched share count must be a positive integer)"
        )
    source_id = str(evidence.source_id or "").strip().upper()
    source = str(evidence.source or "").strip()
    url = str(evidence.evidence_url or "").strip()
    if not is_approved_source(source_id, purpose="verification"):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (unapproved share-count evidence source)"
        )
    unit = str(evidence.unit or "").strip().lower()
    if unit not in {"share", "shares"}:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (researched share-count unit must be shares)"
        )
    as_of_raw = str(evidence.as_of or "").strip()
    try:
        as_of_date = date.fromisoformat(as_of_raw)
    except ValueError as exc:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share-count evidence date missing or invalid)"
        ) from exc
    if as_of_date > date.today():
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share-count evidence date is in the future)"
        )
    if not source or not url.startswith("https://"):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (share-count evidence source or HTTPS URL missing)"
        )
    return float(shares), {
        "provider_id": "ai_research_fallback",
        "ticker": ticker,
        "company_name": str(evidence.company_name).strip(),
        "metric": "issued_equity_shares",
        "shares_outstanding": float(shares),
        "source_id": source_id,
        "source": source,
        "evidence_url": url,
        "as_of": as_of_date.isoformat(),
        "unit": "shares",
        "evidence_class": "public_research_unverified_for_g2",
    }


@dataclass(frozen=True, slots=True)
class AuthenticatedValuationBundle:
    """Server-authoritative inputs for ValuationEngine (P1-01 / P1-02)."""

    ticker: str
    financial_snapshot: FinancialSnapshot
    market_snapshot: MarketSnapshot
    current_market_price: float
    shares_outstanding: float
    reporting_currency: str
    statement_provenance: dict[str, Any]
    quote_provenance: dict[str, Any]
    period_kind: str
    statement_basis: str
    unit_scale: str
    company_name: str | None = None

    def to_trace_dict(self) -> dict[str, Any]:
        latest = self.financial_snapshot.latest
        return {
            "ticker": self.ticker,
            "reporting_currency": self.reporting_currency,
            "period_kind": self.period_kind,
            "statement_basis": self.statement_basis,
            "unit_scale": self.unit_scale,
            "current_market_price": self.current_market_price,
            "shares_outstanding": self.shares_outstanding,
            "market_cap": self.market_snapshot.market_cap,
            "company_name": self.company_name,
            "revenue": latest.revenue,
            "operating_income": latest.operating_income,
            "net_income": latest.net_income,
            "operating_cash_flow": latest.operating_cash_flow,
            "capital_expenditures": latest.capital_expenditures,
            "total_equity": latest.total_equity,
            "total_debt": latest.total_debt,
            "cash_and_equivalents": latest.cash_and_equivalents,
            "statement_provenance": dict(self.statement_provenance),
            "quote_provenance": dict(self.quote_provenance),
            "authenticated": True,
        }


def _sf(field: StatementField) -> float | None:
    if not field.available or field.value is None:
        return None
    return float(field.value)


def _qf(field: QuoteField) -> float | None:
    if not field.available or field.value is None:
        return None
    return float(field.value)


def _reject_null_provider(provider_id: str, *, connector: str) -> None:
    pid = str(provider_id or "").strip().lower()
    if not pid or pid.startswith("null") or pid == "null":
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} ({connector} provider is null/unavailable)"
        )
    if any(tok in pid for tok in ("demo", "sample", "seed", "fake", "fixture")):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} ({connector} provider is demo/fake)"
        )


def _select_homogeneous_periods(
    periods: tuple[AuthenticatedStatementPeriod, ...],
) -> tuple[AuthenticatedStatementPeriod, ...]:
    if not periods:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (no financial statement periods)"
        )
    ordered = sorted(periods, key=lambda p: (p.period_end, p.fiscal_year), reverse=True)
    # Annual / TTM only — quarterly cash flows must not enter annual-style DCF.
    for kind in ("annual", "ttm"):
        selected = tuple(p for p in ordered if p.period_type == kind)
        if selected:
            return selected
    quarterly = tuple(p for p in ordered if p.period_type == "quarterly")
    if quarterly:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} "
            "(annual/TTM statements required; quarterly-only refused for valuation)"
        )
    raise AuthenticatedValuationError(
        f"{DATA_UNAVAILABLE} (unsupported statement period types)"
    )


def _validate_currency_set(
    periods: tuple[AuthenticatedStatementPeriod, ...],
    quote_currency: str | None,
) -> str:
    currencies = {
        (p.reporting_currency or "").strip().upper()
        for p in periods
        if (p.reporting_currency or "").strip()
    }
    if not currencies:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (statement currency missing)"
        )
    if len(currencies) > 1:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (mixed statement currencies)"
        )
    reporting = next(iter(currencies))
    if len(reporting) != 3:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (invalid statement currency)"
        )
    if quote_currency:
        q = quote_currency.strip().upper()
        if q and q != reporting:
            raise AuthenticatedValuationError(
                f"{DATA_UNAVAILABLE} (quote/statement currency mismatch)"
            )
    return reporting


def _resolve_shares(
    quote: AuthenticatedMarketQuote,
    latest: AuthenticatedStatementPeriod,
) -> float:
    """Require authenticated quote shares — never invent from NI/EPS."""
    _ = latest  # EPS integrity checked separately against quote shares
    shares = _qf(quote.shares_outstanding)
    if shares is not None and shares > 0:
        return float(shares)
    raise AuthenticatedValuationError(
        f"{DATA_UNAVAILABLE} (authenticated shares outstanding unavailable)"
    )


def _resolve_price(quote: AuthenticatedMarketQuote) -> float:
    price = _qf(quote.current_price)
    if price is None:
        price = _qf(quote.previous_close)
    if price is None or price <= 0:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (authenticated market price unavailable)"
        )
    return float(price)


def _to_fundamental_statement(
    period: AuthenticatedStatementPeriod,
    instrument: Instrument,
) -> FundamentalStatement:
    period_type = _PERIOD_TYPE_MAP.get(period.period_type)
    if period_type is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (invalid period type {period.period_type!r})"
        )
    if period.fiscal_year < 1900 or period.fiscal_year > 2200:
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (invalid fiscal period)")
    if not isinstance(period.period_end, date):
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (invalid period_end)")
    extras: list[tuple[str, float]] = []
    for name in ("ebit", "ebitda", "free_cash_flow", "long_term_debt"):
        value = _sf(getattr(period, name))
        if value is not None:
            extras.append((name, value))
    # Valuation methods treat capex as a non-negative outflow magnitude.
    capex = _sf(period.capital_expenditures)
    if capex is not None:
        capex = abs(capex)
    return FundamentalStatement(
        instrument=instrument,
        period_end=period.period_end,
        period_type=period_type,
        fiscal_year=int(period.fiscal_year),
        currency=period.reporting_currency.strip().upper(),
        revenue=_sf(period.revenue),
        cost_of_revenue=_sf(period.cost_of_revenue),
        gross_profit=_sf(period.gross_profit),
        operating_income=_sf(period.operating_income) or _sf(period.ebit),
        net_income=_sf(period.net_income),
        eps_basic=_sf(period.eps_basic),
        eps_diluted=_sf(period.eps_diluted),
        total_assets=_sf(period.total_assets),
        total_liabilities=_sf(period.total_liabilities),
        total_equity=_sf(period.total_equity),
        cash_and_equivalents=_sf(period.cash_and_equivalents),
        total_debt=_sf(period.total_debt),
        operating_cash_flow=_sf(period.operating_cash_flow),
        investing_cash_flow=_sf(period.investing_cash_flow),
        financing_cash_flow=_sf(period.financing_cash_flow),
        capital_expenditures=capex,
        extra_line_items=tuple(extras),
    )


def to_financial_statements(
    bundle: AuthenticatedValuationBundle,
) -> FinancialStatements:
    """Map the latest authenticated period into ``financial.FinancialStatements``."""
    latest = bundle.financial_snapshot.latest
    try:
        period_type = PeriodType(bundle.period_kind)
    except ValueError as exc:
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (period kind)") from exc
    currency = CurrencyRef.parse(latest.currency)
    shares = bundle.shares_outstanding
    fcf = None
    if (
        latest.operating_cash_flow is not None
        and latest.capital_expenditures is not None
    ):
        fcf = latest.operating_cash_flow - abs(latest.capital_expenditures)
    return FinancialStatements(
        period=FinancialPeriod(
            period_type=period_type,
            period_end=latest.period_end,
            fiscal_year=latest.fiscal_year,
            currency=currency,
            source="authenticated_provider",
        ),
        income_statement=IncomeStatement(
            revenue=latest.revenue,
            cogs=latest.cost_of_revenue,
            gross_profit=latest.gross_profit,
            ebit=latest.operating_income,
            net_income=latest.net_income,
            eps=latest.eps_basic,
            diluted_eps=latest.eps_diluted,
            weighted_shares=shares,
        ),
        balance_sheet=BalanceSheet(
            cash=latest.cash_and_equivalents,
            total_assets=latest.total_assets,
            total_liabilities=latest.total_liabilities,
            equity=latest.total_equity,
            total_equity=latest.total_equity,
            long_term_debt=latest.total_debt,
        ),
        cash_flow=CashFlowStatement(
            operating_cash_flow=latest.operating_cash_flow,
            investing_cash_flow=latest.investing_cash_flow,
            financing_cash_flow=latest.financing_cash_flow,
            capex=(
                -abs(latest.capital_expenditures)
                if latest.capital_expenditures is not None
                else None
            ),
            free_cash_flow=fcf,
        ),
        statement_metadata=StatementMetadata(unit_scale=UnitScale.ACTUAL),
    )


def signals_from_assessment(
    assessment: ValuationAssessment,
    *,
    current_market_price: float,
    shares_outstanding: float,
) -> ValuationSignals:
    """Build share-level ValuationSignals from company-level assessment."""
    mid = getattr(getattr(assessment, "valuation_range", None), "mid", None)
    if mid is None:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (intrinsic value could not be calculated)"
        )
    if shares_outstanding <= 0:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (shares outstanding unavailable)"
        )
    iv_per_share = float(mid) / float(shares_outstanding)
    conf = getattr(assessment, "confidence", ValuationConfidence.LOW)
    conf_f = _CONFIDENCE_FLOAT.get(conf, 0.55)
    return ValuationSignals(
        intrinsic_value_per_share=iv_per_share,
        current_market_price=float(current_market_price),
        confidence=conf_f,
    )


def load_authenticated_valuation_bundle(
    ticker: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    statement_service: FinancialStatementService | None = None,
    quote_service: MarketQuoteService | None = None,
    get_statements: (
        Callable[[str], AuthenticatedFinancialStatements | None] | None
    ) = None,
    get_quote: Callable[[str], AuthenticatedMarketQuote | None] | None = None,
    research_missing_shares: ShareCountResearcher | None = None,
) -> AuthenticatedValuationBundle:
    """Fetch + validate authenticated statements and quote for ``ticker``.

    Raises:
        AuthenticatedValuationError: when data is missing, mismatched, or unsafe.
    """
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (ticker required)")

    statements = _fetch_statements(
        symbol,
        exchange=exchange,
        currency=currency,
        statement_service=statement_service,
        get_statements=get_statements,
    )
    quote = _fetch_quote(
        symbol,
        exchange=exchange,
        currency=currency,
        quote_service=quote_service,
        get_quote=get_quote,
    )

    _reject_null_provider(statements.provenance.provider_id, connector="statements")
    _reject_null_provider(quote.provenance.provider_id, connector="quote")

    identity_symbol = str(statements.identity.symbol or "").strip().upper()
    quote_symbol = str(quote.symbol or "").strip().upper()
    if identity_symbol != symbol:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (statement identity mismatch: "
            f"requested {symbol}, got {identity_symbol or 'unknown'})"
        )
    if quote_symbol != symbol:
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (quote identity mismatch: "
            f"requested {symbol}, got {quote_symbol or 'unknown'})"
        )

    selected = _select_homogeneous_periods(statements.periods)
    try:
        statement_basis = assert_statement_basis(selected)
        source_unit = assert_unit_homogeneous(selected)
        assert_duplicate_periods(selected)
        selected = normalize_periods_to_actual(selected, source_unit=source_unit)
        for period in selected:
            assert_profitability_sanity(period)
            assert_cash_flow_integrity(period)
            assert_balance_sheet_integrity(period)
    except FinancialIntegrityError as exc:
        raise AuthenticatedValuationError(str(exc)) from exc

    reporting_currency = _validate_currency_set(selected, quote.currency)
    price = _resolve_price(quote)

    quote_shares = _qf(quote.shares_outstanding)
    derived_shares = None
    latest_period = selected[0]
    net_income = _sf(latest_period.net_income)
    eps = _sf(latest_period.eps_basic) or _sf(latest_period.eps_diluted)
    if net_income is not None and eps is not None and eps != 0:
        derived_shares = float(abs(net_income / eps))
    try:
        assert_share_count_integrity(
            quote_shares=quote_shares,
            derived_shares=derived_shares,
        )
    except FinancialIntegrityError as exc:
        raise AuthenticatedValuationError(str(exc)) from exc

    shares_research_provenance: dict[str, Any] | None = None
    try:
        shares = _resolve_shares(quote, latest_period)
    except AuthenticatedValuationError:
        # Trigger the explicit research fallback only when the quote source
        # does not provide a usable share count. The fallback must be sourced
        # and identity-checked; it is not promoted to authenticated-provider
        # evidence and cannot clear G2 by itself.
        shares, shares_research_provenance = _resolve_researched_shares(
            symbol,
            statements.identity.company_name,
            exchange or statements.identity.exchange or quote.exchange,
            research_missing_shares,
        )
    try:
        assert_eps_share_integrity(latest_period, shares)
    except FinancialIntegrityError as exc:
        raise AuthenticatedValuationError(str(exc)) from exc

    market_cap = _qf(quote.market_cap)
    if market_cap is None or market_cap <= 0:
        market_cap = price * shares
    elif shares > 0:
        # Check market cap against the resolved count, including researched fallback.
        implied_shares = float(market_cap) / price
        try:
            assert_share_count_integrity(
                quote_shares=shares,
                derived_shares=implied_shares,
                tolerance=0.25,
            )
        except FinancialIntegrityError as exc:
            raise AuthenticatedValuationError(str(exc)) from exc

    instrument = Instrument(
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        currency=reporting_currency,
        exchange=exchange or statements.identity.exchange or quote.exchange,
    )
    fund_statements = tuple(
        _to_fundamental_statement(period, instrument) for period in selected
    )
    # Require at least one usable valuation input on the latest period.
    latest = fund_statements[0]
    if (
        latest.total_equity is None
        and latest.net_income is None
        and latest.operating_cash_flow is None
    ):
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (required statement fields missing)"
        )

    snapshot = FinancialSnapshot(instrument=instrument, statements=fund_statements)
    return AuthenticatedValuationBundle(
        ticker=symbol,
        financial_snapshot=snapshot,
        market_snapshot=MarketSnapshot(
            market_cap=float(market_cap),
            as_of=selected[0].period_end,
        ),
        current_market_price=price,
        shares_outstanding=shares,
        reporting_currency=reporting_currency,
        statement_provenance=statements.provenance.to_dict(),
        quote_provenance={
            **quote.provenance.to_dict(),
            **(
                {"shares_research_fallback": shares_research_provenance}
                if shares_research_provenance is not None
                else {}
            ),
        },
        period_kind=selected[0].period_type,
        statement_basis=statement_basis,
        unit_scale="actual",
        company_name=statements.identity.company_name,
    )


def _fetch_statements(
    symbol: str,
    *,
    exchange: str | None,
    currency: str,
    statement_service: FinancialStatementService | None,
    get_statements: Callable[[str], AuthenticatedFinancialStatements | None] | None,
) -> AuthenticatedFinancialStatements:
    if get_statements is not None:
        bundle = get_statements(symbol)
    else:
        service = statement_service
        if service is None:
            from dsp_platform.financial_statements import _service

            service = _service()
        health = service.health()
        if not health.authenticated:
            raise AuthenticatedValuationError(
                f"{DATA_UNAVAILABLE} (statement provider unauthenticated)"
            )
        _reject_null_provider(health.provider_id, connector="statements")
        instrument = Instrument(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            currency=currency,
            exchange=exchange,
        )
        bundle = service.get_statements(
            StatementQuery(instrument=instrument, limit=8, include_restated=False)
        )
    if bundle is None:
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (financial statements)")
    if not bundle.has_any_period():
        raise AuthenticatedValuationError(
            f"{DATA_UNAVAILABLE} (financial statements empty)"
        )
    return bundle


def _fetch_quote(
    symbol: str,
    *,
    exchange: str | None,
    currency: str,
    quote_service: MarketQuoteService | None,
    get_quote: Callable[[str], AuthenticatedMarketQuote | None] | None,
) -> AuthenticatedMarketQuote:
    if get_quote is not None:
        quote = get_quote(symbol)
    else:
        service = quote_service
        if service is None:
            from dsp_platform.market_quotes import _service

            service = _service()
        health = service.health()
        if not health.authenticated:
            raise AuthenticatedValuationError(
                f"{DATA_UNAVAILABLE} (quote provider unauthenticated)"
            )
        _reject_null_provider(health.provider_id, connector="quote")
        instrument = Instrument(
            symbol=symbol,
            asset_class=AssetClass.EQUITY,
            currency=currency,
            exchange=exchange,
        )
        quote = service.get_quote(instrument)
    if quote is None:
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (market quote)")
    if not quote.has_any_price():
        raise AuthenticatedValuationError(f"{DATA_UNAVAILABLE} (market price)")
    return quote


def production_requires_authenticated_bundle() -> bool:
    """True when missing authenticated valuation inputs must fail closed."""
    return is_production_environment()


def production_investment_connectors() -> dict[str, str]:
    """Adapter class names the P1-03 production gate selects for this bundle.

    Empty outside production. Constructed offline — no provider I/O — so
    readiness probes can assert the authenticated quote/statement connectors
    without contacting external providers. Raises when production would select an unsafe
    (Null/memory/demo) adapter.
    """
    return assert_production_investment_connectors_configured()
