"""Convert acquired exchange bundles into Option-B evidence and refresh."""

from __future__ import annotations

from dsp_platform.current_outstanding_protocol.ledger import (
    ExchangeCompletenessCorpus,
    attest_option_b_from_exchange_corpus,
)
from dsp_platform.external_evidence.models import ExternalEvidenceIdentity
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionResult
from dsp_platform.share_count_refresh import (
    InstrumentIdentity,
    ShareCountObservation,
    ShareCountRefreshRequest,
    ShareCountRefreshResult,
    refresh_share_count,
)
from dsp_platform.share_count_source_authorization import (
    SourceAuthorizationStatus,
    get_source_authorization,
)

__all__ = ["attest_exchange_bundle", "refresh_from_acquired_evidence"]


def attest_exchange_bundle(
    bundle: ExchangeAcquisitionResult,
    *,
    share_count_as_of,
    source_tier: str = "TIER_1_PRIMARY",
):
    """Attest a recorded/DSP-owned corpus. Live connector PENDING ≠ this role."""
    identity = bundle.identity
    corpus = ExchangeCompletenessCorpus(
        identity=ExternalEvidenceIdentity(
            symbol=identity.symbol,
            exchange=identity.exchange,
            isin=identity.isin,
            company_name=identity.issuer or identity.symbol,
            mic=identity.mic,
        ),
        share_count_as_of=share_count_as_of,
        requested_start=bundle.requested_start,
        requested_end=bundle.requested_end,
        retrieved_at=bundle.retrieved_at,
        pagination_exhausted=bundle.pagination_exhausted,
        date_range_explicit=bundle.date_range_explicit,
        source_tier=source_tier,
        source_url=bundle.source_url,
        evidence_reference=bundle.evidence_reference,
        corporate_actions=bundle.corporate_actions,
        announcements=bundle.announcements,
    )
    return attest_option_b_from_exchange_corpus(corpus)


def refresh_from_acquired_evidence(
    *,
    identity: InstrumentIdentity,
    lookup_horizon,
    current_snapshot: dict | None = None,
    observation: ShareCountObservation | None = None,
    nse_bundle: ExchangeAcquisitionResult | None = None,
    bse_bundle: ExchangeAcquisitionResult | None = None,
    observation_source_id: str = "t1_issuer_disclosure",
) -> ShareCountRefreshResult:
    """Run generic refresh from acquired T1 objects. Never writes production."""
    live = get_source_authorization("nse_public_api_connector")
    if live is not None and live.status is SourceAuthorizationStatus.PENDING:
        # Acquisition may still feed a DSP-attested corpus; promotion uses
        # t1_corporate_action_completeness, not the live connector id.
        pass
    evidence = None
    as_of = None
    if observation is not None:
        as_of = observation.as_of
    elif current_snapshot is not None:
        raw = current_snapshot.get("as_of")
        if isinstance(raw, str) and raw:
            from datetime import date as date_cls

            as_of = date_cls.fromisoformat(raw)
    if nse_bundle is not None and as_of is not None:
        attestation = attest_exchange_bundle(nse_bundle, share_count_as_of=as_of)
        if not attestation.proven:
            from dsp_platform.share_count_refresh import CoverageState, ShareCountRefreshResult

            return ShareCountRefreshResult(
                state=CoverageState.REFRESH_PENDING,
                reason=attestation.reason,
                shares_outstanding=(
                    observation.shares_outstanding if observation is not None else None
                ),
                as_of=as_of,
            )
        evidence = attestation.evidence
        if bse_bundle is not None and not bse_bundle.pagination_exhausted:
            # BSE is a cross-check, not outstanding authority. Incomplete BSE
            # must not silently count as completeness; omit it from attestation.
            bse_bundle = None
    return refresh_share_count(
        ShareCountRefreshRequest(
            identity=identity,
            lookup_horizon=lookup_horizon,
            current_snapshot=current_snapshot,
            corporate_action_evidence=evidence,
            observation=observation,
            observation_source_id=observation_source_id,
            ca_source_id="t1_corporate_action_completeness",
        )
    )
