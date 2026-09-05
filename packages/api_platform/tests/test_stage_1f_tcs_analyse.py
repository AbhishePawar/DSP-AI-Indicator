"""Stage 1F — POST /api/v1/analyse with promoted TCS share-count snapshot.

Mocks only the Upstox/vendor HTTP boundary (in-memory quote + statements).
Does not mock ``_resolve_shares`` or the promoted share-count provider.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    ShareCountService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    StatementProviderHealth,
)
from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    DurablePromotedShareCountAdapter,
)
from dsp_platform.share_counts import reset_share_count_service_for_tests

TICKER = "TCS"
EXCHANGE = "NSE"
ISIN = "INE467B01029"
_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_PRICE = 3500.25
_EPS = Decimal("10")
_BODY = {
    "ticker": TICKER,
    "company": "Tata Consultancy Services",
    "exchange": EXCHANGE,
}


def _expected_shares() -> Decimal:
    payload = json.loads(
        (DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json").read_text(
            encoding="utf-8"
        )
    )
    return Decimal(str(payload["shares_outstanding"]))


def _seed_bundle():
    shares = _expected_shares()
    ni = float(shares * _EPS)
    return build_statements_from_mapping(
        symbol=TICKER,
        payload={
            "identity": {
                "symbol": TICKER,
                "exchange": EXCHANGE,
                "company_name": "Tata Consultancy Services",
                "currency": "INR",
                "isin": ISIN,
            },
            "reporting_currency": "INR",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2026,
                    "period_end": "2026-03-31",
                    "filing_date": "2026-04-15",
                    "reporting_currency": "INR",
                    "restated": False,
                    "income_statement": {
                        "revenue": ni * 5,
                        "net_income": ni,
                        "eps_basic": float(_EPS),
                        "operating_income": ni * 1.2,
                    },
                    "balance_sheet": {
                        "cash": ni,
                        "total_assets": ni * 15,
                        "total_liabilities": ni * 5,
                        "equity": ni * 10,
                        "total_debt": ni * 2,
                    },
                    "cash_flow": {
                        "operating_cash_flow": ni * 1.5,
                        "capex": -ni * 0.3,
                        "free_cash_flow": ni * 1.2,
                    },
                    "ratios": {},
                }
            ],
        },
        provenance=FinancialStatementProvenance(
            provider_id="memory_authenticated_statements",
            provider_name="Memory Statements",
            source_type="licensed_vendor",
            retrieved_at=_HORIZON,
            auth_mode="api_key",
        ),
    )


def _seed_quote():
    return build_quote_from_mapping(
        symbol=TICKER,
        payload={
            "exchange": EXCHANGE,
            "currency": "INR",
            "current_price": _PRICE,
            "previous_close": _PRICE,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=_HORIZON,
            auth_mode="api_key",
            metadata={"isin": ISIN, "exchange": EXCHANGE},
        ),
    )


class _ExchangeGatedStatementAdapter(FinancialStatementPort):
    def __init__(self) -> None:
        self._bundle = _seed_bundle()
        self.exchanges_seen: list[str | None] = []

    @property
    def provider_id(self) -> str:
        return "memory_authenticated_statements"

    def resolve_company(self, instrument):
        return self._bundle.identity if instrument.exchange == EXCHANGE else None

    def get_statements(self, query):
        self.exchanges_seen.append(query.instrument.exchange)
        if query.instrument.exchange != EXCHANGE:
            return None
        return self._bundle

    def health(self) -> StatementProviderHealth:
        return StatementProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail="test",
        )


def _install_services() -> _ExchangeGatedStatementAdapter:
    stmt = _ExchangeGatedStatementAdapter()
    quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    reset_share_count_service_for_tests(
        ShareCountService(
            DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        )
    )
    return stmt


def _client() -> TestClient:
    platform = (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )
    return TestClient(create_app(platform=platform))


def test_post_analyse_tcs_uses_promoted_snapshot_and_values() -> None:
    stmt = _install_services()
    try:
        response = _client().post("/api/v1/analyse", json=_BODY)
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("ok") is True
        errors = " ".join(payload.get("errors") or []).lower()
        assert "shares outstanding" not in errors
        assert "shares_outstanding_unavailable" not in errors
        inner = payload.get("payload") or {}
        server = inner.get("server_valuation") or {}
        assert server.get("authority") == "server"
        iv = server.get("intrinsic_value_per_share")
        assert isinstance(iv, (int, float)) and iv > 0
        assert server.get("current_market_price") == pytest.approx(_PRICE)
        assert EXCHANGE in stmt.exchanges_seen
        assert None not in stmt.exchanges_seen
        expected = float(_expected_shares())
        trace = inner.get("authenticated_valuation_trace") or {}
        if "shares_outstanding" in trace:
            assert trace["shares_outstanding"] == pytest.approx(expected)
    finally:
        reset_financial_statement_service_for_tests(None)
        reset_market_quote_service_for_tests(None)
        reset_share_count_service_for_tests(None)
