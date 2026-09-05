"""Stage 1F — durable promoted share-count snapshots on the analyse path."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    NullShareCountAdapter,
    ShareCountService,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from dsp_platform import (
    AuthenticatedValuationError,
    CompositionRequest,
    PlatformOrchestrator,
    load_authenticated_valuation_bundle,
)
from dsp_platform.composition.authenticated_valuation import _resolve_shares
from dsp_platform.financial_statements import reset_financial_statement_service_for_tests
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    SHARES_OUTSTANDING_CONFLICT,
    SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
    SHARES_OUTSTANDING_IDENTITY_MISMATCH,
    SHARES_OUTSTANDING_STALE,
    SHARES_OUTSTANDING_TAMPERED,
    DurablePromotedShareCountAdapter,
    ShareCountResolutionError,
    sign_promoted_snapshot,
)
from dsp_platform.share_counts import (
    reset_share_count_service_for_tests,
    resolve_authoritative_share_count,
)
from valuation import ValuationEngine

_REPO = Path(__file__).resolve().parents[3]
_PROMOTED_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"
_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_PRICE = 3500.25
_EPS = Decimal("10")


def _payload() -> dict:
    return json.loads(_PROMOTED_JSON.read_text(encoding="utf-8"))


def _expected_shares() -> Decimal:
    return Decimal(str(_payload()["shares_outstanding"]))


def _tcs_instrument(
    *,
    symbol: str = "TCS",
    exchange: str = "NSE",
    isin: str | None = "INE467B01029",
) -> Instrument:
    return Instrument(
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange=exchange,
        isin=isin,
        name="Tata Consultancy Services",
    )


def _install_promoted(*, now: datetime = _HORIZON, directory: Path | None = None) -> None:
    adapter = DurablePromotedShareCountAdapter(directory=directory, now=lambda: now)
    reset_share_count_service_for_tests(ShareCountService(adapter))


def _seed_statements(*, net_income: Decimal, eps: Decimal = _EPS):
    ni = float(net_income)
    eps_f = float(eps)
    return build_statements_from_mapping(
        symbol="TCS",
        payload={
            "identity": {
                "symbol": "TCS",
                "exchange": "NSE",
                "company_name": "Tata Consultancy Services",
                "currency": "INR",
                "isin": "INE467B01029",
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
                        "eps_basic": eps_f,
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


def _seed_quote(*, shares=None, exchange="NSE", isin="INE467B01029", price=_PRICE):
    payload = {
        "exchange": exchange,
        "currency": "INR",
        "current_price": price,
        "previous_close": price,
    }
    if shares is not None:
        payload["shares_outstanding"] = shares
    return build_quote_from_mapping(
        symbol="TCS",
        payload=payload,
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=_HORIZON,
            auth_mode="api_key",
            metadata={"isin": isin, "exchange": exchange} if isin else {"exchange": exchange},
        ),
    )


@pytest.fixture
def tcs_auth_services():
    shares = _expected_shares()
    stmt = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt.put(_seed_statements(net_income=shares * _EPS))
    quote = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt))
    reset_market_quote_service_for_tests(MarketQuoteService(quote))
    _install_promoted()
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


class TestPromotedSnapshotAcceptance:
    def test_snapshot_resolves_by_isin_not_ticker_constant(self) -> None:
        _install_promoted()
        try:
            snapshot = resolve_authoritative_share_count(_tcs_instrument())
            assert snapshot is not None
            assert snapshot.isin == "INE467B01029"
            assert snapshot.exchange == "NSE"
            assert snapshot.symbol == "TCS"
            assert snapshot.provenance.metadata["mic"] == "XNSE"
            assert snapshot.as_of is not None
            assert snapshot.as_of.date() == date(2026, 6, 30)
            assert snapshot.provenance.metadata["complete_through"] == "2026-09-05"
            assert snapshot.provenance.metadata["source_tier"] == "TIER_1_PRIMARY"
            assert snapshot.provenance.metadata["corporate_action_adjusted"] == "true"
            assert snapshot.shares_value() == pytest.approx(float(_expected_shares()))
        finally:
            reset_share_count_service_for_tests(None)

    def test_ticker_alone_does_not_resolve(self) -> None:
        _install_promoted()
        try:
            snapshot = resolve_authoritative_share_count(
                _tcs_instrument(isin=None)
            )
            assert snapshot is None
        finally:
            reset_share_count_service_for_tests(None)

    def test_resolve_shares_accepts_overlay_and_valuation_proceeds(
        self, tcs_auth_services
    ) -> None:
        bundle = load_authenticated_valuation_bundle("TCS", exchange="NSE", currency="INR")
        expected = float(_expected_shares())
        assert bundle.shares_outstanding == pytest.approx(expected)
        assert bundle.current_market_price == pytest.approx(_PRICE)
        assert bundle.market_snapshot.market_cap == pytest.approx(_PRICE * expected)
        assessment = ValuationEngine(clock=lambda: _HORIZON).analyze(
            bundle.financial_snapshot,
            bundle.market_snapshot,
        )
        assert assessment.valuation_range.mid is not None
        per_share = float(assessment.valuation_range.mid) / expected
        assert per_share > 0

    def test_resolve_shares_still_the_fail_closed_gate(self, tcs_auth_services) -> None:
        bundle = load_authenticated_valuation_bundle("TCS", exchange="NSE", currency="INR")
        from data_engine.market_quote.models import QuoteField

        class _Empty:
            shares_outstanding = QuoteField.missing()

        with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
            _resolve_shares(_Empty(), None)  # type: ignore[arg-type]


class TestPromotedSnapshotSecurity:
    def test_wrong_isin_does_not_receive_snapshot(self) -> None:
        _install_promoted()
        try:
            snapshot = resolve_authoritative_share_count(
                _tcs_instrument(isin="US87612E1064")
            )
            assert snapshot is None
        finally:
            reset_share_count_service_for_tests(None)

    def test_wrong_mic_exchange_fails(self) -> None:
        _install_promoted()
        try:
            with pytest.raises(
                ShareCountResolutionError, match=SHARES_OUTSTANDING_IDENTITY_MISMATCH
            ):
                resolve_authoritative_share_count(
                    _tcs_instrument(exchange="NYSE")
                )
        finally:
            reset_share_count_service_for_tests(None)

    def test_wrong_symbol_with_matching_isin_fails(self) -> None:
        _install_promoted()
        try:
            with pytest.raises(
                ShareCountResolutionError, match=SHARES_OUTSTANDING_IDENTITY_MISMATCH
            ):
                resolve_authoritative_share_count(
                    _tcs_instrument(symbol="INFY")
                )
        finally:
            reset_share_count_service_for_tests(None)

    def test_stale_complete_through_fails(self, tmp_path: Path) -> None:
        payload = _payload()
        payload["complete_through"] = "2026-08-01"
        payload.pop("integrity", None)
        (tmp_path / "stale.json").write_text(
            json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            adapter.get_share_count(_tcs_instrument())

    def test_float_field_never_satisfies_provider(self, tmp_path: Path) -> None:
        payload = _payload()
        payload["float"] = str(_expected_shares())
        payload.pop("integrity", None)
        (tmp_path / "float.json").write_text(
            json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        with pytest.raises(ShareCountResolutionError):
            adapter.get_share_count(_tcs_instrument())

    def test_weighted_average_basis_never_satisfies_provider(self, tmp_path: Path) -> None:
        payload = _payload()
        payload["basis"] = "weighted_average_shares_basic"
        payload.pop("integrity", None)
        (tmp_path / "was.json").write_text(
            json.dumps(sign_promoted_snapshot(payload)), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN):
            adapter.get_share_count(_tcs_instrument())

    def test_missing_snapshot_returns_none(self, tmp_path: Path) -> None:
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        assert adapter.get_share_count(_tcs_instrument()) is None

    def test_conflicting_sources_fail_closed(self, tmp_path: Path) -> None:
        first = _payload()
        second = _payload()
        second["shares_outstanding"] = "1"
        first.pop("integrity", None)
        second.pop("integrity", None)
        (tmp_path / "a.json").write_text(
            json.dumps(sign_promoted_snapshot(first)), encoding="utf-8"
        )
        (tmp_path / "b.json").write_text(
            json.dumps(sign_promoted_snapshot(second)), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_CONFLICT):
            adapter.get_share_count(_tcs_instrument())

    def test_tampered_snapshot_fails(self, tmp_path: Path) -> None:
        payload = _payload()
        payload["shares_outstanding"] = "1"
        (tmp_path / "tampered.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        adapter = DurablePromotedShareCountAdapter(directory=tmp_path, now=lambda: _HORIZON)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_TAMPERED):
            adapter.get_share_count(_tcs_instrument())

    def test_gemini_is_not_a_runtime_dependency(self) -> None:
        import ast

        path = (
            _REPO
            / "packages"
            / "dsp_platform"
            / "src"
            / "dsp_platform"
            / "promoted_share_count.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        assert "llm_adapters" not in imported
        assert "httpx" not in imported
        assert "google" not in imported
        auth = (
            _REPO
            / "packages"
            / "dsp_platform"
            / "src"
            / "dsp_platform"
            / "composition"
            / "authenticated_valuation.py"
        ).read_text(encoding="utf-8")
        assert "GeminiAdapter" not in auth
        assert "llm_adapters" not in auth
        assert "_resolve_shares" in auth


class TestNoHardcodedTcsBusinessRule:
    def test_production_python_does_not_embed_tcs_share_count(self) -> None:
        roots = (
            _REPO / "packages" / "dsp_platform" / "src",
            _REPO / "packages" / "data_engine" / "src",
            _REPO / "packages" / "api_platform" / "src",
            _REPO / "packages" / "valuation" / "src",
        )
        offenders: list[str] = []
        for root in roots:
            for path in root.rglob("*.py"):
                text = path.read_text(encoding="utf-8")
                if "3618087518" in text or "3,618,087,518" in text:
                    offenders.append(path.as_posix())
        assert offenders == []


class TestFailClosedWithoutSnapshot:
    def test_missing_provider_still_fails_closed(self, tcs_auth_services) -> None:
        reset_share_count_service_for_tests(ShareCountService(NullShareCountAdapter()))
        with pytest.raises(AuthenticatedValuationError, match="shares outstanding"):
            load_authenticated_valuation_bundle("TCS", exchange="NSE", currency="INR")


class TestPipelineUsesOverlay:
    def test_composition_succeeds_for_tcs_without_quote_shares(
        self, tcs_auth_services
    ) -> None:
        result = PlatformOrchestrator(platform_version="test").execute(
            CompositionRequest(ticker="TCS", exchange="NSE")
        )
        assert result.ok is True
        assert result.metadata.failed_stage is None
        assert (result.valuation_signals or result.valuation) is not None
        errors = " ".join(result.errors or []).lower()
        assert "shares outstanding" not in errors
