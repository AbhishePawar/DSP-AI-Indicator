"""Acquire → validate → candidate. Never writes production snapshots."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from dsp_platform.promoted_share_count import DEFAULT_PROMOTED_SHARE_COUNT_DIR
from dsp_platform.share_count_acquisition.artifacts import write_artifact
from dsp_platform.share_count_acquisition.bse import acquire_bse_disclosures
from dsp_platform.share_count_acquisition.http import JsonHttpPort
from dsp_platform.share_count_acquisition.issuer_fetch import fetch_issuer_outstanding
from dsp_platform.share_count_acquisition.live_http import AllowlistedLiveJsonHttp
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionRequest
from dsp_platform.share_count_acquisition.nse import acquire_nse_disclosures
from dsp_platform.share_count_acquisition.pipeline import refresh_from_acquired_evidence
from dsp_platform.share_count_acquisition.universe import (
    ListedEquityInstrument,
    get_listed_equity,
    iter_listed_equities,
)
from dsp_platform.share_count_promotion import (
    ShareCountPromotionError,
    ShareCountPromotionRecord,
    promote_validated_candidate,
)
from dsp_platform.share_count_refresh import (
    CoverageState,
    InstrumentIdentity,
    ShareCountRefreshResult,
)

__all__ = [
    "AcquisitionRun",
    "acquire_listed_equity",
    "acquire_universe",
    "promote_candidate_file",
]


@dataclass(frozen=True, slots=True)
class AcquisitionRun:
    identity: InstrumentIdentity
    state: CoverageState
    reason: str
    shares_outstanding: object
    as_of: object
    complete_through: object
    candidate: dict[str, Any] | None
    artifact_path: Path | None
    nse_records: int
    bse_records: int
    nse_exhausted: bool
    bse_exhausted: bool
    issuer_observation: bool
    production_written: bool = False


def acquire_listed_equity(
    *,
    isin: str,
    mic: str,
    lookup_horizon: datetime | None = None,
    http: JsonHttpPort | None = None,
    snapshot_dir: Path | None = None,
    artifact_dir: Path | None = None,
    fetch_issuer: bool = True,
    dry_run: bool = False,
) -> AcquisitionRun:
    """Live/recorded acquisition. Dry-run still validates; never promotes."""
    del dry_run
    instrument = get_listed_equity(isin, mic)
    if instrument is None:
        identity = InstrumentIdentity(symbol="", exchange="", mic=mic, isin=isin)
        return AcquisitionRun(
            identity=identity,
            state=CoverageState.UNKNOWN,
            reason="instrument is not in the listed-equity acquisition catalog",
            shares_outstanding=None,
            as_of=None,
            complete_through=None,
            candidate=None,
            artifact_path=None,
            nse_records=0,
            bse_records=0,
            nse_exhausted=False,
            bse_exhausted=False,
            issuer_observation=False,
        )
    horizon = lookup_horizon or datetime.now(tz=UTC)
    if horizon.tzinfo is None:
        raise ValueError("lookup_horizon must be timezone-aware and is not as_of")
    identity = instrument.identity.normalized()
    snapshot = _load_snapshot(identity, snapshot_dir or DEFAULT_PROMOTED_SHARE_COUNT_DIR)
    as_of = _snapshot_as_of(snapshot) or date(horizon.year, 1, 1)
    client = http or AllowlistedLiveJsonHttp()
    if hasattr(client, "warmup_nse"):
        client.warmup_nse(identity.symbol)
    request = ExchangeAcquisitionRequest(
        identity=identity,
        start=as_of,
        end=horizon.date(),
        retrieved_at=horizon,
        scrip_code=instrument.bse_scrip,
        equivalent_isins=instrument.predecessor_isins,
    )
    nse_bundle = acquire_nse_disclosures(request, client)
    bse_client = AllowlistedLiveJsonHttp() if http is None else client
    bse_bundle = acquire_bse_disclosures(request, bse_client)
    observation = None
    observation_source = "promoted_snapshot_artifact" if snapshot is not None else "t1_issuer_disclosure"
    if fetch_issuer:
        observation = fetch_issuer_outstanding(instrument, retrieved_at=horizon)
        if observation is not None:
            observation_source = "t1_issuer_disclosure"
            as_of = observation.as_of
    result = refresh_from_acquired_evidence(
        identity=identity,
        lookup_horizon=horizon,
        current_snapshot=snapshot,
        observation=observation,
        nse_bundle=nse_bundle,
        bse_bundle=bse_bundle,
        observation_source_id=observation_source,
    )
    payload = _artifact_payload(
        instrument=instrument,
        horizon=horizon,
        result=result,
        nse_bundle=nse_bundle,
        bse_bundle=bse_bundle,
        issuer_observation=observation is not None,
        snapshot_present=snapshot is not None,
    )
    artifact_path = None
    if artifact_dir is not None:
        artifact_path = write_artifact(
            Path(artifact_dir) / f"{identity.isin}_{identity.mic}.json",
            payload,
        )
    return AcquisitionRun(
        identity=identity,
        state=result.state,
        reason=result.reason,
        shares_outstanding=result.shares_outstanding,
        as_of=result.as_of,
        complete_through=result.complete_through,
        candidate=result.candidate,
        artifact_path=artifact_path,
        nse_records=nse_bundle.record_count,
        bse_records=bse_bundle.record_count,
        nse_exhausted=nse_bundle.pagination_exhausted,
        bse_exhausted=bse_bundle.pagination_exhausted,
        issuer_observation=observation is not None,
    )


def acquire_universe(
    *,
    lookup_horizon: datetime | None = None,
    artifact_dir: Path | None = None,
    http: JsonHttpPort | None = None,
    fetch_issuer: bool = True,
) -> tuple[AcquisitionRun, ...]:
    return tuple(
        acquire_listed_equity(
            isin=row.identity.isin,
            mic=row.identity.mic,
            lookup_horizon=lookup_horizon,
            http=http,
            artifact_dir=artifact_dir,
            fetch_issuer=fetch_issuer,
        )
        for row in iter_listed_equities()
    )


def promote_candidate_file(
    candidate_path: Path,
    *,
    destination_dir: Path,
    history_dir: Path,
    promoter: str,
    human_approved: bool,
    lookup_horizon: datetime,
) -> ShareCountPromotionRecord:
    """Explicit promotion. Refuses unless the candidate is VALIDATED."""
    raw = json.loads(Path(candidate_path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ShareCountPromotionError("candidate file is not an object")
    state_raw = raw.get("candidate_state") or raw.get("state")
    if state_raw and str(state_raw) != str(CoverageState.VALIDATED):
        raise ShareCountPromotionError(
            f"only VALIDATED candidates may be promoted; state={state_raw}"
        )
    nested = raw.get("candidate")
    option_b = raw.get("option_b") if isinstance(raw.get("option_b"), dict) else {}
    if isinstance(nested, dict):
        candidate = nested
        if str(option_b.get("state") or CoverageState.VALIDATED) != str(
            CoverageState.VALIDATED
        ):
            raise ShareCountPromotionError(
                f"only VALIDATED candidates may be promoted; state={option_b.get('state')}"
            )
    else:
        candidate = raw
    from dsp_platform.share_count_source_authorization import SourceAuthorizationStatus

    result = ShareCountRefreshResult(
        state=CoverageState.VALIDATED,
        reason=str(
            option_b.get("reason")
            or raw.get("reason")
            or "operator-supplied VALIDATED candidate"
        ),
        candidate=candidate,
        complete_through=_parse_date(candidate.get("complete_through")),
        source_status=SourceAuthorizationStatus.APPROVED,
    )
    return promote_validated_candidate(
        result,
        destination_dir=destination_dir,
        history_dir=history_dir,
        human_approved=human_approved,
        lookup_horizon=lookup_horizon,
        promoter=promoter,
    )


def _load_snapshot(identity: InstrumentIdentity, directory: Path) -> dict[str, Any] | None:
    path = Path(directory) / f"{identity.isin}_{identity.mic}.json"
    if not path.is_file():
        alt = Path(directory) / f"{identity.isin}_XBOM.json"
        path = alt if identity.mic == "XNSE" and alt.is_file() else path
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _snapshot_as_of(snapshot: Mapping[str, Any] | None) -> date | None:
    if snapshot is None:
        return None
    raw = snapshot.get("as_of")
    if isinstance(raw, str) and raw:
        return date.fromisoformat(raw)
    return None


def _parse_date(raw: object) -> date | None:
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _artifact_payload(
    *,
    instrument: ListedEquityInstrument,
    horizon: datetime,
    result: ShareCountRefreshResult,
    nse_bundle,
    bse_bundle,
    issuer_observation: bool,
    snapshot_present: bool,
) -> dict[str, Any]:
    identity = instrument.identity.normalized()
    return {
        "instrument_identity": {
            "symbol": identity.symbol,
            "exchange": identity.exchange,
            "mic": identity.mic,
            "isin": identity.isin,
            "issuer": identity.issuer,
        },
        "source": {
            "nse": nse_bundle.source_id,
            "bse": bse_bundle.source_id,
            "issuer": "t1_issuer_disclosure" if issuer_observation else None,
            "snapshot": "promoted_snapshot_artifact" if snapshot_present else None,
        },
        "source_tier": "TIER_1_PRIMARY",
        "retrieved_at": horizon.isoformat(),
        "lookup_horizon": horizon.isoformat(),
        "observation": {
            "shares_outstanding": (
                str(result.shares_outstanding)
                if result.shares_outstanding is not None
                else None
            ),
            "as_of": result.as_of.isoformat() if result.as_of else None,
            "issuer_extracted": issuer_observation,
        },
        "corporate_action_evidence": {
            "nse_source_url": nse_bundle.source_url,
            "bse_source_url": bse_bundle.source_url,
            "nse_record_count": nse_bundle.record_count,
            "bse_record_count": bse_bundle.record_count,
            "nse_pagination_exhausted": nse_bundle.pagination_exhausted,
            "bse_pagination_exhausted": bse_bundle.pagination_exhausted,
            "nse_truncated": nse_bundle.truncated,
            "bse_truncated": bse_bundle.truncated,
            "nse_rate_limited": nse_bundle.rate_limited,
            "bse_rate_limited": bse_bundle.rate_limited,
            "requested_start": nse_bundle.requested_start.isoformat(),
            "requested_end": nse_bundle.requested_end.isoformat(),
            "nse_http_status": nse_bundle.http_status,
            "bse_http_status": bse_bundle.http_status,
            "nse_traces": nse_bundle.fetch_traces,
            "bse_traces": bse_bundle.fetch_traces,
            "nse_subjects": [
                str(item.get("subject") or item.get("desc") or "")
                for item in nse_bundle.corporate_actions[:40]
                if isinstance(item, Mapping)
            ],
            "nse_announcement_descs": [
                str(item.get("desc") or item.get("subject") or "")
                for item in nse_bundle.announcements[:40]
                if isinstance(item, Mapping)
            ],
        },
        "option_b": {
            "state": str(result.state),
            "reason": result.reason,
            "complete_through": (
                result.complete_through.isoformat()
                if result.complete_through is not None
                else None
            ),
        },
        "coverage_horizon": horizon.date().isoformat(),
        "candidate_state": str(result.state),
        "candidate": result.candidate,
        "production_written": False,
    }
