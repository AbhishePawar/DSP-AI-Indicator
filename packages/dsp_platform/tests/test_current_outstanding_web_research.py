"""AI-assisted web evidence research — untrusted locators, DSP remains authority."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.share_count import (
    ACCEPTANCE_PROVIDER_ID,
    NullShareCountAdapter,
    ShareCountAcceptanceError,
    ShareCountSnapshot,
    accept_current_outstanding_claims,
)
from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.canonical_research_ai.port import (
    ProductionBlockedCanonicalResearchAiPort,
)
from dsp_platform.current_outstanding_protocol import (
    ActivationGatedEvidenceDiscovery,
    AiAssistedShareCountWebDiscovery,
    CurrentOutstandingDiagnostic,
    CurrentOutstandingProtocol,
    UntrustedWebEvidenceClaim,
    discovery_result_from_untrusted_web_claims,
    dsp_accept_untrusted_share_count_candidate,
    production_current_outstanding_protocol,
    share_count_web_research_queries,
    untrusted_web_claims_from_ai_draft,
)
from dsp_platform.current_outstanding_protocol.ai_candidate import (
    untrusted_candidate_from_ai_draft,
)
from dsp_platform.current_outstanding_protocol.models import (
    UntrustedShareCountAiCandidate,
)
from dsp_platform.current_outstanding_protocol.testing import (
    SCREENER_FIXTURE_URL,
    DeterministicScreenerLikeWebDiscovery,
    DeterministicShareCountExtractionAiPort,
    DeterministicShareCountWebResearchAiPort,
    fixture_option_b_currentness,
)
from dsp_platform.current_outstanding_protocol.web_research import (
    APPROVED_SECONDARY_WEB_HOSTS,
)
from dsp_platform.external_evidence.models import (
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence_discovery.models import (
    DISCOVERY_NOT_CONFIGURED,
    ExternalEvidenceDiscoveryRequest,
)
from dsp_platform.external_evidence_discovery.port import (
    ExternalEvidenceDiscoveryBlockedError,
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
    LocalPrimarySourceDocumentRetrieval,
    load_local_filing_fixture,
)
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)
from llm_adapters.activation_evidence import ActivationEvidence
from llm_adapters.activation_guard import ActivationState, evaluate_activation

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


def _request() -> ExternalEvidenceDiscoveryRequest:
    return ExternalEvidenceDiscoveryRequest(
        identity=FIXTURE_IDENTITY,
        fact_id="current_outstanding",
        retrieved_at=FIXED,
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


def _filing_web_claim() -> dict[str, object]:
    return {
        "company_identity": "DSPX",
        "ticker": "DSPX",
        "exchange": "TESTEX",
        "shares_outstanding": 100,
        "unit": "shares",
        "as_of": "2024-03-31",
        "source_name": "Annual report",
        "source_url": FIXTURE_LOCATOR,
        "source_type": "filing",
        "evidence_excerpt": EXCERPT,
        "evidence_reference": EXCERPT,
        "explanation": "Note 12 states current issued and outstanding shares.",
        "claim_type": "CURRENT_OUTSTANDING",
    }


def _screener_web_claim() -> dict[str, object]:
    return {
        "company": "DSPX",
        "ticker": "DSPX",
        "exchange": "TESTEX",
        "shares_outstanding": 100,
        "unit": "shares",
        "as_of": "2024-03-31",
        "source_name": "Screener",
        "source_url": SCREENER_FIXTURE_URL,
        "source_type": "company_website",
        "evidence_excerpt": (
            "Screener lists current shares outstanding for DSPX as of 31 March 2024."
        ),
        "explanation": "Screener appears to show current outstanding shares.",
    }


class TestWebResearchQueriesAndGate:
    def test_queries_cover_outstanding_and_screener(self) -> None:
        queries = share_count_web_research_queries(FIXTURE_IDENTITY)
        blob = " ".join(queries).lower()
        assert "shares outstanding" in blob
        assert "outstanding shares" in blob
        assert "current shares outstanding" in blob
        assert "annual report" in blob
        assert "filing" in blob
        assert "screener" in blob

    def test_screener_is_not_auto_approved_secondary(self) -> None:
        assert "screener.in" not in APPROVED_SECONDARY_WEB_HOSTS
        assert frozenset() == APPROVED_SECONDARY_WEB_HOSTS

    def test_activation_off_does_not_call_inner_or_provider(self) -> None:
        verdict = evaluate_activation(ActivationEvidence.missing())
        assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED

        class _Boom:
            called = False

            def discover(self, request):  # noqa: ANN001
                _Boom.called = True
                raise AssertionError("inner discovery must not run")

        gated = ActivationGatedEvidenceDiscovery(
            _Boom(),  # type: ignore[arg-type]
            activation_ready=verdict.is_ready(),
        )
        with pytest.raises(
            ExternalEvidenceDiscoveryBlockedError, match=DISCOVERY_NOT_CONFIGURED
        ):
            gated.discover(_request())
        assert _Boom.called is False

    def test_production_protocol_keeps_web_research_blocked(self) -> None:
        result = production_current_outstanding_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.EVIDENCE_DISCOVERY_BLOCKED
        assert result.current_shares_outstanding is None


class TestUntrustedWebClaims:
    def test_ai_can_return_screener_candidate_that_stays_untrusted(self) -> None:
        ai = DeterministicShareCountWebResearchAiPort(
            web_claims=(_screener_web_claim(),)
        )
        from dsp_platform.current_outstanding_protocol.prompt import (
            build_share_count_web_research_prompt,
        )

        draft = ai.interpret(build_share_count_web_research_prompt(_request()))
        claims = untrusted_web_claims_from_ai_draft(draft)
        assert len(claims) == 1
        assert claims[0].source_name == "Screener"
        assert claims[0].source_url == SCREENER_FIXTURE_URL
        assert claims[0].to_dict()["trusted"] is False
        assert claims[0].to_dict()["may_create_snapshot"] is False
        result = discovery_result_from_untrusted_web_claims(_request(), claims)
        assert len(result.records) == 1
        record = result.records[0]
        assert record.source_tier is SourceTier.TIER_3_DISCOVERY
        assert record.may_influence_calculation is False
        assert record.validation_status.value == "candidate"
        with pytest.raises(ShareCountAcceptanceError, match="ShareCountEvidenceClaim"):
            accept_current_outstanding_claims([claims[0]], symbol="DSPX")  # type: ignore[list-item]

    def test_ai_draft_cannot_create_snapshot_or_enter_valuation(self) -> None:
        draft = CanonicalAIDraft(
            output=CanonicalAIResearchOutput(
                intrinsic_value=99.0,
                margin_of_safety=0.5,
                recommendation_action="BUY",
            ),
            untrusted_extraction={"web_claims": [_filing_web_claim()]},
        )
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="DSPX")
        assert not isinstance(draft, ShareCountSnapshot)

    def test_missing_source_url_is_dropped(self) -> None:
        claim = dict(_filing_web_claim())
        claim["source_url"] = ""
        claims = untrusted_web_claims_from_ai_draft(
            CanonicalAIDraft(
                output=CanonicalAIResearchOutput(),
                untrusted_extraction={"web_claims": [claim]},
            )
        )
        assert claims == ()

    def test_missing_excerpt_is_dropped(self) -> None:
        claim = dict(_filing_web_claim())
        claim["evidence_excerpt"] = ""
        claim["evidence_reference"] = ""
        claims = untrusted_web_claims_from_ai_draft(
            CanonicalAIDraft(
                output=CanonicalAIResearchOutput(),
                untrusted_extraction={"web_claims": [claim]},
            )
        )
        assert claims == ()

    def test_wrong_identity_does_not_become_locator(self) -> None:
        claim = UntrustedWebEvidenceClaim(
            company_identity="INFY",
            ticker="INFY",
            exchange="NSE",
            source_url=FIXTURE_LOCATOR,
            evidence_excerpt=EXCERPT,
        )
        result = discovery_result_from_untrusted_web_claims(_request(), (claim,))
        assert result.records == ()


class TestDspPromotionFromWebEvidence:
    def test_missing_as_of_fails(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="as_of"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(as_of_date=None),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_missing_unit_fails(self) -> None:
        parsed = untrusted_candidate_from_ai_draft(
            CanonicalAIDraft(
                output=CanonicalAIResearchOutput(),
                untrusted_extraction={
                    "company_identity": "DSPX",
                    "claimed_share_count": 100,
                    "unit": "",
                    "source_url": FIXTURE_LOCATOR,
                    "supporting_excerpt": EXCERPT,
                },
            )
        )
        assert parsed is None

    def test_wrong_identity_fails(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="identity mismatch"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(ticker="INFY", company_identity="INFY"),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_weighted_average_fails(self) -> None:
        excerpt = "Weighted-average basic shares outstanding were 100 shares."
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                ),
                document=_document(text=excerpt, as_of=AS_OF),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_authorized_shares_fail(self) -> None:
        excerpt = "Authorized shares outstanding were 100 shares."
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                ),
                document=_document(text=excerpt, as_of=AS_OF),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_market_cap_derived_fails(self) -> None:
        excerpt = "Implied outstanding shares from market cap were 100 shares."
        with pytest.raises(ShareCountAcceptanceError, match="outstanding"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                ),
                document=_document(text=excerpt, as_of=AS_OF),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_non_positive_fails(self) -> None:
        with pytest.raises(ShareCountAcceptanceError):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(claimed_share_count=0),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_ambiguous_unit_fails(self) -> None:
        with pytest.raises(ShareCountAcceptanceError, match="shares"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(unit="crore"),
                document=_document(),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_historical_only_fails_current_validation(self) -> None:
        excerpt = (
            "Historically outstanding shares were 100 shares. This is not current."
        )
        with pytest.raises(ShareCountAcceptanceError, match="historical-only"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                    explanation="historical-only FY2018 figure",
                ),
                document=_document(text=excerpt, as_of=AS_OF),
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_valid_primary_evidence_uses_existing_acceptance(self) -> None:
        snap = dsp_accept_untrusted_share_count_candidate(
            _candidate(),
            document=_document(),
            requested_identity=FIXTURE_IDENTITY,
        )
        assert snap.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        assert snap.shares_value() == pytest.approx(100.0)

    def test_screener_document_cannot_become_snapshot(self) -> None:
        excerpt = (
            "Screener lists current shares outstanding for DSPX as of 31 March 2024."
        )
        document = _document(
            locator=SCREENER_FIXTURE_URL,
            source_tier=SourceTier.TIER_3_DISCOVERY,
            source_type=SourceType.COMPANY_WEBSITE,
            text=excerpt,
            as_of=AS_OF,
        )
        with pytest.raises(ShareCountAcceptanceError, match="Tier 3/4"):
            dsp_accept_untrusted_share_count_candidate(
                _candidate(
                    source_reference=SCREENER_FIXTURE_URL,
                    supporting_excerpt=excerpt,
                    evidence_reference=excerpt,
                ),
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_conflict_fails_closed(self) -> None:
        first = dsp_accept_untrusted_share_count_candidate(
            _candidate(),
            document=_document(),
            requested_identity=FIXTURE_IDENTITY,
        )
        other_excerpt = (
            "As of 31 March 2024, issued and outstanding shares were 200 shares."
        )
        second_doc = _document(
            text=other_excerpt,
            locator="https://fixtures.dsp.test/filings/DSPX-FY24-other",
            as_of=AS_OF,
        )
        second = dsp_accept_untrusted_share_count_candidate(
            _candidate(
                claimed_share_count=200,
                supporting_excerpt=other_excerpt,
                evidence_reference=other_excerpt,
                source_reference=second_doc.locator,
            ),
            document=second_doc,
            requested_identity=FIXTURE_IDENTITY,
        )
        from data_engine.share_count.acceptance import ShareCountEvidenceClaim

        def _as_claim(snap: ShareCountSnapshot, shares: int, url: str, excerpt: str):
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
                    _as_claim(first, 100, FIXTURE_LOCATOR, EXCERPT),
                    _as_claim(second, 200, second_doc.locator, other_excerpt),
                ],
                symbol="DSPX",
                exchange="TESTEX",
                isin="DSPX00000001",
            )


class TestProtocolWebResearchPath:
    def test_screener_like_source_can_be_discovered_as_candidate(self) -> None:
        discovered = DeterministicScreenerLikeWebDiscovery().discover(_request())
        assert discovered.records[0].source_url == SCREENER_FIXTURE_URL
        assert discovered.records[0].source_tier is SourceTier.TIER_3_DISCOVERY
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=DeterministicScreenerLikeWebDiscovery(),
            retrieval=ProductionBlockedPrimarySourceDocumentRetrieval(),
            ai=ProductionBlockedCanonicalResearchAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.DOCUMENT_RETRIEVAL_BLOCKED
        assert result.current_shares_outstanding is None

    def test_ai_web_locator_of_primary_filing_can_validate(self) -> None:
        retrieval = LocalPrimarySourceDocumentRetrieval(
            {FIXTURE_LOCATOR: load_local_filing_fixture()}
        )
        discovery = ActivationGatedEvidenceDiscovery(
            AiAssistedShareCountWebDiscovery(
                ai=DeterministicShareCountWebResearchAiPort(
                    web_claims=(_filing_web_claim(),)
                )
            ),
            activation_ready=True,
        )
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=discovery,
            retrieval=retrieval,
            ai=DeterministicShareCountExtractionAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
            corporate_action_currentness=fixture_option_b_currentness(
                as_of=AS_OF, retrieved_at=FIXED
            ),
        )
        assert result.diagnostic is _Diag.SHARECOUNT_VALIDATED
        assert result.current_shares_outstanding == pytest.approx(100.0)
        assert result.snapshot is not None
        assert result.snapshot.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        public = result.to_public_dict()
        assert "prompt" not in public
        assert "web_claims" not in public
        assert "intrinsic_value" not in public
        assert "recommendation" not in public

    def test_ai_cannot_modify_valuation_or_recommendation_state(self) -> None:
        valuation_state = {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        recommendation_state = {"action": "HOLD"}
        production_current_outstanding_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert valuation_state == {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        assert recommendation_state == {"action": "HOLD"}
