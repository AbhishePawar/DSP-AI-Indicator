"""Valuation overlay from a CURRENT DSP-validated share-research record.

Does not write promoted snapshots. Does not treat Gemini prose as authority.
Identity mismatch and non-CURRENT statuses do not overlay.
"""

from __future__ import annotations

from datetime import UTC, datetime

from contracts.domain.instrument import Instrument
from data_engine import (
    ShareCountBasis,
    ShareCountField,
    ShareCountProvenance,
    ShareCountSnapshot,
    ShareCountUnit,
)
from dsp_platform.share_research.identity import equivalent_mics
from dsp_platform.share_research.models import ShareResearchCheck, ShareResearchStatus
from dsp_platform.share_research.store import ShareResearchStore, get_share_research_store

__all__ = ["current_share_research_snapshot"]


def current_share_research_snapshot(
    instrument: Instrument,
    *,
    store: ShareResearchStore | None = None,
    now: datetime | None = None,
) -> ShareCountSnapshot | None:
    isin = str(instrument.isin or "").strip().upper()
    if not isin:
        return None
    record = (store or get_share_research_store()).load_current(isin)
    if record is None:
        return None
    if record.status is not ShareResearchStatus.CURRENT:
        return None
    if not record.valuation_eligible:
        return None
    if record.identity_check is not ShareResearchCheck.PASS:
        return None
    if record.corporate_action_check is not ShareResearchCheck.PASS:
        return None
    if record.cross_check is not ShareResearchCheck.PASS:
        return None
    if record.outstanding_shares is None or record.as_of is None:
        return None
    requested_symbol = str(instrument.symbol or "").strip().upper()
    if requested_symbol and requested_symbol != record.ticker:
        return None
    requested_exchange = str(instrument.exchange or "").strip().upper()
    if requested_exchange and requested_exchange != record.exchange:
        from dsp_platform.share_research.identity import EXCHANGE_TO_MIC

        requested_mic = EXCHANGE_TO_MIC.get(requested_exchange, "")
        if requested_mic and not equivalent_mics(requested_mic, record.mic):
            return None
    horizon = now or datetime.now(tz=UTC)
    if record.current_through is None or record.current_through < horizon.date():
        return None
    source_url = next((row.url for row in record.primary_sources if row.accepted), "")
    as_of_dt = datetime(
        record.as_of.year, record.as_of.month, record.as_of.day, tzinfo=UTC
    )
    return ShareCountSnapshot(
        symbol=record.ticker,
        exchange=record.exchange,
        isin=record.isin,
        shares=ShareCountField.of(record.outstanding_shares),
        basis=ShareCountBasis.CURRENT_OUTSTANDING,
        unit=ShareCountUnit.SHARES,
        as_of=as_of_dt,
        provenance=ShareCountProvenance(
            provider_id="dsp_share_research",
            provider_name="DSP validated share research",
            source_type="primary_filing",
            retrieved_at=record.last_verified_at,
            as_of=as_of_dt,
            auth_mode="research_record",
            metadata={
                "research_id": record.research_id,
                "source_url": source_url,
                "current_through": record.current_through.isoformat(),
                "integrity_hash": record.integrity_hash,
            },
        ),
    )
