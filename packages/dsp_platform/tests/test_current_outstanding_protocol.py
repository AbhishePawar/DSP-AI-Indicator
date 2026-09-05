"""AI-assisted current-outstanding protocol — fail-closed, AI off by default."""

from __future__ import annotations

from datetime import UTC, date, datetime
from math import inf, nan

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.share_count import (
    ACCEPTANCE_PROVIDER_ID,
    InMemoryShareCountAdapter,
    NullShareCountAdapter,
    ShareCountAcceptanceError,
    ShareCountBasis,
    ShareCountSnapshot,
    ShareCountUnit,
    accept_current_outstanding_claims,
    build_share_count_from_mapping,
)
from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.canonical_research_ai.port import (
    ProductionBlockedCanonicalResearchAiPort,
)
from dsp_platform.current_outstanding_protocol import (
    CurrentOutstandingDiagnostic,
    UntrustedShareCountAiCandidate,
    dsp_accept_untrusted_share_count_candidate,
    production_current_outstanding_protocol,
)
from dsp_platform.current_outstanding_protocol.ai_candidate import (
    untrusted_candidate_from_ai_draft,
)
from dsp_platform.current_outstanding_protocol.protocol import (
    CurrentOutstandingProtocol,
)
from dsp_platform.current_outstanding_protocol.testing import (
    DeterministicShareCountExtractionAiPort,
    fixture_option_b_currentness,
)
from dsp_platform.external_evidence.models import (
    SourceTier,
    SourceType,
)
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)
from dsp_platform.primary_source_retrieval.port import (
    ProductionBlockedPrimarySourceDocumentRetrieval,
)
from dsp_platform.primary_source_retrieval.testing import (
    FIXTURE_IDENTITY,
    FIXTURE_LOCATOR,
    LocalDocumentExternalEvidenceDiscovery,
    LocalPrimarySourceDocumentRetrieval,
    load_local_filing_fixture,
)
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
AS_OF = date(2024, 3, 31)
EXCERPT = "As of 31 March 2024, issued and outstanding shares were 100 shares."
_Diag = CurrentOutstandingDiagnostic


def _instrument() -> Instrument:
    return Instrument(
        symbol="DSPX",
        asset_class=AssetClass.EQUITY,
        currency="USD",
        exchange="TESTEX",
        isin="DSPX00000001",
        name="DSP Test Synthetic Co",
    )


def _document(**overrides: object) -> RetrievedPrimarySourceDocument:
    payload: dict[str, object] = {
        "identity": FIXTURE_IDENTITY,
        "locator": FIXTURE_LOCATOR,
        "document_type": PrimarySourceDocumentType.ANNUAL_REPORT,
        "source_type": SourceType.FILING,
        "source_tier": SourceTier.TIER_1_PRIMARY,
        "retrieved_at": FIXED,
        "text": load_local_filing_fixture(),
        "publication_date": date(2024, 4, 15),
        "as_of": AS_OF,
    }
    payload.update(overrides)
    return RetrievedPrimarySourceDocument(**payload)  # type: ignore[arg-type]


def _candidate(**overrides: object) -> UntrustedShareCountAiCandidate:
    payload: dict[str, object] = {
        "company_identity": "DSPX",
        "claimed_share_count": 100,
        "unit": "shares",
        "as_of_date": AS_OF,
        "source_reference": FIXTURE_LOCATOR,
        "evidence_reference": EXCERPT,
        "supporting_excerpt": EXCERPT,
    }
    payload.update(overrides)
    return UntrustedShareCountAiCandidate(**payload)  # type: ignore[arg-type]


def _local_protocol(
    *,
    share_count_port=None,
    ai=None,
    retrieval=None,
    discovery=None,
) -> CurrentOutstandingProtocol:
    retrieval = retrieval or LocalPrimarySourceDocumentRetrieval(
        {FIXTURE_LOCATOR: load_local_filing_fixture()}
    )
    discovery = discovery or LocalDocumentExternalEvidenceDiscovery(
        retrieval,
        locator=FIXTURE_LOCATOR,
    )
    return CurrentOutstandingProtocol(
        share_count_port=share_count_port or NullShareCountAdapter(),
        discovery=discovery,
        retrieval=retrieval,
        ai=ai or DeterministicShareCountExtractionAiPort(),
    )


def _extraction(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "company_identity": "DSPX",
        "claimed_share_count": 100,
        "unit": "shares",
        "as_of_date": "2024-03-31",
        "source_reference": FIXTURE_LOCATOR,
        "evidence_reference": EXCERPT,
        "supporting_excerpt": EXCERPT,
    }
    payload.update(overrides)
    return payload


class TestAiCannotCreateSnapshot:
    def test_untrusted_candidate_is_not_a_snapshot(self) -> None:
        candidate = _candidate()
        assert not isinstance(candidate, ShareCountSnapshot)
        with pytest.raises(ShareCountAcceptanceError, match="ShareCountEvidenceClaim"):
            accept_current_outstanding_claims([candidate], symbol="DSPX")  # type: ignore[list-item]

    def test_canonical_ai_draft_cannot_create_snapshot(self) -> None:
        draft = CanonicalAIDraft(
            output=CanonicalAIResearchOutput(
                executive_summary="Outstanding shares appear to be 100.",
                financial_metrics={"current_outstanding": 100.0},
                intrinsic_value=12.0,
                margin_of_safety=0.4,
                recommendation_action="BUY",
            ),
            untrusted_extraction=_extraction(),
        )
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="DSPX")
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            dsp_accept_untrusted_share_count_candidate(
                draft,
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )


class TestDspPromotionRejects:
    def test_candidate_without_source_evidence_is_rejected(self) -> None:
        parsed = untrusted_candidate_from_ai_draft(
            CanonicalAIDraft(
                output=CanonicalAIResearchOutput(),
                untrusted_extraction=_extraction(source_reference=""),
            )
        )
        assert parsed is None

    def test_candidate_without_as_of_is_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="as_of"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(as_of_date=None),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_ambiguous_unit_is_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="shares"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(unit="%"),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_wrong_company_identity_is_rejected(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="identity mismatch"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(company_identity="INFY"),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    @pytest.mark.parametrize("value", [0, -1, nan, inf, "not-a-number"])
    def test_invalid_share_count_is_rejected(self, value: object) -> None:
        with pytest.raises(ShareCountAcceptanceError):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(claimed_share_count=value),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_weighted_average_cannot_become_current_outstanding(self) -> None:
        excerpt = "Weighted-average basic shares outstanding were 100 shares."
        document = _document(text=excerpt, as_of=AS_OF)
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                    source_reference=FIXTURE_LOCATOR,
                ),
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_market_cap_derived_shares_rejected(self) -> None:
        excerpt = "Implied outstanding shares from market cap were 100 shares."
        document = _document(text=excerpt, as_of=AS_OF)
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                    source_reference=FIXTURE_LOCATOR,
                ),
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )


class TestExistingAcceptancePath:
    def test_valid_primary_evidence_uses_existing_acceptance(self) -> None:
        snap = dsp_accept_untrusted_share_count_candidate(
            _candidate(),
            document=_document(),
            requested_identity=FIXTURE_IDENTITY,
        )
        assert isinstance(snap, ShareCountSnapshot)
        assert snap.shares_value() == pytest.approx(100.0)
        assert snap.basis is ShareCountBasis.CURRENT_OUTSTANDING
        assert snap.unit is ShareCountUnit.SHARES
        assert snap.provenance.provider_id == ACCEPTANCE_PROVIDER_ID

    def test_million_shares_normalized_then_accepted(self) -> None:
        excerpt = "Issued and outstanding shares were 100 million shares."
        document = _document(text=excerpt, as_of=AS_OF)
        snap = dsp_accept_untrusted_share_count_candidate(
            _candidate(
                claimed_share_count=100,
                unit="million shares",
                supporting_excerpt=excerpt,
                evidence_reference=excerpt,
            ),
            document=document,
            requested_identity=FIXTURE_IDENTITY,
        )
        assert snap.shares_value() == pytest.approx(100_000_000)
        assert snap.unit is ShareCountUnit.SHARES

    def test_conflict_follows_existing_acceptance_contract(self) -> None:
        first = dsp_accept_untrusted_share_count_candidate(
            _candidate(),
            document=_document(),
            requested_identity=FIXTURE_IDENTITY,
        )
        second_excerpt = (
            "As of 31 March 2024, issued and outstanding shares were 200 shares."
        )
        second_doc = _document(
            text=second_excerpt,
            locator="https://fixtures.dsp.test/filings/DSPX-FY24-other",
            as_of=AS_OF,
        )
        second = dsp_accept_untrusted_share_count_candidate(
            _candidate(
                claimed_share_count=200,
                supporting_excerpt=second_excerpt,
                evidence_reference=second_excerpt,
                source_reference=second_doc.locator,
            ),
            document=second_doc,
            requested_identity=FIXTURE_IDENTITY,
        )
        from data_engine.share_count.acceptance import ShareCountEvidenceClaim

        def _claim_from_snap(
            snap: ShareCountSnapshot,
            shares: int,
            url: str,
            excerpt: str,
        ):
            return ShareCountEvidenceClaim(
                symbol=snap.symbol,
                exchange=snap.exchange,
                isin=snap.isin,
                shares=shares,
                unit="shares",
                basis="current_outstanding",
                as_of=AS_OF,
                source_url=url,
                source_type="filing",
                source_tier="TIER_1_PRIMARY",
                evidence_reference=excerpt,
                retrieved_at=FIXED,
                fact_id="current_outstanding",
                validation_status="validated",
            )

        with pytest.raises(ShareCountAcceptanceError, match="conflict"):
            accept_current_outstanding_claims(
                [
                    _claim_from_snap(first, 100, FIXTURE_LOCATOR, EXCERPT),
                    _claim_from_snap(
                        second, 200, second_doc.locator, second_excerpt
                    ),
                ],
                symbol="DSPX",
                exchange="TESTEX",
                isin="DSPX00000001",
            )


class TestProtocolOrchestration:
    def test_valid_fixture_path_validates_through_dsp(self) -> None:
        result = _local_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
            corporate_action_currentness=fixture_option_b_currentness(
                as_of=AS_OF, retrieved_at=FIXED
            ),
        )
        assert result.diagnostic is _Diag.SHARECOUNT_VALIDATED
        assert result.upstox_status is _Diag.UPSTOX_VALUE_UNAVAILABLE
        assert result.current_shares_outstanding == pytest.approx(100.0)
        assert result.snapshot is not None
        assert result.snapshot.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        public = result.to_public_dict()
        assert public["current_shares_outstanding"] == pytest.approx(100.0)
        assert "prompt" not in public
        assert "model" not in public
        assert "untrusted_extraction" not in public

    def test_valid_fixture_without_corporate_actions_is_option_b_unproven(self) -> None:
        result = _local_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.OPTION_B_UNPROVEN
        assert result.snapshot is None
        assert result.current_shares_outstanding is None

    def test_production_ai_and_discovery_remain_blocked(self) -> None:
        protocol = production_current_outstanding_protocol(NullShareCountAdapter())
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.EVIDENCE_DISCOVERY_BLOCKED
        assert result.current_shares_outstanding is None
        assert result.snapshot is None

    def test_ai_execution_blocked_when_discovery_and_retrieval_injected(
        self,
    ) -> None:
        retrieval = LocalPrimarySourceDocumentRetrieval(
            {FIXTURE_LOCATOR: load_local_filing_fixture()}
        )
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=LocalDocumentExternalEvidenceDiscovery(
                retrieval, locator=FIXTURE_LOCATOR
            ),
            retrieval=retrieval,
            ai=ProductionBlockedCanonicalResearchAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.AI_EXECUTION_BLOCKED
        assert result.current_shares_outstanding is None

    def test_document_retrieval_blocked_after_discovery_locator(self) -> None:
        retrieval = LocalPrimarySourceDocumentRetrieval(
            {FIXTURE_LOCATOR: load_local_filing_fixture()}
        )
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=LocalDocumentExternalEvidenceDiscovery(
                retrieval, locator=FIXTURE_LOCATOR
            ),
            retrieval=ProductionBlockedPrimarySourceDocumentRetrieval(),
            ai=DeterministicShareCountExtractionAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.DOCUMENT_RETRIEVAL_BLOCKED
        assert result.current_shares_outstanding is None

    def test_malformed_ai_candidate_is_rejected(self) -> None:
        protocol = _local_protocol(
            ai=DeterministicShareCountExtractionAiPort(
                extraction={"company_identity": "DSPX"}
            )
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.AI_CANDIDATE_REJECTED
        assert result.current_shares_outstanding is None

    def test_authoritative_port_value_short_circuits(self) -> None:
        from data_engine.share_count.models import ShareCountProvenance

        adapter = InMemoryShareCountAdapter(api_key="test-key")
        adapter.put(
            build_share_count_from_mapping(
                symbol="DSPX",
                payload={
                    "exchange": "TESTEX",
                    "isin": "DSPX00000001",
                    "shares": 250.0,
                    "as_of": FIXED,
                },
                provenance=ShareCountProvenance(
                    provider_id="upstox_share_count_test",
                    provider_name="TEST-ONLY Upstox slot",
                    source_type="licensed_vendor",
                    retrieved_at=FIXED,
                    auth_mode="api_key",
                ),
            )
        )

        class _BoomDiscovery:
            def discover(self, request):  # noqa: ANN001
                raise AssertionError("discovery must not run when Upstox value present")

        protocol = CurrentOutstandingProtocol(
            share_count_port=adapter,
            discovery=_BoomDiscovery(),  # type: ignore[arg-type]
            retrieval=ProductionBlockedPrimarySourceDocumentRetrieval(),
            ai=ProductionBlockedCanonicalResearchAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.UPSTOX_VALUE_PRESENT
        assert result.current_shares_outstanding == pytest.approx(250.0)

    def test_ai_cannot_directly_modify_valuation_or_recommendation(self) -> None:
        valuation_state = {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        recommendation_state = {"action": "HOLD", "score": 55}
        protocol = _local_protocol(
            ai=DeterministicShareCountExtractionAiPort(
                extraction=_extraction(
                    claimed_share_count=100,
                )
            )
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert valuation_state == {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        assert recommendation_state == {"action": "HOLD", "score": 55}
        public = result.to_public_dict()
        assert "intrinsic_value" not in public
        assert "margin_of_safety" not in public
        assert "recommendation" not in public
        assert not hasattr(result, "intrinsic_value")
        assert not hasattr(result, "recommendation")

    def test_unavailable_is_none_not_zero(self) -> None:
        result = production_current_outstanding_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.current_shares_outstanding is None
        assert result.current_shares_outstanding != 0


class TestExistingSurfacesUnchanged:
    def test_quote_shares_outstanding_field_is_unchanged(self) -> None:
        from data_engine import MarketQuoteProvenance, build_quote_from_mapping

        quote = build_quote_from_mapping(
            symbol="TEST",
            payload={
                "exchange": "NYSE",
                "currency": "USD",
                "current_price": 8.0,
                "previous_close": 8.0,
                "shares_outstanding": 999.0,
            },
            provenance=MarketQuoteProvenance(
                provider_id="memory_authenticated_quote",
                provider_name="Memory Quote",
                source_type="licensed_vendor",
                retrieved_at=FIXED,
                auth_mode="api_key",
            ),
        )
        assert quote.shares_outstanding.value == pytest.approx(999.0)

    def test_authenticated_valuation_source_does_not_call_protocol(self) -> None:
        from pathlib import Path

        auth = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "dsp_platform"
            / "composition"
            / "authenticated_valuation.py"
        )
        pipeline = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "dsp_platform"
            / "composition"
            / "pipeline.py"
        )
        text = auth.read_text(encoding="utf-8") + pipeline.read_text(encoding="utf-8")
        assert "current_outstanding_protocol" not in text

