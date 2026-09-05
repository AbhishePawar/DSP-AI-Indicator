"""Stage 1M — official attachment classification and issuer document discovery."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from dsp_platform.current_outstanding_protocol.ledger import (
    ExchangeCompletenessCorpus,
    attest_option_b_from_exchange_corpus,
    classify_exchange_event,
)
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.primary_source_retrieval.extraction import extract_paid_up_equity_shares
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)
from dsp_platform.share_count_acquisition.attachments import (
    enrich_unresolved_announcements,
    official_attachment_url,
    retrieve_official_document,
)
from dsp_platform.share_count_acquisition.issuer import (
    IssuerEvidenceSource,
    extract_outstanding_observation,
)
from dsp_platform.share_count_acquisition.issuer_documents import (
    discover_issuer_document_urls,
)
from dsp_platform.share_count_acquisition.live_http import AllowlistedLiveJsonHttp
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionResult
from dsp_platform.share_count_acquisition.nse import acquire_nse_disclosures
from dsp_platform.share_count_acquisition.universe import (
    PredecessorIsin,
    get_listed_equity,
)
from dsp_platform.share_count_acquisition.http import RecordedJsonHttp
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionRequest
from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.external_evidence.models import SourceTier, SourceType

_HORIZON = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
_AS_OF = date(2026, 6, 30)
_SEBI_CASH = (
    "7. Consideration - whether cash consideration or share swap or any other "
    "form and details of the same Cash consideration. The acquisition of 100% "
    "of equity shares of the target is expected to be completed within 3-4 months."
)
_SEBI_SHARE = (
    "7. Consideration - whether cash consideration or share swap or any other "
    "form and details of the same Share swap. Allotment of equity shares of the "
    "company as consideration."
)
_SEBI_MIXED = (
    "Consideration is a combination of cash and share consideration. "
    "New shares will be issued as part consideration."
)


class FakeBytesHttp:
    def __init__(self, pages: dict[str, dict]) -> None:
        self._pages = pages
        self.calls: list[str] = []

    def get_bytes(self, url: str, **kwargs: object) -> dict:
        del kwargs
        self.calls.append(url)
        if url in self._pages:
            return self._pages[url]
        return {
            "ok": False,
            "status": None,
            "body": None,
            "content_type": "",
            "error": "missing fixture",
        }


def _identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="SYNTH",
        exchange="NSE",
        mic="XNSE",
        isin="INE999Z01019",
        issuer="SYNTHETIC — NOT PRODUCTION DATA",
    )


def _source() -> IssuerEvidenceSource:
    return IssuerEvidenceSource(
        identity=_identity(),
        ir_url="https://fixtures.dsp.test/synthetic/outstanding",
        issuer_name="SYNTHETIC — NOT PRODUCTION DATA",
    )


def _document(text: str) -> RetrievedPrimarySourceDocument:
    identity = _identity()
    return RetrievedPrimarySourceDocument(
        identity=ExternalEvidenceIdentity(
            symbol=identity.symbol,
            exchange=identity.exchange,
            isin=identity.isin,
            company_name=identity.issuer,
            mic=identity.mic,
        ),
        locator="https://www.example-issuer.test/filing.pdf",
        document_type=PrimarySourceDocumentType.EXCHANGE_FILING,
        source_type=SourceType.FILING,
        source_tier=SourceTier.TIER_1_PRIMARY,
        retrieved_at=_HORIZON,
        text=text,
        publication_date=_AS_OF,
        as_of=None,
    )


class TestAcquisitionClassification:
    def test_cash_acquisition_from_official_attachment(self) -> None:
        kind, changes = classify_exchange_event(
            "Acquisition " + _SEBI_CASH
        )
        assert kind == "acquisition_cash"
        assert changes is False

    def test_share_acquisition(self) -> None:
        kind, changes = classify_exchange_event("Acquisition " + _SEBI_SHARE)
        assert kind == "acquisition_share_consideration"
        assert changes is True

    def test_mixed_acquisition(self) -> None:
        kind, changes = classify_exchange_event("Acquisition " + _SEBI_MIXED)
        assert kind == "acquisition_mixed_consideration"
        assert changes is True

    def test_unresolved_acquisition_without_terms(self) -> None:
        kind, changes = classify_exchange_event(
            "The issuer has informed the Exchange about Acquisition"
        )
        assert kind == "acquisition_unresolved"
        assert changes is None

    def test_form_question_alone_is_not_cash(self) -> None:
        kind, changes = classify_exchange_event(
            "Acquisition whether cash consideration or share swap or any other form"
        )
        assert kind == "acquisition_unresolved"
        assert changes is None

    def test_depository_certificate_is_non_capital(self) -> None:
        kind, changes = classify_exchange_event(
            "Certificate under SEBI (Depositories and Participants) Regulations, 2018"
        )
        assert kind == "non_capital_disclosure"
        assert changes is False

    def test_takeover_regulation_disclosure_is_not_an_acquisition(self) -> None:
        kind, changes = classify_exchange_event(
            "Disclosure under SEBI Takeover Regulations Regulation 31(4)"
        )
        assert kind == "non_capital_disclosure"
        assert changes is False

    def test_nature_of_consideration_cash(self) -> None:
        kind, changes = classify_exchange_event(
            "Acquisition 7. Nature of consideration Cash 8. Cost of acquisition"
        )
        assert kind == "acquisition_cash"
        assert changes is False

    def test_completed_acquisition_without_share_issue(self) -> None:
        kind, changes = classify_exchange_event(
            "The issuer Completes Acquisition of a target. The company has completed the acquisition."
        )
        assert kind == "acquisition_completion"
        assert changes is False

    def test_shareholders_meeting_is_non_capital(self) -> None:
        kind, changes = classify_exchange_event(
            "Shareholders meeting Notice of Annual General Meeting"
        )
        assert kind == "non_capital_disclosure"
        assert changes is False


class TestAttachmentRetrieval:
    def test_attchmnt_file_field_is_used(self) -> None:
        url = official_attachment_url(
            {
                "attchmntFile": (
                    "https://nsearchives.nseindia.com/corporate/SYNTH_acq.pdf"
                )
            }
        )
        assert url == "https://nsearchives.nseindia.com/corporate/SYNTH_acq.pdf"

    def test_untrusted_external_attachment_rejected(self) -> None:
        assert (
            official_attachment_url(
                {"attchmntFile": "https://evil.example/secret.pdf"}
            )
            is None
        )
        document = retrieve_official_document(
            "https://evil.example/secret.pdf",
            http=FakeBytesHttp({}),
            allowed_hosts=frozenset({"nsearchives.nseindia.com"}),
        )
        assert document.ok is False
        assert "allowlisted" in (document.error or "")

    def test_invalid_content_type_rejected(self) -> None:
        url = "https://nsearchives.nseindia.com/corporate/x.bin"
        http = FakeBytesHttp(
            {
                url: {
                    "ok": True,
                    "status": 200,
                    "content_type": "application/javascript",
                    "body": b"alert(1)",
                    "sha256": "abc",
                    "content_length": 8,
                    "retrieved_at": _HORIZON.isoformat(),
                }
            }
        )
        document = retrieve_official_document(url, http=http)
        assert document.ok is False
        assert "content type" in (document.error or "")

    def test_timeout_is_fail_closed(self) -> None:
        url = "https://nsearchives.nseindia.com/corporate/slow.pdf"
        http = FakeBytesHttp(
            {
                url: {
                    "ok": False,
                    "status": None,
                    "error": "timed out",
                    "body": None,
                    "content_type": "",
                    "retrieved_at": _HORIZON.isoformat(),
                }
            }
        )
        document = retrieve_official_document(url, http=http)
        assert document.ok is False
        assert "timed out" in (document.error or "")

    def test_oversized_document_rejected(self) -> None:
        url = "https://nsearchives.nseindia.com/corporate/big.pdf"
        http = FakeBytesHttp(
            {
                url: {
                    "ok": False,
                    "status": 200,
                    "truncated": True,
                    "body": None,
                    "content_type": "application/pdf",
                    "content_length": 4_000_000,
                    "retrieved_at": _HORIZON.isoformat(),
                }
            }
        )
        document = retrieve_official_document(url, http=http)
        assert document.ok is False
        assert "size" in (document.error or "")

    def test_enrichment_classifies_cash_from_attachment(self) -> None:
        url = "https://nsearchives.nseindia.com/corporate/acq.pdf"
        bundle = ExchangeAcquisitionResult(
            identity=_identity(),
            source_id="nse_public_api_connector",
            requested_start=_AS_OF,
            requested_end=date(2026, 9, 6),
            retrieved_at=_HORIZON,
            corporate_actions=(),
            announcements=(
                {
                    "symbol": "SYNTH",
                    "isin": "INE999Z01019",
                    "desc": "Acquisition",
                    "attchmntText": "informed the Exchange about Acquisition",
                    "attchmntFile": url,
                    "seq_id": "1",
                },
            ),
            pagination_exhausted=True,
            date_range_explicit=True,
            truncated=False,
            page_count=1,
            record_count=1,
            source_url="https://www.nseindia.com/api/corporate-announcements",
            evidence_reference="recorded",
            pages_fetched=1,
        )
        http = FakeBytesHttp(
            {
                url: {
                    "ok": True,
                    "status": 200,
                    "content_type": "text/plain",
                    "body": _SEBI_CASH.encode("utf-8"),
                    "sha256": "d" * 64,
                    "content_length": len(_SEBI_CASH),
                    "retrieved_at": _HORIZON.isoformat(),
                }
            }
        )
        enriched = enrich_unresolved_announcements(bundle, http=http)
        text = enriched.announcements[0]["attachment_text"]
        kind, changes = classify_exchange_event(
            "Acquisition " + text
        )
        assert kind == "acquisition_cash"
        assert changes is False
        assert enriched.announcements[0]["attachment_sha256"] == "d" * 64


class TestIssuerExtraction:
    def test_explicit_outstanding_sentence(self) -> None:
        observation = extract_outstanding_observation(
            _source(),
            document_text=(
                "As of June 30, 2026, issued and outstanding shares were "
                "1,000,000,001 shares."
            ),
            retrieved_at=_HORIZON,
            publication_at=_AS_OF,
        )
        assert observation is not None
        assert observation.shares_outstanding == Decimal("1000000001")
        assert observation.as_of == _AS_OF

    def test_indian_grouping_outstanding(self) -> None:
        observation = extract_outstanding_observation(
            _source(),
            document_text=(
                "As of June 30, 2026, issued and outstanding shares were "
                "3,61,80,87,518 shares."
            ),
            retrieved_at=_HORIZON,
            publication_at=_AS_OF,
        )
        assert observation is not None
        assert observation.shares_outstanding == Decimal("3618087518")

    def test_filing_issued_and_outstanding_net_of_treasury(self) -> None:
        text = (
            "Share capital - par value 480,00,00,000 equity shares\n"
            "authorized, issued and outstanding 404,96,45,811 (404,69,40,812) equity shares\n"
            "fully paid up, net of 79,33,019 treasury shares as at June 30, 2026\n"
        )
        observation = extract_outstanding_observation(
            _source(),
            document_text=text,
            retrieved_at=_HORIZON,
            publication_at=_AS_OF,
        )
        assert observation is not None
        assert observation.shares_outstanding == Decimal("4049645811")
        assert observation.as_of == _AS_OF

    def test_weighted_average_rejected(self) -> None:
        assert (
            extract_outstanding_observation(
                _source(),
                document_text=(
                    "Weighted-average shares outstanding were 1,000,000,001 "
                    "as of June 30, 2026."
                ),
                retrieved_at=_HORIZON,
            )
            is None
        )

    def test_float_rejected(self) -> None:
        assert (
            extract_outstanding_observation(
                _source(),
                document_text=(
                    "Free float shares outstanding were 1,000 shares "
                    "as of June 30, 2026."
                ),
                retrieved_at=_HORIZON,
            )
            is None
        )

    def test_ambiguous_number_of_shares_rejected(self) -> None:
        assert (
            extract_outstanding_observation(
                _source(),
                document_text="Number of shares 4,151,256,108 as of June 30, 2026.",
                retrieved_at=_HORIZON,
            )
            is None
        )

    def test_paid_up_capital_derivation(self) -> None:
        text = (
            "As of June 30, 2026 the company has issued and fully paid equity shares. "
            "Paid-up equity share capital of the company is Rs. 10000000. "
            "Face value of Rs. 10."
        )
        record = extract_paid_up_equity_shares(_document(text))
        assert record is not None
        assert record.numeric_value == 1_000_000
        assert "derived outstanding" in (record.evidence_reference or "").lower()
        observation = extract_outstanding_observation(
            _source(),
            document_text=text,
            retrieved_at=_HORIZON,
            publication_at=_AS_OF,
        )
        assert observation is not None
        assert observation.shares_outstanding == Decimal("1000000")

    def test_paid_up_rejected_when_partly_paid(self) -> None:
        text = (
            "As of June 30, 2026 issued and fully paid. "
            "Paid-up equity share capital of Rs. 10000000. "
            "Face value of Rs. 10. Partly paid shares remain outstanding."
        )
        assert extract_paid_up_equity_shares(_document(text)) is None

    def test_landing_page_vs_filing_hrefs(self) -> None:
        html = """
        <a href="/investors/share-details.html">Number of shares</a>
        <a href="/investors/reports-filings/quarterly-results/q1-finstatement.pdf">
          Financial statements
        </a>
        <a href="https://evil.example/report.pdf">External report</a>
        """
        urls = discover_issuer_document_urls(
            html,
            base_url="https://www.issuer.test/investors/",
            allowed_hosts=frozenset({"www.issuer.test", "issuer.test"}),
        )
        assert any(item.endswith("q1-finstatement.pdf") for item in urls)
        assert all("evil.example" not in item for item in urls)


class TestPredecessorIsin:
    def test_valid_predecessor_accepted(self) -> None:
        hdfc = get_listed_equity("INE040A01034", "XNSE")
        assert hdfc is not None
        assert "INE040A01018" in hdfc.equivalent_isins(date(2026, 9, 6))
        identity = hdfc.identity
        http = RecordedJsonHttp(
            {
                "corporate-announcements": [
                    {
                        "symbol": "HDFCBANK",
                        "sm_isin": "INE040A01018",
                        "desc": "General Updates",
                    }
                ],
                "corporateActions": [],
            }
        )
        accepted = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=date(2026, 1, 1),
                end=date(2026, 9, 6),
                retrieved_at=_HORIZON,
                equivalent_isins=hdfc.equivalent_isins(date(2026, 9, 6)),
            ),
            http,
        )
        assert accepted.record_count == 1

    def test_wrong_predecessor_rejected(self) -> None:
        identity = InstrumentIdentity(
            symbol="HDFCBANK",
            exchange="NSE",
            mic="XNSE",
            isin="INE040A01034",
            issuer="HDFC Bank Limited",
        )
        http = RecordedJsonHttp(
            {
                "corporate-announcements": [
                    {
                        "symbol": "HDFCBANK",
                        "sm_isin": "INE009A01021",
                        "desc": "General Updates",
                    }
                ],
                "corporateActions": [],
            }
        )
        rejected = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=date(2026, 1, 1),
                end=date(2026, 9, 6),
                retrieved_at=_HORIZON,
                equivalent_isins=("INE040A01018",),
            ),
            http,
        )
        assert rejected.record_count == 0

    def test_different_issuer_symbol_rejected(self) -> None:
        identity = InstrumentIdentity(
            symbol="HDFCBANK",
            exchange="NSE",
            mic="XNSE",
            isin="INE040A01034",
            issuer="HDFC Bank Limited",
        )
        http = RecordedJsonHttp(
            {
                "corporate-announcements": [
                    {
                        "symbol": "INFY",
                        "sm_isin": "INE040A01018",
                        "desc": "General Updates",
                    }
                ],
                "corporateActions": [],
            }
        )
        rejected = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=date(2026, 1, 1),
                end=date(2026, 9, 6),
                retrieved_at=_HORIZON,
                equivalent_isins=("INE040A01018",),
            ),
            http,
        )
        assert rejected.record_count == 0

    def test_expired_predecessor_inactive(self) -> None:
        row = PredecessorIsin(
            isin="INE040A01018",
            effective_until=date(2020, 1, 1),
        )
        assert row.active_on(date(2019, 12, 31)) is True
        assert row.active_on(date(2026, 9, 6)) is False

    def test_option_b_accepts_predecessor_isin(self) -> None:
        identity = ExternalEvidenceIdentity(
            symbol="HDFCBANK",
            exchange="NSE",
            isin="INE040A01034",
            company_name="HDFC Bank Limited",
            mic="XNSE",
        )
        corpus = ExchangeCompletenessCorpus(
            identity=identity,
            share_count_as_of=_AS_OF,
            requested_start=_AS_OF,
            requested_end=date(2026, 9, 6),
            retrieved_at=_HORIZON,
            pagination_exhausted=True,
            date_range_explicit=True,
            source_tier="TIER_1_PRIMARY",
            source_url="https://www.nseindia.com/api/corporates-corporateActions",
            evidence_reference="recorded predecessor identity",
            corporate_actions=(
                {
                    "symbol": "HDFCBANK",
                    "isin": "INE040A01018",
                    "subject": "Interim Dividend - Rs 1",
                    "exDate": "15-Jul-2026",
                    "comp": "HDFC Bank Limited",
                },
            ),
            announcements=(),
            equivalent_isins=("INE040A01018",),
        )
        assert attest_option_b_from_exchange_corpus(corpus).proven is True


class TestSecurity:
    def test_live_http_rejects_private_and_localhost(self) -> None:
        client = AllowlistedLiveJsonHttp()
        assert client.get_bytes("http://127.0.0.1/")["ok"] is False
        assert client.get_bytes("https://localhost/secret")["ok"] is False
        blob = " ".join(
            str(row.get("error") or "") for row in client.public_traces()
        ).lower()
        assert "https" in blob or "blocked" in blob or "localhost" in blob
        encoded = str(client.public_traces()).lower()
        assert "cookie" not in encoded
        assert "authorization" not in encoded

    def test_wrong_mic_catalog_lookup(self) -> None:
        assert get_listed_equity("INE467B01029", "XNAS") is None
        assert get_listed_equity("INE467B01029", "XNSE") is not None


@pytest.mark.skipif(os.environ.get("DSP_LIVE_T1") != "1", reason="live T1 opt-in")
def test_live_universe_opt_in_stage_1m() -> None:
    from dsp_platform.share_count_acquisition.operator import acquire_universe

    runs = acquire_universe(lookup_horizon=datetime.now(tz=UTC), fetch_issuer=True)
    assert len(runs) >= 5
    assert all(run.production_written is False for run in runs)
    tcs = next(run for run in runs if run.identity.isin == "INE467B01029")
    assert tcs.state.value in {"CURRENT", "VALIDATED", "REFRESH_PENDING"}
