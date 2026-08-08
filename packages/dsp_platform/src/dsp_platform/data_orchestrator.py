"""Unified authenticated data gateway façade for DSPPlatform (EPIC-D005).

Read-only aggregation of D001–D004 façades. No calculations or scoring.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from data_engine import (
    DataOrchestrator,
    DataOrchestratorRequest,
    UnifiedDataBundle,
)

__all__ = [
    "get_unified_data_bundle",
    "unified_data_health",
    "unified_data_metrics",
    "reset_data_orchestrator_for_tests",
]

_LOCK = Lock()
_ORCHESTRATOR: DataOrchestrator | None = None


def _build_orchestrator(request: DataOrchestratorRequest) -> DataOrchestrator:
    """Build orchestrator with closures bound to the current request."""
    from dsp_platform import corporate_actions as ca
    from dsp_platform import financial_statements as fs
    from dsp_platform import historical_series as hs
    from dsp_platform import market_quotes as mq

    symbol = request.symbol
    exchange = request.exchange
    currency = request.currency

    return DataOrchestrator(
        fetch_market_quote=lambda: mq.get_authenticated_market_quote(
            symbol, exchange=exchange, currency=currency
        ),
        fetch_financial_statements=lambda: fs.get_authenticated_financial_statements(
            symbol,
            exchange=exchange,
            currency=currency,
            period_type=request.statement_period_type,
            limit=request.statement_limit,
        ),
        fetch_corporate_actions=lambda: ca.get_authenticated_corporate_actions(
            symbol,
            exchange=exchange,
            currency=currency,
            limit=request.corporate_actions_limit,
        ),
        fetch_historical_series=lambda: hs.get_authenticated_historical_series(
            symbol,
            series_kind=request.historical_series_kind,
            exchange=exchange,
            currency=currency,
            frequency=request.historical_frequency,
            limit=request.historical_limit,
        ),
        health_market_quote=mq.market_quote_health,
        health_financial_statements=fs.financial_statement_health,
        health_corporate_actions=ca.corporate_actions_health,
        health_historical_series=hs.historical_series_health,
        resolve_company=lambda: fs.resolve_company_identity(
            symbol, exchange=exchange, currency=currency
        ),
    )


def reset_data_orchestrator_for_tests(
    orchestrator: DataOrchestrator | None = None,
) -> None:
    """Replace or clear process-local orchestrator (tests only)."""
    global _ORCHESTRATOR
    with _LOCK:
        _ORCHESTRATOR = orchestrator


def get_unified_data_bundle(
    symbol: str,
    *,
    exchange: str | None = None,
    currency: str = "USD",
    include_market_quote: bool = True,
    include_financial_statements: bool = True,
    include_corporate_actions: bool = True,
    include_historical_series: bool = True,
    historical_series_kind: str = "ohlcv",
    historical_frequency: str | None = "daily",
    historical_limit: int = 30,
    statement_period_type: str | None = None,
    statement_limit: int = 8,
    corporate_actions_limit: int = 50,
) -> dict[str, Any]:
    """Aggregate authenticated data sources into one canonical dict."""
    request = DataOrchestratorRequest(
        symbol=symbol.strip().upper(),
        exchange=exchange,
        currency=currency,
        include_market_quote=include_market_quote,
        include_financial_statements=include_financial_statements,
        include_corporate_actions=include_corporate_actions,
        include_historical_series=include_historical_series,
        historical_series_kind=historical_series_kind,
        historical_frequency=historical_frequency,
        historical_limit=historical_limit,
        statement_period_type=statement_period_type,
        statement_limit=statement_limit,
        corporate_actions_limit=corporate_actions_limit,
    )

    global _ORCHESTRATOR
    with _LOCK:
        # Tests may inject a fully built orchestrator (symbol-agnostic mocks).
        if _ORCHESTRATOR is not None:
            orch = _ORCHESTRATOR
        else:
            orch = _build_orchestrator(request)
            # Do not cache request-bound closures — rebuild per call.

    bundle: UnifiedDataBundle = orch.get_bundle(request)
    return bundle.to_public_dict()


def unified_data_health() -> dict[str, Any]:
    """Aggregate health across authenticated data providers."""
    request = DataOrchestratorRequest(symbol="HEALTH")
    global _ORCHESTRATOR
    with _LOCK:
        orch = _ORCHESTRATOR or _build_orchestrator(request)
        if _ORCHESTRATOR is None:
            _ORCHESTRATOR = orch
    return orch.health().to_dict()


def unified_data_metrics() -> dict[str, int]:
    with _LOCK:
        if _ORCHESTRATOR is None:
            return {
                "requests": 0,
                "sections_ok": 0,
                "sections_unavailable": 0,
                "sections_error": 0,
                "partial_responses": 0,
            }
        return _ORCHESTRATOR.metrics.snapshot()
