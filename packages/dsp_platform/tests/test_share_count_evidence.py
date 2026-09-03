"""B4 — validated external evidence → ShareCountSnapshot → valuation (test-only)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import inf, nan

import pytest

from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    ShareCountAcceptanceError,
    ShareCountBasis,
    ShareCountUnit,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.share_count import ACCEPTANCE_PROVIDER_ID
from dsp_platform import load_authenticated_valuation_bundle
from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.composition.authenticated_valuation import signals_from_assessment
from dsp_platform.external_evidence import (
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    SourceTier,
    SourceType,
    build_validated_external_evidence_package,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)
from dsp_platform.share_counts import (
    install_memory_share_count_for_tests,
    reset_share_count_service_for_tests,
)
from valuation import ValuationEngine

TICKER = "TEST"
FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 3, 31)
PUBLISHED = date(2024, 4, 15)
SUBJECT = ExternalEvidenceIdentity(
    symbol="TEST",
    exchange="NYSE",
    isin="US0000000001",
    company_name="Test Corp",
)


def _identity(**overrides: object) -> ExternalEvidenceIdentity:
    payload = {
        "symbol": SUBJECT.symbol,
        "exchange": SUBJECT.exchange,
        "isin": SUBJECT.isin,
        "company_name": SUBJECT.company_name,
    }
    payload.update(overrides)
    return ExternalEvidenceIdentity(**payload)  # type: ignore[arg-type]


def _outstanding(**overrides: object) -> ExternalEvidenceRecord:
    payload: dict[str, object] = {
        "fact_id": "current_outstanding",
        "identity": _identity(),
        "evidence_kind": EvidenceKind.NUMERICAL,
        "numeric_value": 100.0,
        "unit": "shares",
        "as_of": AS_OF,
        "publication_date": PUBLISHED,
        "source_url": "https://www.sec.gov/Archives/edgar/test-outstanding",
        "source_type": SourceType.FILING,
        "source_tier": SourceTier.TIER_1_PRIMARY,
        "evidence_reference": (
            "Note 12: issued and outstanding share capital was 100 shares."
        ),
        "retrieved_at": FIXED,
        "evidence_quality": EvidenceQuality.HIGH,
        "validation_status": EvidenceValidationStatus.VALIDATED,
        "may_influence_calculation": False,
    }
    payload.update(overrides)
    return ExternalEvidenceRecord(**payload)  # type: ignore[arg-type]


def _package(*records: ExternalEvidenceRecord):
    return build_validated_external_evidence_package(records, subject=SUBJECT)


def _stmt_provenance() -> FinancialStatementProvenance:
    return FinancialStatementProvenance(
        provider_id="memory_authenticated_statements",
        provider_name="Memory Statements",
        source_type="licensed_vendor",
        retrieved_at=FIXED,
        auth_mode="api_key",
    )


def _seed_statements():
    return build_statements_from_mapping(
        symbol=TICKER,
        payload={
            "identity": {
                "symbol": TICKER,
                "exchange": "NYSE",
                "company_name": "Test Corp",
                "currency": "USD",
                "isin": "US0000000001",
            },
            "reporting_currency": "USD",
            "statement_basis": "consolidated",
            "unit_scale": "actual",
            "periods": [
                {
                    "period_type": "annual",
                    "fiscal_year": 2024,
                    "period_end": "2024-12-31",
                    "filing_date": "2025-02-01",
                    "reporting_currency": "USD",
                    "restated": False,
                    "income_statement": {
                        "revenue": 500.0,
                        "net_income": 100.0,
                        "eps_basic": 1.0,
                        "operating_income": 120.0,
                    },
                    "balance_sheet": {
                        "cash": 50.0,
                        "total_assets": 1500.0,
                        "total_liabilities": 500.0,
                        "equity": 1000.0,
                        "total_debt": 200.0,
                    },
                    "cash_flow": {
                        "operating_cash_flow": 150.0,
                        "capex": -30.0,
                        "free_cash_flow": 120.0,
                    },
                    "ratios": {},
                }
            ],
        },
        provenance=_stmt_provenance(),
    )


def _seed_quote(*, shares: float | None = 999.0, price: float = 8.0):
    return build_quote_from_mapping(
        symbol=TICKER,
        payload={
            "exchange": "NYSE",
            "currency": "USD",
            "current_price": price,
            "previous_close": price,
            "market_cap": price * 100.0,
            "shares_outstanding": shares,
        },
        provenance=MarketQuoteProvenance(
            provider_id="memory_authenticated_quote",
            provider_name="Memory Quote",
            source_type="licensed_vendor",
            retrieved_at=FIXED,
            auth_mode="api_key",
        ),
    )


def _install_quote_statements() -> None:
    stmt_adapter = InMemoryAuthenticatedStatementAdapter(api_key="test-key")
    stmt_adapter.put(_seed_statements())
    quote_adapter = InMemoryAuthenticatedQuoteAdapter(api_key="test-key")
    quote_adapter.put(_seed_quote())
    reset_financial_statement_service_for_tests(FinancialStatementService(stmt_adapter))
    reset_market_quote_service_for_tests(MarketQuoteService(quote_adapter))


@pytest.fixture
def cleanup_services():
    yield
    reset_financial_statement_service_for_tests(None)
    reset_market_quote_service_for_tests(None)
    reset_share_count_service_for_tests(None)


class TestShareCountEvidenceAcceptance:
    def test_validated_package_does_not_auto_create_snapshot(self) -> None:
        package = _package(_outstanding())
        assert package.canonical_calculation_inputs() == {}

    def test_explicit_acceptance_creates_current_outstanding_snapshot(self) -> None:
        package = _package(_outstanding())
        snap = accept_share_count_from_validated_evidence(
            package,
            symbol="TEST",
            exchange="NYSE",
            isin="US0000000001",
        )
        assert snap.shares_value() == pytest.approx(100.0)
        assert snap.basis is ShareCountBasis.CURRENT_OUTSTANDING
        assert snap.unit is ShareCountUnit.SHARES
        assert snap.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        assert snap.provenance.metadata["publication_date"] == "2024-04-15"
        assert snap.provenance.metadata["as_of_date"] == "2024-03-31"
        assert "outstanding" in snap.provenance.metadata["evidence_reference"].lower()


class TestShareCountEvidenceNegatives:
    def test_ai_narrative_cannot_create_snapshot(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(
                "The company has 100 outstanding shares.",
                symbol="TEST",
            )

    def test_canonical_ai_output_cannot_create_snapshot(self) -> None:
        draft = CanonicalAIDraft(
            output=CanonicalAIResearchOutput(
                executive_summary="Outstanding shares appear to be 100.",
                financial_metrics={"current_outstanding": 100.0},
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="TEST")
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft.output, symbol="TEST")

    def test_candidate_cannot_enter_acceptance(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="candidate"):
            _package(
                _outstanding(validation_status=EvidenceValidationStatus.CANDIDATE)
            )

    def test_rejected_cannot_enter_acceptance(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="rejected"):
            _package(
                _outstanding(validation_status=EvidenceValidationStatus.REJECTED)
            )

    def test_tier3_cannot_enter_validated_package(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="Tier 3"):
            _package(_outstanding(source_tier=SourceTier.TIER_3_DISCOVERY))

    def test_tier4_cannot_become_sharecount_authority(self) -> None:
        package = _package(
            _outstanding(
                source_tier=SourceTier.TIER_4_NEWS_CONTEXT,
                source_type=SourceType.NEWS,
                source_url="https://www.reuters.test/markets/test-outstanding",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="Tier 3/4"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    def test_weighted_average_cannot_become_current_outstanding(self) -> None:
        package = _package(
            _outstanding(
                fact_id="weighted_average_shares_diluted",
                evidence_reference="Weighted average diluted shares were 100.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="weighted-average"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    def test_equity_capital_cannot_become_current_outstanding(self) -> None:
        package = _package(
            _outstanding(
                fact_id="equity_capital",
                unit="INR",
                evidence_reference="Equity capital was INR 100.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="equity capital"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    def test_eps_cannot_become_current_outstanding(self) -> None:
        package = _package(
            _outstanding(
                fact_id="eps",
                numeric_value=1.0,
                unit="USD",
                evidence_reference="Basic EPS was USD 1.00.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="EPS"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    def test_market_cap_cannot_become_current_outstanding(self) -> None:
        package = _package(
            _outstanding(
                fact_id="market_cap",
                numeric_value=800.0,
                unit="USD",
                evidence_reference="Market capitalization was USD 800.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="market cap"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    def test_identity_mismatch_tcs_on_infy_rejected(self) -> None:
        tcs = ExternalEvidenceIdentity(
            symbol="TCS",
            exchange="NSE",
            isin="INE467B01029",
        )
        record = _outstanding(identity=tcs)
        package = build_validated_external_evidence_package([record], subject=tcs)
        with pytest.raises(ShareCountAcceptanceError, match="identity mismatch"):
            accept_share_count_from_validated_evidence(
                package, symbol="INFY", exchange="NSE"
            )

    def test_nse_not_mapped_to_bse(self) -> None:
        package = _package(_outstanding())
        with pytest.raises(ShareCountAcceptanceError, match="exchange mismatch"):
            accept_share_count_from_validated_evidence(
                package, symbol="TEST", exchange="BSE"
            )

    def test_missing_as_of_rejected(self) -> None:
        package = _package(_outstanding(as_of=None))
        with pytest.raises(ShareCountAcceptanceError, match="as_of"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    @pytest.mark.parametrize("value", [0, -5])
    def test_non_positive_share_count_rejected(self, value: float) -> None:
        package = _package(_outstanding(numeric_value=value))
        with pytest.raises(ShareCountAcceptanceError):
            accept_share_count_from_validated_evidence(package, symbol="TEST")

    @pytest.mark.parametrize("value", [nan, inf])
    def test_non_finite_share_count_rejected_before_acceptance(
        self, value: float
    ) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="finite"):
            _package(_outstanding(numeric_value=value))

    def test_unresolved_conflict_rejected(self) -> None:
        package = _package(
            _outstanding(numeric_value=100.0, fact_id="current_outstanding"),
            _outstanding(
                numeric_value=200.0,
                fact_id="shares_outstanding",
                source_url="https://www.sec.gov/Archives/edgar/other-outstanding",
            ),
        )
        with pytest.raises(ShareCountAcceptanceError, match="conflict"):
            accept_share_count_from_validated_evidence(package, symbol="TEST")


class TestShareCountEvidenceValuationPath:
    def test_accepted_snapshot_feeds_authenticated_valuation(
        self, cleanup_services
    ) -> None:
        package = _package(_outstanding())
        snap = accept_share_count_from_validated_evidence(
            package,
            symbol="TEST",
            exchange="NYSE",
            isin="US0000000001",
        )
        _install_quote_statements()
        install_memory_share_count_for_tests(snap)
        bundle = load_authenticated_valuation_bundle(TICKER)
        assert bundle.shares_outstanding == pytest.approx(100.0)
        assert bundle.shares_outstanding != pytest.approx(999.0)
        assert bundle.share_count_provenance["provider_id"] == ACCEPTANCE_PROVIDER_ID
        assert bundle.share_count_provenance["endpoint"] == (
            "https://www.sec.gov/Archives/edgar/test-outstanding"
        )
        meta = bundle.share_count_provenance["metadata"]
        assert meta["source_tier"] == "TIER_1_PRIMARY"
        assert meta["as_of_date"] == "2024-03-31"
        assert meta["publication_date"] == "2024-04-15"
        assessment = ValuationEngine(clock=lambda: FIXED).analyze(
            bundle.financial_snapshot,
            bundle.market_snapshot,
        )
        signals = signals_from_assessment(
            assessment,
            current_market_price=bundle.current_market_price,
            shares_outstanding=bundle.shares_outstanding,
        )
        assert signals.intrinsic_value_per_share is not None
        assert signals.intrinsic_value_per_share > 0
        assert signals.margin_of_safety is not None
        company_iv = float(assessment.valuation_range.mid)
        assert signals.intrinsic_value_per_share == pytest.approx(
            company_iv / bundle.shares_outstanding
        )
