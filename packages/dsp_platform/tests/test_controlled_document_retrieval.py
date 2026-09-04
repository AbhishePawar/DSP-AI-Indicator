"""Controlled HTTPS document retrieval — fixtures only, no live internet."""

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
from data_engine.share_count.acceptance import ShareCountEvidenceClaim
from dsp_platform.controlled_document_retrieval import (
    SCREENER_WEB_HOSTS,
    TIER_1_WEB_HOSTS,
    ControlledHttpsDocumentRetrieval,
    source_tier_for_host,
)
from dsp_platform.controlled_document_retrieval.ssrf import (
    assert_public_https_locator,
)
from dsp_platform.controlled_document_retrieval.testing import (
    FakeDocumentTransport,
    FakeHop,
    public_resolver,
)
from dsp_platform.current_outstanding_protocol import (
    CurrentOutstandingDiagnostic,
    CurrentOutstandingProtocol,
    dsp_accept_untrusted_share_count_candidate,
    production_current_outstanding_protocol,
)
from dsp_platform.current_outstanding_protocol.models import (
    UntrustedShareCountAiCandidate,
)
from dsp_platform.current_outstanding_protocol.testing import (
    DeterministicScreenerLikeWebDiscovery,
    DeterministicShareCountExtractionAiPort,
)
from dsp_platform.external_evidence import (
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import (
    ExternalEvidenceDiscoveryBlockedError,
    ProductionBlockedExternalEvidenceDiscovery,
)
from dsp_platform.primary_source_retrieval import (
    DocumentRetrievalBlockedError,
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
    ProductionBlockedPrimarySourceDocumentRetrieval,
)
from dsp_platform.primary_source_retrieval.testing import (
    FIXTURE_IDENTITY,
    FIXTURE_LOCATOR,
    load_local_filing_fixture,
)
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)
from llm_adapters.activation_evidence import ActivationEvidence
from llm_adapters.activation_guard import ActivationState, evaluate_activation

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
AS_OF = "2024-03-31"
EXCERPT = "As of 31 March 2024, issued and outstanding shares were 100 shares."
HTML = f"<html><body><p>{EXCERPT}</p></body></html>"
SCREENER_URL = "https://www.screener.in/company/DSPX/"
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


def _request(locator: str = FIXTURE_LOCATOR) -> PrimarySourceDocumentRequest:
    return PrimarySourceDocumentRequest(
        identity=FIXTURE_IDENTITY,
        locator=locator,
        document_type=PrimarySourceDocumentType.ANNUAL_REPORT,
        fact_id="current_outstanding",
        retrieved_at=FIXED,
    )


def _retrieval(
    hops: dict[str, FakeHop],
    *,
    tier_1_hosts: frozenset[str] | None = None,
    resolver=public_resolver,
) -> ControlledHttpsDocumentRetrieval:
    return ControlledHttpsDocumentRetrieval(
        transport=FakeDocumentTransport(hops),
        resolver=resolver,
        tier_1_hosts=tier_1_hosts,
    )


def _private_resolver(_host: str, _port: int, *args: object, **kwargs: object):
    del args, kwargs
    return [(2, 1, 6, "", ("10.0.0.8", 443))]


def _loopback_resolver(_host: str, _port: int, *args: object, **kwargs: object):
    del args, kwargs
    return [(2, 1, 6, "", ("127.0.0.1", 443))]


class TestSsrfAndLocatorPolicy:
    def test_https_fixture_url_is_accepted_before_fetch(self) -> None:
        assert assert_public_https_locator(FIXTURE_LOCATOR) == "fixtures.dsp.test"

    def test_http_scheme_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="https"):
            assert_public_https_locator("http://fixtures.dsp.test/filings/x")

    def test_ftp_scheme_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="http/https"):
            assert_public_https_locator("ftp://fixtures.dsp.test/filings/x")

    def test_file_scheme_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="http/https"):
            assert_public_https_locator("file:///etc/passwd")

    def test_localhost_rejected_before_transport(self) -> None:
        transport = FakeDocumentTransport({})
        retrieval = ControlledHttpsDocumentRetrieval(
            transport=transport,
            resolver=public_resolver,
        )
        with pytest.raises(ExternalEvidenceValidationError, match="blocked hostname"):
            retrieval.retrieve(_request("https://localhost/secret"))
        assert transport.fetched == []

    def test_loopback_ip_rejected(self) -> None:
        with pytest.raises(
            ExternalEvidenceValidationError, match="private or non-public"
        ):
            ControlledHttpsDocumentRetrieval(
                transport=FakeDocumentTransport({}),
                resolver=public_resolver,
            ).retrieve(_request("https://127.0.0.1/"))

    def test_loopback_dns_resolution_rejected(self) -> None:
        with pytest.raises(
            ExternalEvidenceValidationError, match="private or non-public"
        ):
            _retrieval(
                {FIXTURE_LOCATOR: FakeHop(body=HTML.encode("utf-8"))},
                resolver=_loopback_resolver,
            ).retrieve(_request())

    def test_private_dns_resolution_rejected(self) -> None:
        with pytest.raises(
            ExternalEvidenceValidationError, match="private or non-public"
        ):
            _retrieval(
                {FIXTURE_LOCATOR: FakeHop(body=HTML.encode("utf-8"))},
                resolver=_private_resolver,
            ).retrieve(_request())

    def test_documentation_net_resolution_rejected(self) -> None:
        def _docs_net(_host: str, _port: int, *args: object, **kwargs: object):
            del args, kwargs
            return [(2, 1, 6, "", ("203.0.113.10", 443))]

        with pytest.raises(
            ExternalEvidenceValidationError, match="private or non-public"
        ):
            _retrieval(
                {FIXTURE_LOCATOR: FakeHop(body=HTML.encode("utf-8"))},
                resolver=_docs_net,
            ).retrieve(_request())

    def test_link_local_ipv6_resolution_rejected(self) -> None:
        def _link_local(_host: str, _port: int, *args: object, **kwargs: object):
            del args, kwargs
            return [(10, 1, 6, "", ("fe80::1", 443, 0, 0))]

        with pytest.raises(
            ExternalEvidenceValidationError, match="private or non-public"
        ):
            _retrieval(
                {FIXTURE_LOCATOR: FakeHop(body=HTML.encode("utf-8"))},
                resolver=_link_local,
            ).retrieve(_request())

    def test_metadata_link_local_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError):
            ControlledHttpsDocumentRetrieval(
                transport=FakeDocumentTransport({}),
                resolver=public_resolver,
            ).retrieve(_request("https://169.254.169.254/latest/meta-data"))

    def test_non_443_port_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="port 443"):
            assert_public_https_locator("https://fixtures.dsp.test:8443/x")

    def test_ipv6_loopback_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError):
            ControlledHttpsDocumentRetrieval(
                transport=FakeDocumentTransport({}),
                resolver=public_resolver,
            ).retrieve(_request("https://[::1]/secret"))

    def test_metadata_hostname_rejected(self) -> None:
        transport = FakeDocumentTransport({})
        retrieval = ControlledHttpsDocumentRetrieval(
            transport=transport,
            resolver=public_resolver,
        )
        with pytest.raises(ExternalEvidenceValidationError, match="blocked hostname"):
            retrieval.retrieve(_request("https://metadata.google.internal/"))
        assert transport.fetched == []

    def test_credentials_in_url_rejected(self) -> None:
        with pytest.raises(ExternalEvidenceValidationError, match="credentials"):
            assert_public_https_locator(
                "https://user:token@fixtures.dsp.test/filings/x"
            )

    def test_crlf_in_locator_rejected(self) -> None:
        with pytest.raises(
            ExternalEvidenceValidationError, match="control characters"
        ):
            assert_public_https_locator(
                "https://fixtures.dsp.test/filings/x\r\nX-Injected: 1"
            )


class TestControlledRetrieval:
    def test_valid_https_html_preserves_provenance(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=HTML.encode("utf-8"),
                headers={"content-type": "text/html; charset=utf-8"},
            )
        }
        document = _retrieval(hops).retrieve(_request())
        assert document.locator == FIXTURE_LOCATOR
        assert document.requested_locator == FIXTURE_LOCATOR
        assert document.final_locator == FIXTURE_LOCATOR
        assert document.hostname == "fixtures.dsp.test"
        assert document.retrieval_status == "retrieved"
        assert EXCERPT in document.text
        assert document.source_tier is SourceTier.TIER_3_DISCOVERY
        payload = document.to_dict()
        assert payload["requested_locator"] == FIXTURE_LOCATOR
        assert "text" not in payload

    def test_same_host_redirect_is_followed(self) -> None:
        dest = f"{FIXTURE_LOCATOR}-final"
        hops = {
            FIXTURE_LOCATOR: FakeHop(status_code=302, location=dest),
            dest: FakeHop(
                body=HTML.encode("utf-8"),
                headers={"content-type": "text/html"},
            ),
        }
        transport = FakeDocumentTransport(hops)
        document = ControlledHttpsDocumentRetrieval(
            transport=transport,
            resolver=public_resolver,
        ).retrieve(_request())
        assert document.locator == FIXTURE_LOCATOR
        assert document.final_locator == dest
        assert transport.fetched == [FIXTURE_LOCATOR, dest]

    def test_cross_host_redirect_is_source_mismatch(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                status_code=302,
                location="https://evil.example/steal",
            )
        }
        with pytest.raises(ExternalEvidenceValidationError, match="source mismatch"):
            _retrieval(hops).retrieve(_request())

    def test_http_redirect_is_rejected(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                status_code=302,
                location="http://fixtures.dsp.test/filings/insecure",
            )
        }
        with pytest.raises(ExternalEvidenceValidationError, match="https"):
            _retrieval(hops).retrieve(_request())

    def test_too_many_redirects_rejected(self) -> None:
        hops = {
            f"{FIXTURE_LOCATOR}/{i}": FakeHop(
                status_code=302,
                location=f"{FIXTURE_LOCATOR}/{i + 1}",
            )
            for i in range(5)
        }
        hops[FIXTURE_LOCATOR] = FakeHop(
            status_code=302, location=f"{FIXTURE_LOCATOR}/0"
        )
        with pytest.raises(ExternalEvidenceValidationError, match="too many redirects"):
            _retrieval(hops).retrieve(_request())

    def test_relative_redirect_stays_on_host(self) -> None:
        dest = f"{FIXTURE_LOCATOR}-final"
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                status_code=302,
                location="/filings/DSPX-FY24-note12-outstanding-final",
            ),
            dest: FakeHop(
                body=HTML.encode("utf-8"),
                headers={"content-type": "text/html"},
            ),
        }
        document = _retrieval(hops).retrieve(_request())
        assert document.requested_locator == FIXTURE_LOCATOR
        assert document.final_locator == dest

    def test_timeout_is_rejected(self) -> None:
        hops = {FIXTURE_LOCATOR: FakeHop(timeout=True)}
        with pytest.raises(ExternalEvidenceValidationError, match="timeout"):
            _retrieval(hops).retrieve(_request())

    def test_oversized_response_rejected(self) -> None:
        hops = {FIXTURE_LOCATOR: FakeHop(oversized=True)}
        with pytest.raises(ExternalEvidenceValidationError, match="size limit"):
            _retrieval(hops).retrieve(_request())

    def test_unsupported_content_type_rejected(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=b'{"shares":100}',
                headers={"content-type": "application/json"},
            )
        }
        with pytest.raises(
            ExternalEvidenceValidationError, match="unsupported content type"
        ):
            _retrieval(hops).retrieve(_request())

    def test_gzip_content_encoding_rejected(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=HTML.encode("utf-8"),
                headers={
                    "content-type": "text/html",
                    "content-encoding": "gzip",
                },
            )
        }
        with pytest.raises(
            ExternalEvidenceValidationError, match="compressed responses"
        ):
            _retrieval(hops).retrieve(_request())

    def test_pdf_is_not_supported(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=b"%PDF-1.4",
                headers={"content-type": "application/pdf"},
            )
        }
        with pytest.raises(ExternalEvidenceValidationError, match="PDF"):
            _retrieval(hops).retrieve(_request())

    def test_empty_content_rejected(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=b"   ",
                headers={"content-type": "text/plain"},
            )
        }
        with pytest.raises(ExternalEvidenceValidationError, match="missing document"):
            _retrieval(hops).retrieve(_request())

    def test_screener_host_is_t3_not_t2(self) -> None:
        assert "screener.in" in SCREENER_WEB_HOSTS
        assert source_tier_for_host("www.screener.in") is SourceTier.TIER_3_DISCOVERY
        assert frozenset() == TIER_1_WEB_HOSTS
        hops = {
            SCREENER_URL: FakeHop(
                body=HTML.encode("utf-8"),
                headers={"content-type": "text/html"},
            )
        }
        document = _retrieval(hops).retrieve(_request(SCREENER_URL))
        assert document.source_tier is SourceTier.TIER_3_DISCOVERY
        candidate = UntrustedShareCountAiCandidate(
            company_identity="DSPX",
            claimed_share_count=100,
            unit="shares",
            as_of_date=AS_OF,
            source_reference=SCREENER_URL,
            evidence_reference=EXCERPT,
            supporting_excerpt=EXCERPT,
        )
        with pytest.raises(ShareCountAcceptanceError, match="Tier 3/4"):
            dsp_accept_untrusted_share_count_candidate(
                candidate,
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_t1_host_policy_can_admit_fixture(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=load_local_filing_fixture().encode("utf-8"),
                headers={"content-type": "text/plain"},
            )
        }
        document = _retrieval(
            hops,
            tier_1_hosts=frozenset({"fixtures.dsp.test"}),
        ).retrieve(_request())
        assert document.source_tier is SourceTier.TIER_1_PRIMARY
        candidate = UntrustedShareCountAiCandidate(
            company_identity="DSPX",
            claimed_share_count=100,
            unit="shares",
            as_of_date=AS_OF,
            source_reference=FIXTURE_LOCATOR,
            evidence_reference=EXCERPT,
            supporting_excerpt=EXCERPT,
        )
        snap = dsp_accept_untrusted_share_count_candidate(
            candidate,
            document=document,
            requested_identity=FIXTURE_IDENTITY,
        )
        assert snap.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        assert snap.shares_value() == pytest.approx(100.0)

    def test_excerpt_must_exist_in_retrieved_content(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=b"<html><body>No share count here.</body></html>",
                headers={"content-type": "text/html"},
            )
        }
        document = _retrieval(
            hops,
            tier_1_hosts=frozenset({"fixtures.dsp.test"}),
        ).retrieve(_request())
        candidate = UntrustedShareCountAiCandidate(
            company_identity="DSPX",
            claimed_share_count=100,
            unit="shares",
            as_of_date=AS_OF,
            source_reference=FIXTURE_LOCATOR,
            evidence_reference=EXCERPT,
            supporting_excerpt=EXCERPT,
        )
        with pytest.raises(ShareCountAcceptanceError, match="not present"):
            dsp_accept_untrusted_share_count_candidate(
                candidate,
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )

    def test_source_url_mismatch_is_rejected(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=load_local_filing_fixture().encode("utf-8"),
                headers={"content-type": "text/plain"},
            )
        }
        document = _retrieval(
            hops,
            tier_1_hosts=frozenset({"fixtures.dsp.test"}),
        ).retrieve(_request())
        candidate = UntrustedShareCountAiCandidate(
            company_identity="DSPX",
            claimed_share_count=100,
            unit="shares",
            as_of_date=AS_OF,
            source_reference="https://fixtures.dsp.test/filings/other",
            evidence_reference=EXCERPT,
            supporting_excerpt=EXCERPT,
        )
        with pytest.raises(ShareCountAcceptanceError, match="must match"):
            dsp_accept_untrusted_share_count_candidate(
                candidate,
                document=document,
                requested_identity=FIXTURE_IDENTITY,
            )


class _FilingLocatorDiscovery:
    """TEST-ONLY T1 locator. Untrusted discovery, not ShareCount authority."""

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        record = ExternalEvidenceRecord(
            fact_id=request.fact_id,
            identity=request.identity,
            evidence_kind=EvidenceKind.QUALITATIVE,
            text_value="Untrusted AI locator. Not share-count authority.",
            topic=QualitativeEvidenceTopic.OTHER_QUALITATIVE,
            source_url=FIXTURE_LOCATOR,
            source_type=SourceType.FILING,
            source_tier=SourceTier.TIER_1_PRIMARY,
            evidence_reference=EXCERPT,
            retrieved_at=request.retrieved_at,
            evidence_quality=EvidenceQuality.UNKNOWN,
            validation_status=EvidenceValidationStatus.CANDIDATE,
            may_influence_calculation=False,
        )
        return ExternalEvidenceDiscoveryResult(request=request, records=(record,))


class TestProtocolAndActivation:
    def test_ai_candidate_remains_untrusted_and_cannot_build_snapshot(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=load_local_filing_fixture().encode("utf-8"),
                headers={"content-type": "text/plain"},
            )
        }
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=DeterministicScreenerLikeWebDiscovery(),
            retrieval=_retrieval(
                hops, tier_1_hosts=frozenset({"fixtures.dsp.test"})
            ),
            ai=DeterministicShareCountExtractionAiPort(),
        )
        # Screener discovery locator is T3 URL; retrieval of screener stays T3.
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.current_shares_outstanding is None
        assert result.snapshot is None

    def test_t1_retrieved_document_uses_existing_acceptance(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=load_local_filing_fixture().encode("utf-8"),
                headers={"content-type": "text/plain"},
            )
        }
        protocol = CurrentOutstandingProtocol(
            share_count_port=NullShareCountAdapter(),
            discovery=_FilingLocatorDiscovery(),
            retrieval=_retrieval(
                hops, tier_1_hosts=frozenset({"fixtures.dsp.test"})
            ),
            ai=DeterministicShareCountExtractionAiPort(),
        )
        result = protocol.resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.SHARECOUNT_VALIDATED
        assert result.snapshot is not None
        assert result.snapshot.provenance.provider_id == ACCEPTANCE_PROVIDER_ID
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(
                result.untrusted_candidate, symbol="DSPX"
            )
        assert not isinstance(result.untrusted_candidate, ShareCountSnapshot)

    def test_conflict_path_unchanged(self) -> None:
        hops = {
            FIXTURE_LOCATOR: FakeHop(
                body=load_local_filing_fixture().encode("utf-8"),
                headers={"content-type": "text/plain"},
            )
        }
        document = _retrieval(
            hops, tier_1_hosts=frozenset({"fixtures.dsp.test"})
        ).retrieve(_request())
        first = dsp_accept_untrusted_share_count_candidate(
            UntrustedShareCountAiCandidate(
                company_identity="DSPX",
                claimed_share_count=100,
                unit="shares",
                as_of_date=AS_OF,
                source_reference=FIXTURE_LOCATOR,
                evidence_reference=EXCERPT,
                supporting_excerpt=EXCERPT,
            ),
            document=document,
            requested_identity=FIXTURE_IDENTITY,
        )
        other = ShareCountEvidenceClaim(
            symbol=first.symbol,
            exchange=first.exchange,
            isin=first.isin,
            shares=200,
            unit="shares",
            basis="current_outstanding",
            as_of=date(2024, 3, 31),
            source_url="https://fixtures.dsp.test/filings/other",
            source_type="filing",
            source_tier="TIER_1_PRIMARY",
            evidence_reference=EXCERPT.replace("100", "200"),
            retrieved_at=FIXED,
            fact_id="current_outstanding",
            validation_status="validated",
        )
        first_claim = ShareCountEvidenceClaim(
            symbol=first.symbol,
            exchange=first.exchange,
            isin=first.isin,
            shares=100,
            unit="shares",
            basis="current_outstanding",
            as_of=date(2024, 3, 31),
            source_url=FIXTURE_LOCATOR,
            source_type="filing",
            source_tier="TIER_1_PRIMARY",
            evidence_reference=EXCERPT,
            retrieved_at=FIXED,
            fact_id="current_outstanding",
            validation_status="validated",
        )
        with pytest.raises(ShareCountAcceptanceError, match="conflict"):
            accept_current_outstanding_claims(
                [first_claim, other],
                symbol="DSPX",
                exchange="TESTEX",
                isin="DSPX00000001",
            )

    def test_production_ai_and_retrieval_remain_blocked(self) -> None:
        verdict = evaluate_activation(ActivationEvidence.missing())
        assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
        result = production_current_outstanding_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.diagnostic is _Diag.EVIDENCE_DISCOVERY_BLOCKED
        assert result.current_shares_outstanding is None
        with pytest.raises(
            DocumentRetrievalBlockedError, match="document_retrieval_not_configured"
        ):
            ProductionBlockedPrimarySourceDocumentRetrieval().retrieve(_request())
        with pytest.raises(ExternalEvidenceDiscoveryBlockedError):
            ProductionBlockedExternalEvidenceDiscovery().discover(
                ExternalEvidenceDiscoveryRequest(
                    identity=FIXTURE_IDENTITY,
                    fact_id="current_outstanding",
                    retrieved_at=FIXED,
                )
            )
