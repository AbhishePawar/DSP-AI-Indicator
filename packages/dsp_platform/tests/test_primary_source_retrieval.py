"""B6 — local primary-source document retrieval seam tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from data_engine import (
    FinancialStatementProvenance,
    FinancialStatementService,
    InMemoryAuthenticatedQuoteAdapter,
    InMemoryAuthenticatedStatementAdapter,
    MarketQuoteProvenance,
    MarketQuoteService,
    ShareCountAcceptanceError,
    ShareCountSnapshot,
    build_quote_from_mapping,
    build_statements_from_mapping,
)
from data_engine.share_count import ACCEPTANCE_PROVIDER_ID
from dsp_platform import load_authenticated_valuation_bundle
from dsp_platform.canonical_research_ai import CanonicalAIDraft
from dsp_platform.composition.authenticated_valuation import signals_from_assessment
from dsp_platform.external_evidence import (
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    build_validated_external_evidence_package,
    validate_external_evidence_record,
)
from dsp_platform.external_evidence_discovery import (
    ExternalEvidenceDiscoveryRequest,
)
from dsp_platform.financial_statements import (
    reset_financial_statement_service_for_tests,
)
from dsp_platform.market_quotes import reset_market_quote_service_for_tests
from dsp_platform.primary_source_retrieval import (
    DOCUMENT_RETRIEVAL_NOT_CONFIGURED,
    DocumentRetrievalBlockedError,
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
    ProductionBlockedPrimarySourceDocumentRetrieval,
    extract_candidate_evidence,
    validate_document_locator,
)
from dsp_platform.primary_source_retrieval.testing import (
    FIXTURE_IDENTITY,
    FIXTURE_LOCATOR,
    FIXTURE_SHARES,
    TEST_ONLY,
    LocalDocumentExternalEvidenceDiscovery,
    LocalPrimarySourceDocumentRetrieval,
    load_local_filing_fixture,
)
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)
from dsp_platform.share_counts import (
    install_memory_share_count_for_tests,
    reset_share_count_service_for_tests,
)
from valuation import ValuationEngine

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
TICKER = "DSPX"


def _document_text(
    *,
    body: str,
    symbol: str = "DSPX",
    exchange: str = "TESTEX",
    isin: str = "DSPX00000001",
    as_of: str | None = "2024-03-31",
    publication: str | None = "2024-04-15",
    locator: str = FIXTURE_LOCATOR,
) -> str:
    lines = [
        "SYNTHETIC PRIMARY FILING — NOT A LIVE DOCUMENT.",
        f"Issuer-Symbol: {symbol}",
        f"Issuer-Exchange: {exchange}",
        f"Issuer-ISIN: {isin}",
        "Issuer-Name: DSP Test Synthetic Co",
        "Document-Type: annual_report",
        f"Source-URL: {locator}",
    ]
    if publication is not None:
        lines.append(f"Publication-Date: {publication}")
    if as_of is not None:
        lines.append(f"Fact-As-Of: {as_of}")
    lines.extend(["", body])
    return "\n".join(lines)


def _request(**overrides: object) -> PrimarySourceDocumentRequest:
    payload: dict[str, object] = {
        "identity": FIXTURE_IDENTITY,
        "locator": FIXTURE_LOCATOR,
        "document_type": PrimarySourceDocumentType.ANNUAL_REPORT,
        "fact_id": "current_outstanding",
        "retrieved_at": FIXED,
    }
    payload.update(overrides)
    return PrimarySourceDocumentRequest(**payload)  # type: ignore[arg-type]


def _retrieval(
    text: str, locator: str = FIXTURE_LOCATOR
) -> LocalPrimarySourceDocumentRetrieval:
    return LocalPrimarySourceDocumentRetrieval({locator: text})


def _discovery(
    text: str | None = None,
) -> LocalDocumentExternalEvidenceDiscovery:
    corpus_text = text if text is not None else load_local_filing_fixture()
    return LocalDocumentExternalEvidenceDiscovery(
        _retrieval(corpus_text),
        locator=FIXTURE_LOCATOR,
    )


def _discovery_request(**overrides: object) -> ExternalEvidenceDiscoveryRequest:
    payload: dict[str, object] = {
        "identity": FIXTURE_IDENTITY,
        "fact_id": "current_outstanding",
        "retrieved_at": FIXED,
    }
    payload.update(overrides)
    return ExternalEvidenceDiscoveryRequest(**payload)  # type: ignore[arg-type]


def _validated_copy(record: ExternalEvidenceRecord) -> ExternalEvidenceRecord:
    return replace(record, validation_status=EvidenceValidationStatus.VALIDATED)


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
                "exchange": "TESTEX",
                "company_name": "DSP Test Synthetic Co",
                "currency": "USD",
                "isin": "DSPX00000001",
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
            "exchange": "TESTEX",
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


class TestLocalRetrieval:
    def test_test_only_flag(self) -> None:
        assert TEST_ONLY is True
        assert LocalPrimarySourceDocumentRetrieval.TEST_ONLY is True

    def test_retrieves_synthetic_filing_without_network(self) -> None:
        text = load_local_filing_fixture()
        document = _retrieval(text).retrieve(_request())
        assert document.identity == FIXTURE_IDENTITY
        assert document.locator == FIXTURE_LOCATOR
        assert document.as_of is not None
        assert document.publication_date is not None
        assert document.retrieved_at == FIXED
        assert document.as_of != document.retrieved_at
        assert "text" not in document.to_dict()
        assert document.to_dict()["canonical"] is False
        assert "100 shares" in document.text

    def test_extracts_candidate_current_outstanding(self) -> None:
        result = _discovery().discover(_discovery_request())
        assert len(result.records) == 1
        record = result.records[0]
        assert record.validation_status is EvidenceValidationStatus.CANDIDATE
        assert record.numeric_value == pytest.approx(FIXTURE_SHARES)
        assert record.unit == "shares"
        assert record.fact_id == "current_outstanding"
        assert record.may_influence_calculation is False
        assert "outstanding" in record.evidence_reference.lower()
        assert record.retrieved_at == FIXED
        assert record.as_of != record.retrieved_at
        validate_external_evidence_record(record)

    def test_production_blocked_does_not_use_fixture(self) -> None:
        with pytest.raises(
            DocumentRetrievalBlockedError, match=DOCUMENT_RETRIEVAL_NOT_CONFIGURED
        ) as exc:
            ProductionBlockedPrimarySourceDocumentRetrieval().retrieve(_request())
        assert exc.value.retrieval_state == DOCUMENT_RETRIEVAL_NOT_CONFIGURED


class TestExtractionNegatives:
    def _extract(self, body: str, **headers: object) -> ExternalEvidenceRecord | None:
        text = _document_text(body=body, **headers)  # type: ignore[arg-type]
        document = _retrieval(text).retrieve(_request())
        return extract_candidate_evidence(
            document,
            fact_id="current_outstanding",
            requested_identity=FIXTURE_IDENTITY,
        )

    def test_authorized_shares_are_not_extracted(self) -> None:
        assert self._extract("Authorized shares were 100 shares.") is None

    def test_issued_shares_alone_are_not_extracted(self) -> None:
        assert self._extract("Issued shares were 100 shares.") is None

    def test_weighted_average_is_not_extracted(self) -> None:
        assert (
            self._extract("Weighted average shares outstanding were 100 shares.")
            is None
        )

    def test_equity_capital_is_not_extracted(self) -> None:
        assert self._extract("Equity capital was 100 shares outstanding.") is None

    def test_eps_is_not_extracted(self) -> None:
        assert (
            self._extract("Basic EPS of 1.00 implies 100 outstanding shares.")
            is None
        )

    def test_ni_eps_inference_is_not_extracted(self) -> None:
        assert (
            self._extract("Net income 100 and EPS 1 implying 100 outstanding shares.")
            is None
        )

    def test_market_cap_inversion_is_not_extracted(self) -> None:
        assert (
            self._extract(
                "Market cap 800 at price 8 implying 100 outstanding shares."
            )
            is None
        )

    def test_volume_is_not_extracted(self) -> None:
        assert self._extract("Trading volume was 100 shares outstanding.") is None

    def test_open_interest_is_not_extracted(self) -> None:
        assert self._extract("Open interest was 100 outstanding shares.") is None

    def test_millions_are_not_scaled(self) -> None:
        assert (
            self._extract("Issued and outstanding shares were 100 million shares.")
            is None
        )

    def test_malformed_number_is_not_extracted(self) -> None:
        assert self._extract("Issued and outstanding shares were abc shares.") is None

    def test_zero_is_not_extracted(self) -> None:
        assert self._extract("Issued and outstanding shares were 0 shares.") is None

    def test_missing_as_of_returns_no_candidate(self) -> None:
        text = _document_text(
            body="Issued and outstanding shares were 100 shares.",
            as_of=None,
        )
        document = _retrieval(text).retrieve(_request())
        assert document.as_of is None
        assert (
            extract_candidate_evidence(
                document,
                fact_id="current_outstanding",
                requested_identity=FIXTURE_IDENTITY,
            )
            is None
        )

    def test_identity_mismatch_fails_closed(self) -> None:
        other = ExternalEvidenceIdentity(
            symbol="INFY",
            exchange="NSE",
            isin="INE009A01021",
        )
        with pytest.raises(ExternalEvidenceValidationError, match="identity"):
            _discovery().discover(_discovery_request(identity=other))

    def test_missing_identity_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="exchange or ISIN"):
            _retrieval(load_local_filing_fixture()).retrieve(
                _request(
                    identity=ExternalEvidenceIdentity(
                        symbol="DSPX",
                        company_name="DSP Test Synthetic Co",
                    )
                )
            )

    def test_invalid_url_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="locator"):
            validate_document_locator("javascript:alert(1)")
        with pytest.raises(ExternalEvidenceValidationError, match="locator"):
            _retrieval(load_local_filing_fixture()).retrieve(
                _request(locator="javascript:alert(1)")
            )

    def test_oversized_excerpt_returns_no_candidate(self) -> None:
        padding = "x" * 480
        body = f"Issued and outstanding shares were 100 shares {padding} extra."
        assert self._extract(body) is None


class TestCannotBypassBoundaries:
    def test_candidate_cannot_enter_validated_package(self) -> None:
        record = _discovery().discover(_discovery_request()).records[0]
        with pytest.raises(ExternalEvidenceValidationError, match="candidate"):
            build_validated_external_evidence_package(
                [record], subject=FIXTURE_IDENTITY
            )

    def test_candidate_cannot_be_passed_to_b4(self) -> None:
        record = _discovery().discover(_discovery_request()).records[0]
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(record, symbol="DSPX")

    def test_document_cannot_be_passed_to_b4(self) -> None:
        document = _retrieval(load_local_filing_fixture()).retrieve(_request())
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(document, symbol="DSPX")

    def test_ai_narrative_cannot_be_passed_to_b4(self) -> None:
        draft = CanonicalAIDraft(
            output=CanonicalAIResearchOutput(
                executive_summary="Outstanding shares appear to be 100.",
            )
        )
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="DSPX")

    def test_result_is_not_valuation_or_recommendation_input(self) -> None:
        document = _retrieval(load_local_filing_fixture()).retrieve(_request())
        payload = document.to_dict()
        assert "intrinsic_value" not in payload
        assert "margin_of_safety" not in payload
        assert "recommendation" not in payload
        assert "api_key" not in str(payload)
        assert payload["may_influence_calculation"] is False


class TestExplicitChainToValuation:
    def test_local_document_to_sharecount_to_valuation(
        self, cleanup_services
    ) -> None:
        result = _discovery().discover(_discovery_request())
        candidate = result.records[0]
        validate_external_evidence_record(candidate)
        package = build_validated_external_evidence_package(
            [_validated_copy(candidate)],
            subject=FIXTURE_IDENTITY,
        )
        assert package.canonical_calculation_inputs() == {}
        snap = accept_share_count_from_validated_evidence(
            package,
            symbol="DSPX",
            exchange="TESTEX",
            isin="DSPX00000001",
        )
        assert isinstance(snap, ShareCountSnapshot)
        assert snap.shares_value() == pytest.approx(100.0)
        assert snap.provenance.endpoint == FIXTURE_LOCATOR
        assert snap.provenance.metadata["as_of_date"] == "2024-03-31"
        _install_quote_statements()
        install_memory_share_count_for_tests(snap)
        bundle = load_authenticated_valuation_bundle(TICKER, exchange="TESTEX")
        assert bundle.shares_outstanding == pytest.approx(100.0)
        assert bundle.shares_outstanding != pytest.approx(999.0)
        assert bundle.share_count_provenance["provider_id"] == ACCEPTANCE_PROVIDER_ID
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
