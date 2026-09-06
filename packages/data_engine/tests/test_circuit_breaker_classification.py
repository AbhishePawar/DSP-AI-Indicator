"""Circuit-breaker failure classification — provider vs domain validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from data_engine import (
    CircuitBreaker,
    CircuitOpenError,
    DataValidationError,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    InvalidProviderDataError,
    MarketQuoteService,
    ProviderRequestError,
    RetryPolicy,
    ShareCountBasis,
    ShareCountField,
    ShareCountProvenance,
    ShareCountProviderHealth,
    ShareCountService,
    ShareCountSnapshot,
    ShareCountUnit,
    StatementQuery,
    UnsupportedInstrumentError,
    is_provider_circuit_failure,
)
from data_engine.financial_statement.models import CompanyIdentity


SHARES_OUTSTANDING_STALE = "SHARES_OUTSTANDING_STALE"
SHARES_OUTSTANDING_IDENTITY_MISMATCH = "SHARES_OUTSTANDING_IDENTITY_MISMATCH"


class _ShareCountValidationError(DataValidationError):
    """Stand-in for dsp_platform.ShareCountResolutionError (typed, not message-matched)."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail or "")
        message = self.code if not self.detail else f"{self.code}: {self.detail}"
        super().__init__(message)

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
_NO_RETRY = RetryPolicy(max_attempts=1, backoff_seconds=0.0)


def _instrument(symbol: str = "TCS") -> Instrument:
    return Instrument(symbol=symbol, asset_class=AssetClass.EQUITY, currency="INR")


def _health(*, provider_id: str) -> ShareCountProviderHealth:
    return ShareCountProviderHealth(
        provider_id=provider_id,
        healthy=True,
        authenticated=True,
        detail="test",
    )


class _ShareCountErrorAdapter:
    def __init__(self, error: BaseException) -> None:
        self._error = error
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return "test_share_count"

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        self.calls += 1
        _ = instrument
        raise self._error

    def health(self) -> ShareCountProviderHealth:
        return _health(provider_id=self.provider_id)


class _ShareCountSnapshotAdapter:
    def __init__(self, snapshot: ShareCountSnapshot) -> None:
        self._snapshot = snapshot
        self.calls = 0

    @property
    def provider_id(self) -> str:
        return "test_share_count"

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        self.calls += 1
        _ = instrument
        return self._snapshot

    def health(self) -> ShareCountProviderHealth:
        return _health(provider_id=self.provider_id)


def _share_service(adapter, *, threshold: int = 5) -> ShareCountService:
    return ShareCountService(
        adapter,
        circuit_breaker=CircuitBreaker(name="share count", failure_threshold=threshold),
        retry=_NO_RETRY,
    )


def _quote_boom_service(exc: BaseException, *, threshold: int = 5) -> MarketQuoteService:
    class Boom(InMemoryAuthenticatedQuoteAdapter):
        def get_quote(self, instrument: Instrument):  # type: ignore[override]
            _ = instrument
            raise exc

    return MarketQuoteService(
        Boom(api_key="x"),
        circuit_breaker=CircuitBreaker(name="market quote", failure_threshold=threshold),
        retry=_NO_RETRY,
    )


def _statement_boom_service(exc: BaseException, *, threshold: int = 5) -> FinancialStatementService:
    class Boom(InMemoryAuthenticatedStatementAdapter):
        def get_statements(self, query):  # type: ignore[override]
            _ = query
            raise exc

        def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
            _ = instrument
            return None

    return FinancialStatementService(
        Boom(api_key="x"),
        circuit_breaker=CircuitBreaker(
            name="financial statements", failure_threshold=threshold
        ),
        retry=_NO_RETRY,
    )


def _invalid_snapshot() -> ShareCountSnapshot:
    return ShareCountSnapshot(
        symbol="",
        shares=ShareCountField.of(100),
        basis=ShareCountBasis.CURRENT_OUTSTANDING,
        unit=ShareCountUnit.SHARES,
        provenance=ShareCountProvenance(
            provider_id="memory_authenticated_share_count",
            provider_name="TEST-ONLY snapshot integrity fixture",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
        ),
    )


class TestFailureTaxonomy:
    def test_timeout_counts_breaker_failure(self) -> None:
        service = _share_service(_ShareCountErrorAdapter(TimeoutError("timed out")))
        with pytest.raises(TimeoutError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 1
        assert service._breaker.is_open is False

    def test_http_503_counts_breaker_failure(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(ProviderRequestError("HTTP 503 unavailable"))
        )
        with pytest.raises(ProviderRequestError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 1

    def test_http_429_counts_breaker_failure(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(ProviderRequestError("HTTP 429 rate limited"))
        )
        with pytest.raises(ProviderRequestError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 1

    def test_http_500_and_502_count_breaker_failure(self) -> None:
        for status in (500, 502):
            service = _share_service(
                _ShareCountErrorAdapter(ProviderRequestError(f"HTTP {status}"))
            )
            with pytest.raises(ProviderRequestError):
                service.get_share_count(_instrument())
            assert service._breaker.failure_count == 1

    def test_network_failure_counts_breaker_failure(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(ConnectionError("connection reset"))
        )
        with pytest.raises(ConnectionError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 1

    def test_shares_outstanding_stale_does_not_count(self) -> None:
        adapter = _ShareCountErrorAdapter(
            _ShareCountValidationError(
                SHARES_OUTSTANDING_STALE,
                "corporate-action coverage does not reach retrieved_at",
            )
        )
        service = _share_service(adapter)
        with pytest.raises(_ShareCountValidationError) as caught:
            service.get_share_count(_instrument())
        assert caught.value.code == SHARES_OUTSTANDING_STALE
        assert service._breaker.failure_count == 0
        assert service._breaker.is_open is False
        assert adapter.calls == 1

    def test_identity_mismatch_does_not_count(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(
                _ShareCountValidationError(
                    SHARES_OUTSTANDING_IDENTITY_MISMATCH,
                    "requested NYSE, snapshot NSE",
                )
            )
        )
        with pytest.raises(_ShareCountValidationError) as caught:
            service.get_share_count(_instrument())
        assert caught.value.code == SHARES_OUTSTANDING_IDENTITY_MISMATCH
        assert service._breaker.failure_count == 0
        assert service._breaker.is_open is False

    def test_snapshot_integrity_failure_does_not_count(self) -> None:
        service = _share_service(_ShareCountSnapshotAdapter(_invalid_snapshot()))
        with pytest.raises(InvalidProviderDataError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 0
        assert service._breaker.is_open is False
        assert service.metrics.rejected_invalid == 1

    def test_unsupported_instrument_does_not_count(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(UnsupportedInstrumentError("unsupported instrument"))
        )
        with pytest.raises(UnsupportedInstrumentError):
            service.get_share_count(_instrument())
        assert service._breaker.failure_count == 0
        assert service._breaker.is_open is False


class TestClassificationIsTyped:
    def test_does_not_use_message_matching(self) -> None:
        assert is_provider_circuit_failure(ProviderRequestError("SHARES_OUTSTANDING_STALE"))
        assert not is_provider_circuit_failure(
            _ShareCountValidationError(SHARES_OUTSTANDING_STALE, "x")
        )
        assert not is_provider_circuit_failure(DataValidationError("provider timeout"))
        assert not is_provider_circuit_failure(InvalidProviderDataError("HTTP 503"))


class TestRetryDoesNotAmplifyValidation:
    def test_stale_is_not_retried(self) -> None:
        adapter = _ShareCountErrorAdapter(
            _ShareCountValidationError(SHARES_OUTSTANDING_STALE, "stale")
        )
        service = ShareCountService(
            adapter,
            circuit_breaker=CircuitBreaker(name="share count"),
            retry=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
        )
        with pytest.raises(_ShareCountValidationError):
            service.get_share_count(_instrument())
        assert adapter.calls == 1
        assert service._breaker.failure_count == 0

    def test_provider_failure_still_retries(self) -> None:
        adapter = _ShareCountErrorAdapter(ProviderRequestError("HTTP 503"))
        service = ShareCountService(
            adapter,
            circuit_breaker=CircuitBreaker(name="share count"),
            retry=RetryPolicy(max_attempts=3, backoff_seconds=0.0),
        )
        with pytest.raises(ProviderRequestError):
            service.get_share_count(_instrument())
        assert adapter.calls == 3
        assert service._breaker.failure_count == 3


class TestBreakerDomainMessages:
    def test_market_quote_open_message(self) -> None:
        service = _quote_boom_service(ProviderRequestError("boom"), threshold=1)
        with pytest.raises(ProviderRequestError):
            service.get_quote(_instrument())
        with pytest.raises(CircuitOpenError, match="market quote circuit breaker open"):
            service.get_quote(_instrument())

    def test_share_count_open_message(self) -> None:
        service = _share_service(
            _ShareCountErrorAdapter(ProviderRequestError("boom")),
            threshold=1,
        )
        with pytest.raises(ProviderRequestError):
            service.get_share_count(_instrument())
        with pytest.raises(CircuitOpenError, match="share count circuit breaker open"):
            service.get_share_count(_instrument())

    def test_financial_statements_open_message(self) -> None:
        service = _statement_boom_service(ProviderRequestError("boom"), threshold=1)
        query = StatementQuery(_instrument())
        with pytest.raises(ProviderRequestError):
            service.get_statements(query)
        with pytest.raises(
            CircuitOpenError, match="financial statements circuit breaker open"
        ):
            service.get_statements(query)

    def test_generic_breaker_does_not_hardcode_market_quote(self) -> None:
        breaker = CircuitBreaker(name="share count", failure_threshold=1)
        breaker.record_failure()
        with pytest.raises(CircuitOpenError) as caught:
            breaker.before_call()
        assert "market quote" not in str(caught.value)
        assert caught.value.domain == "share count"
