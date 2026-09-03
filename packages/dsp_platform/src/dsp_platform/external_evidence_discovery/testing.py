"""TEST-ONLY deterministic ExternalEvidenceDiscoveryPort.

Not a web-search adapter. Not production discovery. Requires no network,
API key, or SDK. Returns a synthetic CURRENT_OUTSTANDING candidate only.

Never selected by production configuration.
"""

from __future__ import annotations

from datetime import date, datetime

from dsp_platform.external_evidence.models import (
    CURRENT_OUTSTANDING_FACT_IDS,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    SourceTier,
    SourceType,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    validate_external_evidence_record,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import (
    bound_evidence_excerpt,
    validate_discovery_request,
)

__all__ = [
    "FIXTURE_AS_OF",
    "FIXTURE_IDENTITY",
    "FIXTURE_PUBLICATION_DATE",
    "FIXTURE_SHARES",
    "FIXTURE_SOURCE_URL",
    "TEST_ONLY",
    "DeterministicExternalEvidenceDiscovery",
]

TEST_ONLY = True

FIXTURE_IDENTITY = ExternalEvidenceIdentity(
    symbol="DSPX",
    exchange="TESTEX",
    isin="DSPX00000001",
    company_name="DSP Test Synthetic Co",
)
FIXTURE_SHARES = 123456789.0
FIXTURE_SOURCE_URL = (
    "https://fixtures.dsp.test/filings/DSPX-FY24-note12-outstanding"
)
FIXTURE_AS_OF = date(2024, 3, 31)
FIXTURE_PUBLICATION_DATE = date(2024, 4, 15)

_FORBIDDEN_INFERENCE_FACT_IDS = frozenset(
    {
        *WEIGHTED_AVERAGE_SHARES_FACT_IDS,
        "equity_capital",
        "paid_up_capital",
        "authorized_shares",
        "issued_shares",
        "market_cap",
        "market_capitalization",
        "volume",
        "open_interest",
        "oi",
        "eps",
        "eps_basic",
        "eps_diluted",
        "net_income",
        "price",
        "current_price",
    }
)

_EXCERPT = bound_evidence_excerpt(
    "SYNTHETIC FIXTURE — not a live filing. Note 12: issued and "
    "outstanding share capital was 123456789 shares."
)


class DeterministicExternalEvidenceDiscovery:
    """In-memory test discovery. No network. No credentials. Test-only."""

    TEST_ONLY = True

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        validate_discovery_request(request)
        if not _identity_matches(request):
            return _empty(request)
        if request.as_of_target is not None and request.as_of_target != FIXTURE_AS_OF:
            return _empty(request)
        fact = request.fact_id.strip().lower()
        if fact in _FORBIDDEN_INFERENCE_FACT_IDS:
            return _empty(request)
        if fact not in CURRENT_OUTSTANDING_FACT_IDS:
            return _empty(request)
        record = _outstanding_candidate(retrieved_at=request.retrieved_at)
        validate_external_evidence_record(record)
        return ExternalEvidenceDiscoveryResult(
            request=request,
            records=(record,),
        )


def _identity_matches(request: ExternalEvidenceDiscoveryRequest) -> bool:
    try:
        assert_identities_compatible(request.identity, FIXTURE_IDENTITY)
    except ExternalEvidenceValidationError:
        return False
    return True


def _empty(
    request: ExternalEvidenceDiscoveryRequest,
) -> ExternalEvidenceDiscoveryResult:
    return ExternalEvidenceDiscoveryResult(request=request, records=())


def _outstanding_candidate(*, retrieved_at: datetime) -> ExternalEvidenceRecord:
    return ExternalEvidenceRecord(
        fact_id="current_outstanding",
        identity=FIXTURE_IDENTITY,
        evidence_kind=EvidenceKind.NUMERICAL,
        numeric_value=FIXTURE_SHARES,
        unit="shares",
        as_of=FIXTURE_AS_OF,
        publication_date=FIXTURE_PUBLICATION_DATE,
        source_url=FIXTURE_SOURCE_URL,
        source_type=SourceType.FILING,
        source_tier=SourceTier.TIER_1_PRIMARY,
        evidence_reference=_EXCERPT,
        retrieved_at=retrieved_at,
        evidence_quality=EvidenceQuality.UNKNOWN,
        validation_status=EvidenceValidationStatus.CANDIDATE,
        may_influence_calculation=False,
        claimed_dsp_field=None,
    )
