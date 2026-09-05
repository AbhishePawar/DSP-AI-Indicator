"""Canonical current-outstanding production protocol.

Upstox/ShareCountPort first. If unavailable: discovery → retrieval →
untrusted AI extraction → DSP validation → existing ShareCount acceptance.

Production AI, discovery, and retrieval remain blocked. This module does
not call providers, HTTP, valuation, or recommendation engines.
"""

from __future__ import annotations

from datetime import date, datetime

from contracts.domain.instrument import Instrument
from data_engine import (
    ADMISSIBLE_SOURCE_TIERS,
    InvalidProviderDataError,
    NullShareCountAdapter,
    ProviderRequestError,
    ShareCountAcceptanceError,
    ShareCountBasis,
    ShareCountPort,
    ShareCountUnit,
    assert_share_count_identity,
    validate_share_count_snapshot,
)
from dsp_platform.canonical_research_ai.port import (
    CanonicalResearchAiBlockedError,
    CanonicalResearchAiPort,
    ProductionBlockedCanonicalResearchAiPort,
)
from dsp_platform.current_outstanding_protocol.ai_candidate import (
    untrusted_candidate_from_ai_draft,
)
from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
    evaluate_option_b_currentness,
)
from dsp_platform.current_outstanding_protocol.gated_discovery import (
    ActivationGatedEvidenceDiscovery,
    AiAssistedShareCountWebDiscovery,
)
from dsp_platform.current_outstanding_protocol.models import (
    CurrentOutstandingDiagnostic,
    CurrentOutstandingProtocolResult,
)
from dsp_platform.current_outstanding_protocol.promotion import (
    dsp_accept_untrusted_share_count_candidate,
)
from dsp_platform.current_outstanding_protocol.prompt import (
    build_share_count_extraction_prompt,
)
from dsp_platform.external_evidence.models import (
    ExternalEvidenceIdentity,
    ExternalEvidenceValidationError,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
)
from dsp_platform.external_evidence_discovery.port import (
    ExternalEvidenceDiscoveryBlockedError,
    ExternalEvidenceDiscoveryPort,
)
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentRequest,
    PrimarySourceDocumentType,
)
from dsp_platform.primary_source_retrieval.port import (
    DocumentRetrievalBlockedError,
    PrimarySourceDocumentRetrievalPort,
    ProductionBlockedPrimarySourceDocumentRetrieval,
)

__all__ = [
    "CurrentOutstandingProtocol",
    "production_current_outstanding_protocol",
]

_Diag = CurrentOutstandingDiagnostic


class CurrentOutstandingProtocol:
    """Orchestrate the fail-closed current-outstanding evidence path."""

    def __init__(
        self,
        *,
        share_count_port: ShareCountPort,
        discovery: ExternalEvidenceDiscoveryPort,
        retrieval: PrimarySourceDocumentRetrievalPort,
        ai: CanonicalResearchAiPort,
        document_type: PrimarySourceDocumentType = (
            PrimarySourceDocumentType.ANNUAL_REPORT
        ),
    ) -> None:
        self._share_count_port = share_count_port
        self._discovery = discovery
        self._retrieval = retrieval
        self._ai = ai
        self._document_type = document_type

    def resolve(
        self,
        instrument: Instrument,
        *,
        identity: ExternalEvidenceIdentity,
        retrieved_at: datetime,
        fact_id: str = "current_outstanding",
        as_of_target: date | None = None,
        locator: str | None = None,
        corporate_action_currentness: CorporateActionCurrentnessEvidence | None = None,
    ) -> CurrentOutstandingProtocolResult:
        """Resolve current outstanding shares or fail closed."""
        if not isinstance(instrument, Instrument):
            return _result(
                _Diag.SHARECOUNT_UNAVAILABLE,
                upstox_status=_Diag.UPSTOX_VALUE_UNAVAILABLE,
                detail="instrument is required",
            )
        if identity.symbol.strip().upper() != instrument.symbol.strip().upper():
            return _result(
                _Diag.SHARECOUNT_UNAVAILABLE,
                upstox_status=_Diag.UPSTOX_VALUE_UNAVAILABLE,
                detail="instrument and evidence identity symbols disagree",
            )
        present = _port_snapshot(
            self._share_count_port,
            instrument,
            identity=identity,
        )
        if present is not None:
            shares = present.shares_value()
            return CurrentOutstandingProtocolResult(
                diagnostic=_Diag.UPSTOX_VALUE_PRESENT,
                snapshot=present,
                current_shares_outstanding=(
                    float(shares) if shares is not None else None
                ),
                upstox_status=_Diag.UPSTOX_VALUE_PRESENT,
            )
        upstox_status = _Diag.UPSTOX_VALUE_UNAVAILABLE
        request = ExternalEvidenceDiscoveryRequest(
            identity=identity,
            fact_id=fact_id,
            retrieved_at=retrieved_at,
            as_of_target=as_of_target,
        )
        try:
            discovered = self._discovery.discover(request)
        except ExternalEvidenceDiscoveryBlockedError as exc:
            return _result(
                _Diag.EVIDENCE_DISCOVERY_BLOCKED,
                upstox_status=upstox_status,
                detail=str(exc),
            )
        except ExternalEvidenceValidationError as exc:
            return _result(
                _Diag.SHARECOUNT_UNAVAILABLE,
                upstox_status=upstox_status,
                detail=str(exc),
            )
        resolved_locator = (locator or "").strip() or _locator_from_discovery(
            discovered
        )
        if not resolved_locator:
            return _result(
                _Diag.SHARECOUNT_UNAVAILABLE,
                upstox_status=upstox_status,
                detail="no retrievable primary-source locator",
            )
        retrieval_request = PrimarySourceDocumentRequest(
            identity=identity,
            locator=resolved_locator,
            document_type=self._document_type,
            fact_id=fact_id,
            retrieved_at=retrieved_at,
        )
        try:
            document = self._retrieval.retrieve(retrieval_request)
        except DocumentRetrievalBlockedError as exc:
            return _result(
                _Diag.DOCUMENT_RETRIEVAL_BLOCKED,
                upstox_status=upstox_status,
                detail=str(exc),
            )
        except ExternalEvidenceValidationError as exc:
            return _result(
                _Diag.DOCUMENT_RETRIEVAL_BLOCKED,
                upstox_status=upstox_status,
                detail=str(exc),
            )
        prompt = build_share_count_extraction_prompt(
            document,
            requested_identity=identity,
        )
        try:
            draft = self._ai.interpret(prompt)
        except CanonicalResearchAiBlockedError as exc:
            return _result(
                _Diag.AI_EXECUTION_BLOCKED,
                upstox_status=upstox_status,
                detail=str(exc),
            )
        candidate = untrusted_candidate_from_ai_draft(draft)
        if candidate is None:
            return CurrentOutstandingProtocolResult(
                diagnostic=_Diag.AI_CANDIDATE_REJECTED,
                snapshot=None,
                current_shares_outstanding=None,
                upstox_status=upstox_status,
                untrusted_candidate=None,
                detail="AI candidate missing or malformed",
            )
        try:
            snapshot = dsp_accept_untrusted_share_count_candidate(
                candidate,
                document=document,
                requested_identity=identity,
            )
        except ShareCountAcceptanceError as exc:
            message = str(exc)
            diagnostic = (
                _Diag.SHARECOUNT_CONFLICT
                if "conflict" in message
                else _Diag.AI_CANDIDATE_REJECTED
            )
            return CurrentOutstandingProtocolResult(
                diagnostic=diagnostic,
                snapshot=None,
                current_shares_outstanding=None,
                upstox_status=upstox_status,
                untrusted_candidate=candidate,
                detail=message,
            )
        as_of_date = snapshot.as_of.date() if snapshot.as_of is not None else None
        if as_of_date is None:
            return CurrentOutstandingProtocolResult(
                diagnostic=_Diag.OPTION_B_UNPROVEN,
                snapshot=None,
                current_shares_outstanding=None,
                upstox_status=upstox_status,
                untrusted_candidate=candidate,
                detail="share-count as_of is required for Option B currentness",
            )
        currentness = evaluate_option_b_currentness(
            share_count_as_of=as_of_date,
            retrieved_at=retrieved_at,
            evidence=corporate_action_currentness,
        )
        if not currentness.proven:
            return CurrentOutstandingProtocolResult(
                diagnostic=_Diag.OPTION_B_UNPROVEN,
                snapshot=None,
                current_shares_outstanding=None,
                upstox_status=upstox_status,
                untrusted_candidate=candidate,
                detail=currentness.reason,
            )
        shares = snapshot.shares_value()
        return CurrentOutstandingProtocolResult(
            diagnostic=_Diag.SHARECOUNT_VALIDATED,
            snapshot=snapshot,
            current_shares_outstanding=float(shares) if shares is not None else None,
            upstox_status=upstox_status,
            untrusted_candidate=candidate,
        )


def production_current_outstanding_protocol(
    share_count_port: ShareCountPort | None = None,
) -> CurrentOutstandingProtocol:
    """Production seam: gated web research, blocked retrieval/AI. No env bypass."""
    blocked_ai = ProductionBlockedCanonicalResearchAiPort()
    return CurrentOutstandingProtocol(
        share_count_port=share_count_port or NullShareCountAdapter(),
        discovery=ActivationGatedEvidenceDiscovery(
            AiAssistedShareCountWebDiscovery(ai=blocked_ai),
            activation_ready=False,
        ),
        retrieval=ProductionBlockedPrimarySourceDocumentRetrieval(),
        ai=blocked_ai,
    )


def _port_snapshot(
    port: ShareCountPort,
    instrument: Instrument,
    *,
    identity: ExternalEvidenceIdentity,
):
    try:
        snapshot = port.get_share_count(instrument)
    except (InvalidProviderDataError, ProviderRequestError):
        return None
    if snapshot is None:
        return None
    if snapshot.basis != ShareCountBasis.CURRENT_OUTSTANDING:
        return None
    if snapshot.unit != ShareCountUnit.SHARES:
        return None
    try:
        validate_share_count_snapshot(snapshot)
        assert_share_count_identity(
            snapshot,
            symbol=identity.symbol,
            exchange=identity.exchange,
            isin=identity.isin,
        )
    except InvalidProviderDataError:
        return None
    shares = snapshot.shares_value()
    if shares is None or shares <= 0:
        return None
    return snapshot


def _locator_from_discovery(discovered: object) -> str:
    records = getattr(discovered, "records", ()) or ()
    preferred: list[str] = []
    locators: list[str] = []
    for record in records:
        url = str(getattr(record, "source_url", "") or "").strip()
        if not url:
            continue
        locators.append(url)
        tier_obj = getattr(record, "source_tier", "")
        tier = str(getattr(tier_obj, "value", tier_obj))
        if tier in ADMISSIBLE_SOURCE_TIERS:
            preferred.append(url)
    if preferred:
        return preferred[0]
    if locators:
        return locators[0]
    return ""


def _result(
    diagnostic: CurrentOutstandingDiagnostic,
    *,
    upstox_status: CurrentOutstandingDiagnostic,
    detail: str | None = None,
) -> CurrentOutstandingProtocolResult:
    return CurrentOutstandingProtocolResult(
        diagnostic=diagnostic,
        snapshot=None,
        current_shares_outstanding=None,
        upstox_status=upstox_status,
        detail=detail,
    )
