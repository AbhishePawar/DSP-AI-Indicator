"""Stage 1E Option B completeness: identity, ledger, and TCS acceptance."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.share_count import NullShareCountAdapter, ShareCountAcceptanceError
from dsp_platform.current_outstanding_protocol.currentness import (
    evaluate_option_b_currentness,
)
from dsp_platform.current_outstanding_protocol.ledger import (
    ExchangeCompletenessCorpus,
    attest_option_b_from_exchange_corpus,
    classify_exchange_event,
)
from dsp_platform.current_outstanding_protocol.models import CurrentOutstandingDiagnostic
from dsp_platform.current_outstanding_protocol.promotion import (
    dsp_accept_untrusted_share_count_candidate,
)
from dsp_platform.current_outstanding_protocol.protocol import CurrentOutstandingProtocol
from dsp_platform.current_outstanding_protocol.testing import (
    DeterministicShareCountExtractionAiPort,
)
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.primary_source_retrieval.testing import (
    LocalDocumentExternalEvidenceDiscovery,
    LocalPrimarySourceDocumentRetrieval,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_CORPUS = _FIXTURES / "tcs_nse_bse_corporate_action_corpus.json"
_TCS_FAQ = _FIXTURES / "primary_sources" / "TCS-IR-FAQ-outstanding-2026-06-30.txt"
_TCS_LOCATOR = "https://www.tcs.com/investor-relations/investor-faqs"
_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_AS_OF = date(2026, 6, 30)
_Diag = CurrentOutstandingDiagnostic

TCS_IDENTITY = ExternalEvidenceIdentity(
    symbol="TCS",
    exchange="NSE",
    isin="INE467B01029",
    company_name="Tata Consultancy Services",
    mic="XNSE",
)


def _tcs_instrument() -> Instrument:
    return Instrument(
        symbol="TCS",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange="NSE",
        isin="INE467B01029",
        name="Tata Consultancy Services",
    )


def _load_corpus(**overrides: object) -> ExchangeCompletenessCorpus:
    payload = json.loads(_CORPUS.read_text(encoding="utf-8"))
    payload.update(overrides)
    identity = TCS_IDENTITY
    return ExchangeCompletenessCorpus(
        identity=identity,
        share_count_as_of=_AS_OF,
        requested_start=date.fromisoformat(str(payload["requested_start"])),
        requested_end=date.fromisoformat(str(payload["requested_end"])),
        retrieved_at=_HORIZON,
        pagination_exhausted=bool(payload["pagination_exhausted"]),
        date_range_explicit=bool(payload["date_range_explicit"]),
        source_tier="TIER_1_PRIMARY",
        source_url=str(payload["source_url"]),
        evidence_reference=(
            "NSE corporates-corporateActions and corporate-announcements "
            "for TCS/INE467B01029 from 2026-06-30 to 2026-09-05, "
            "pagination exhausted, BSE AnnSubCategoryGetData cross-check."
        ),
        corporate_actions=tuple(payload["corporate_actions"]),
        announcements=tuple(payload["announcements"]),
    )


class TestExchangeEventClassification:
    def test_interim_dividend_does_not_change_outstanding(self) -> None:
        kind, changes = classify_exchange_event(
            "Interim Dividend - Rs 12 Per Share"
        )
        assert kind == "dividend"
        assert changes is False

    def test_cash_acquisition_does_not_change_outstanding(self) -> None:
        kind, changes = classify_exchange_event(
            "Acquisition Cash consideration. expected to be completed within 3-4 months."
        )
        assert kind == "acquisition_cash"
        assert changes is False

    def test_share_swap_acquisition_changes_outstanding(self) -> None:
        kind, changes = classify_exchange_event(
            "Acquisition consideration is share swap of issuer equity shares"
        )
        assert kind == "acquisition_share_consideration"
        assert changes is True

    def test_unclassified_acquisition_without_consideration(self) -> None:
        kind, changes = classify_exchange_event(
            "Tata Consultancy Services Limited has informed the Exchange about Acquisition"
        )
        assert kind == "acquisition_unresolved"
        assert changes is None

    def test_buyback_extinguishment_changes_outstanding(self) -> None:
        kind, changes = classify_exchange_event(
            "Buyback extinguishment of equity shares"
        )
        assert kind == "buyback_extinguishment"
        assert changes is True


class TestOptionBLedgerAttestation:
    def test_tcs_nse_bse_corpus_attests_through_retrieval_horizon(self) -> None:
        attestation = attest_option_b_from_exchange_corpus(_load_corpus())
        assert attestation.proven is True
        assert attestation.evidence is not None
        assert attestation.evidence.complete_through == date(2026, 9, 5)
        assert attestation.evidence.share_count_as_of == _AS_OF
        assert attestation.ledger[0].isin == "INE467B01029"
        assert attestation.ledger[0].event_type == "dividend"
        assert attestation.ledger[0].changes_outstanding_shares is False
        verdict = evaluate_option_b_currentness(
            share_count_as_of=_AS_OF,
            retrieved_at=_HORIZON,
            evidence=attestation.evidence,
        )
        assert verdict.proven is True

    def test_pagination_not_exhausted_is_unproven(self) -> None:
        corpus = replace(_load_corpus(), pagination_exhausted=False)
        attestation = attest_option_b_from_exchange_corpus(corpus)
        assert attestation.proven is False
        assert "pagination" in attestation.reason

    def test_date_range_not_explicit_is_unproven(self) -> None:
        corpus = replace(_load_corpus(), date_range_explicit=False)
        attestation = attest_option_b_from_exchange_corpus(corpus)
        assert attestation.proven is False
        assert "date range" in attestation.reason

    def test_stale_requested_end_is_unproven(self) -> None:
        corpus = replace(_load_corpus(), requested_end=date(2026, 8, 1))
        attestation = attest_option_b_from_exchange_corpus(corpus)
        assert attestation.proven is False
        assert "retrieved_at" in attestation.reason

    def test_wrong_isin_is_unproven(self) -> None:
        payload = json.loads(_CORPUS.read_text(encoding="utf-8"))
        actions = [dict(payload["corporate_actions"][0], isin="US87612E1064")]
        attestation = attest_option_b_from_exchange_corpus(
            _load_corpus(corporate_actions=actions)
        )
        assert attestation.proven is False
        assert "identity" in attestation.reason

    def test_unclassified_acquisition_blocks_completeness(self) -> None:
        payload = json.loads(_CORPUS.read_text(encoding="utf-8"))
        announcements = []
        for row in payload["announcements"]:
            item = dict(row)
            if item.get("desc") == "Acquisition":
                item.pop("filing_excerpt", None)
                item["attchmntText"] = (
                    "Tata Consultancy Services Limited has informed the Exchange about Acquisition"
                )
            announcements.append(item)
        attestation = attest_option_b_from_exchange_corpus(
            _load_corpus(announcements=announcements)
        )
        assert attestation.proven is False
        assert "not classified" in attestation.reason

    def test_later_bonus_blocks_option_b(self) -> None:
        payload = json.loads(_CORPUS.read_text(encoding="utf-8"))
        actions = list(payload["corporate_actions"])
        actions.append(
            {
                "symbol": "TCS",
                "isin": "INE467B01029",
                "comp": "Tata Consultancy Services Limited",
                "subject": "Bonus 1:1",
                "exDate": "01-Aug-2026",
            }
        )
        attestation = attest_option_b_from_exchange_corpus(
            _load_corpus(corporate_actions=actions)
        )
        assert attestation.proven is True
        assert attestation.evidence is not None
        verdict = evaluate_option_b_currentness(
            share_count_as_of=_AS_OF,
            retrieved_at=_HORIZON,
            evidence=attestation.evidence,
        )
        assert verdict.proven is False
        assert "later share-changing" in verdict.reason


class TestFloatAndWasRejection:
    def test_float_excerpt_is_rejected(self) -> None:
        from dsp_platform.current_outstanding_protocol.models import (
            UntrustedShareCountAiCandidate,
        )
        from dsp_platform.external_evidence.models import SourceTier, SourceType
        from dsp_platform.primary_source_retrieval.models import (
            PrimarySourceDocumentType,
            RetrievedPrimarySourceDocument,
        )

        excerpt = "Free-float shares outstanding were 3,618,087,518 shares."
        document = RetrievedPrimarySourceDocument(
            identity=TCS_IDENTITY,
            locator=_TCS_LOCATOR,
            document_type=PrimarySourceDocumentType.INVESTOR_RELATIONS,
            source_type=SourceType.COMPANY_WEBSITE,
            source_tier=SourceTier.TIER_1_PRIMARY,
            retrieved_at=_HORIZON,
            text=excerpt,
            as_of=_AS_OF,
        )
        with pytest.raises(ShareCountAcceptanceError):
            dsp_accept_untrusted_share_count_candidate(
                UntrustedShareCountAiCandidate(
                    company_identity="TCS",
                    claimed_share_count="3618087518",
                    unit="shares",
                    as_of_date=_AS_OF,
                    source_reference=_TCS_LOCATOR,
                    evidence_reference=excerpt,
                    supporting_excerpt=excerpt,
                    ticker="TCS",
                    exchange="NSE",
                    isin="INE467B01029",
                    mic="XNSE",
                ),
                document=document,
                requested_identity=TCS_IDENTITY,
            )

    def test_weighted_average_excerpt_is_rejected(self) -> None:
        from dsp_platform.current_outstanding_protocol.models import (
            UntrustedShareCountAiCandidate,
        )
        from dsp_platform.external_evidence.models import SourceTier, SourceType
        from dsp_platform.primary_source_retrieval.models import (
            PrimarySourceDocumentType,
            RetrievedPrimarySourceDocument,
        )

        excerpt = "Weighted average shares outstanding were 3,618,087,518 shares."
        document = RetrievedPrimarySourceDocument(
            identity=TCS_IDENTITY,
            locator=_TCS_LOCATOR,
            document_type=PrimarySourceDocumentType.INVESTOR_RELATIONS,
            source_type=SourceType.COMPANY_WEBSITE,
            source_tier=SourceTier.TIER_1_PRIMARY,
            retrieved_at=_HORIZON,
            text=excerpt,
            as_of=_AS_OF,
        )
        with pytest.raises(ShareCountAcceptanceError):
            dsp_accept_untrusted_share_count_candidate(
                UntrustedShareCountAiCandidate(
                    company_identity="TCS",
                    claimed_share_count="3618087518",
                    unit="shares",
                    as_of_date=_AS_OF,
                    source_reference=_TCS_LOCATOR,
                    evidence_reference=excerpt,
                    supporting_excerpt=excerpt,
                    ticker="TCS",
                    exchange="NSE",
                    isin="INE467B01029",
                    mic="XNSE",
                ),
                document=document,
                requested_identity=TCS_IDENTITY,
            )


class TestTcsOptionBAcceptance:
    def test_tcs_faq_plus_exchange_corpus_validates_current_outstanding(self) -> None:
        text = _TCS_FAQ.read_text(encoding="utf-8")
        retrieval = LocalPrimarySourceDocumentRetrieval({_TCS_LOCATOR: text})
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=LocalDocumentExternalEvidenceDiscovery(
                retrieval, locator=_TCS_LOCATOR
            ),
            retrieval=retrieval,
            ai=DeterministicShareCountExtractionAiPort(),
        )
        attestation = attest_option_b_from_exchange_corpus(_load_corpus())
        assert attestation.evidence is not None
        result = protocol.resolve(
            _tcs_instrument(),
            identity=TCS_IDENTITY,
            retrieved_at=_HORIZON,
            locator=_TCS_LOCATOR,
            corporate_action_currentness=attestation.evidence,
        )
        assert result.diagnostic is _Diag.SHARECOUNT_VALIDATED
        assert result.snapshot is not None
        assert result.snapshot.isin == "INE467B01029"
        assert result.snapshot.exchange == "NSE"
        assert result.current_shares_outstanding == pytest.approx(3618087518.0)
        assert result.snapshot.as_of is not None
        assert result.snapshot.as_of.date() == _AS_OF

    def test_production_factory_still_blocked(self) -> None:
        from dsp_platform.current_outstanding_protocol import (
            production_current_outstanding_protocol,
        )
        from dsp_platform.primary_source_retrieval.port import (
            ProductionBlockedPrimarySourceDocumentRetrieval,
        )

        protocol = production_current_outstanding_protocol()
        result = protocol.resolve(
            _tcs_instrument(),
            identity=TCS_IDENTITY,
            retrieved_at=_HORIZON,
            corporate_action_currentness=attest_option_b_from_exchange_corpus(
                _load_corpus()
            ).evidence,
        )
        assert isinstance(
            protocol._retrieval,  # noqa: SLF001
            ProductionBlockedPrimarySourceDocumentRetrieval,
        )
        assert result.snapshot is None
        assert result.diagnostic in {
            _Diag.EVIDENCE_DISCOVERY_BLOCKED,
            _Diag.DOCUMENT_RETRIEVAL_BLOCKED,
        }
