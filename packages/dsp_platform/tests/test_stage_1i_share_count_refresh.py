"""Stage 1I — generic Option-B refresh and T1/T2 source authorization.

Refresh never writes promoted_share_counts/*.json. The second fixture is
SYNTHETIC — NOT PRODUCTION DATA.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform.current_outstanding_protocol.currentness import (
    SHARE_CHANGING_ACTION_TYPES,
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
)
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    SHARES_OUTSTANDING_STALE,
    DurablePromotedShareCountAdapter,
    ShareCountResolutionError,
)
from dsp_platform.share_count_refresh import (
    CoverageState,
    InstrumentIdentity,
    ShareCountObservation,
    ShareCountRefreshRequest,
    refresh_share_count,
)
from dsp_platform.share_count_source_authorization import (
    SOURCE_CATALOG,
    SourceAuthorizationStatus,
    SourceRole,
    assert_source_authorized,
)

_TCS_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"
_HORIZON = datetime(2026, 9, 5, 14, 6, tzinfo=UTC)
_STALE_HORIZON = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
_AS_OF = date(2026, 6, 30)
_TCS_SHARES = Decimal("3618087518")
_TCS_ISIN = "INE467B01029"

# SYNTHETIC — NOT PRODUCTION DATA
_SYNTHETIC_ISIN = "INE999Z01019"
_SYNTHETIC_SHARES = Decimal("1000000001")


def _tcs_snapshot() -> dict:
    return json.loads(_TCS_JSON.read_text(encoding="utf-8"))


def _tcs_identity(*, mic: str = "XNSE", isin: str = _TCS_ISIN) -> InstrumentIdentity:
    exchange = "BSE" if mic == "XBOM" else "NSE"
    return InstrumentIdentity(symbol="TCS", exchange=exchange, mic=mic, isin=isin)


def _tcs_instrument() -> Instrument:
    return Instrument(
        symbol="TCS",
        asset_class=AssetClass.EQUITY,
        currency="INR",
        exchange="NSE",
        isin=_TCS_ISIN,
        name="Tata Consultancy Services",
    )


def _ca_evidence(
    *,
    as_of: date = _AS_OF,
    complete_through: date = date(2026, 9, 5),
    events: tuple[ShareChangingCorporateAction, ...] = (),
    source_url: str = "https://fixtures.dsp.test/corporate-actions",
    evidence_reference: str = (
        "DSP-attested T1 corporate-action completeness; outstanding shares."
    ),
) -> CorporateActionCurrentnessEvidence:
    return CorporateActionCurrentnessEvidence(
        events=events,
        complete_through=complete_through,
        share_count_as_of=as_of,
        source_tier="TIER_1_PRIMARY",
        source_url=source_url,
        evidence_reference=evidence_reference,
    )


def _tcs_dividend() -> ShareChangingCorporateAction:
    return ShareChangingCorporateAction(
        action_type="dividend",
        effective_date=date(2026, 7, 15),
        changes_outstanding_shares=False,
        description="Interim Dividend - Rs 12 Per Share",
    )


def _observation(
    *,
    shares: Decimal = _SYNTHETIC_SHARES,
    as_of: date = _AS_OF,
    retrieved_at: datetime | None = None,
    publication_at: date | None = _AS_OF,
    source_url: str = "https://fixtures.dsp.test/synthetic/outstanding",
    evidence_reference: str = (
        "SYNTHETIC — NOT PRODUCTION DATA. As of June 30, 2026, "
        "outstanding shares were 1,000,000,001."
    ),
    source_id: str = "t1_issuer_disclosure",
) -> ShareCountObservation:
    return ShareCountObservation(
        shares_outstanding=shares,
        as_of=as_of,
        effective_date=as_of,
        retrieved_at=retrieved_at or _HORIZON,
        publication_at=publication_at,
        source_id=source_id,
        source_url=source_url,
        evidence_reference=evidence_reference,
        source_tier="TIER_1_PRIMARY",
    )


def _synth_identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="SYNTH",
        exchange="NSE",
        mic="XNSE",
        isin=_SYNTHETIC_ISIN,
    )


def _refresh(**kwargs: object) -> object:
    return refresh_share_count(ShareCountRefreshRequest(**kwargs))  # type: ignore[arg-type]


class TestExistingSafetyBoundary:
    def test_current_tcs_snapshot_resolves(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        snap = adapter.get_share_count(_tcs_instrument())
        assert snap is not None
        assert Decimal(str(int(snap.shares_value() or 0))) == _TCS_SHARES

    def test_tcs_snapshot_stale_after_complete_through_fails_closed(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _STALE_HORIZON)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            adapter.get_share_count(_tcs_instrument())

    def test_unknown_equity_has_no_promoted_snapshot(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        unknown = Instrument(
            symbol="INFY",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
            isin="INE009A01021",
        )
        assert adapter.get_share_count(unknown) is None

    def test_refresh_current_tcs_does_not_copy_or_extend_snapshot(self) -> None:
        before = _TCS_JSON.read_bytes()
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.CURRENT
        assert result.shares_outstanding == _TCS_SHARES
        assert result.complete_through == date(2026, 9, 5)
        assert result.candidate is None
        assert _TCS_JSON.read_bytes() == before

    def test_refresh_does_not_silently_extend_stale_tcs(self) -> None:
        before = _TCS_JSON.read_bytes()
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_STALE_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.STALE
        assert result.candidate is None
        assert "does not reach retrieved_at" in result.reason
        assert _TCS_JSON.read_bytes() == before


class TestTcsRefreshAcceptance:
    def test_refresh_exercises_algorithm_not_json_copy(self) -> None:
        snapshot = _tcs_snapshot()
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=snapshot,
            corporate_action_evidence=_ca_evidence(
                events=(_tcs_dividend(),),
                source_url=snapshot["source"]["source_url"],
                evidence_reference=snapshot["source"]["evidence_reference"],
            ),
        )
        assert result.state is CoverageState.CURRENT
        assert result.shares_outstanding == _TCS_SHARES
        assert result.as_of == _AS_OF

    def test_attested_ca_extension_emits_validated_candidate_only(self) -> None:
        snapshot = _tcs_snapshot()
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_STALE_HORIZON,
            current_snapshot=snapshot,
            corporate_action_evidence=_ca_evidence(
                complete_through=date(2026, 9, 6),
                events=(_tcs_dividend(),),
                source_url="https://fixtures.dsp.test/tcs/ca-attested-2026-09-06",
                evidence_reference=(
                    "DSP-attested T1 corporate-action completeness through "
                    "2026-09-06; outstanding shares unchanged after dividend."
                ),
            ),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.candidate is not None
        assert result.candidate["shares_outstanding"] == str(_TCS_SHARES)
        assert result.candidate["complete_through"] == "2026-09-06"
        assert result.candidate["refresh"]["human_promotion_required"] is True
        assert "integrity" not in result.candidate
        production = _tcs_snapshot()
        assert production["complete_through"] == "2026-09-05"

    def test_unreflected_bonus_after_as_of_is_unproven(self) -> None:
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
            corporate_action_evidence=_ca_evidence(
                events=(
                    _tcs_dividend(),
                    ShareChangingCorporateAction(
                        action_type="bonus",
                        effective_date=date(2026, 8, 1),
                        changes_outstanding_shares=True,
                        already_reflected_in_share_count=False,
                    ),
                )
            ),
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert result.candidate is None
        assert "later share-changing" in result.reason


class TestIdentity:
    def test_correct_isin_mic(self) -> None:
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.CURRENT

    def test_wrong_mic_is_unavailable(self) -> None:
        result = _refresh(
            identity=InstrumentIdentity(
                symbol="TCS", exchange="NASDAQ", mic="XNAS", isin=_TCS_ISIN
            ),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.INVALID

    def test_wrong_isin_is_unavailable(self) -> None:
        result = _refresh(
            identity=_tcs_identity(isin="INE009A01021"),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.INVALID
        assert "ISIN" in result.reason

    def test_ticker_collision_wrong_isin(self) -> None:
        result = _refresh(
            identity=InstrumentIdentity(
                symbol="TCS", exchange="NSE", mic="XNSE", isin="INE000A01000"
            ),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.INVALID

    def test_nse_bse_dual_listing_is_same_equity(self) -> None:
        result = _refresh(
            identity=_tcs_identity(mic="XBOM"),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
        )
        assert result.state is CoverageState.CURRENT
        assert result.shares_outstanding == _TCS_SHARES


class TestTime:
    def test_as_of_valid(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.as_of == _AS_OF

    def test_future_as_of_rejected(self) -> None:
        future = date(2026, 12, 31)
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(as_of=future, publication_at=future),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                as_of=future, complete_through=date(2027, 1, 31)
            ),
        )
        assert result.state is CoverageState.UNAVAILABLE
        assert "after lookup horizon" in result.reason

    def test_complete_through_before_horizon_rejected(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(complete_through=date(2026, 8, 1)),
        )
        assert result.state is CoverageState.STALE

    def test_complete_through_after_horizon_accepted(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(complete_through=date(2026, 9, 30)),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.complete_through == date(2026, 9, 30)

    def test_retrieved_at_cannot_stand_in_for_as_of(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(
                retrieved_at=datetime(2026, 6, 30, 12, tzinfo=UTC),
                publication_at=None,
            ),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.UNAVAILABLE
        assert "retrieved_at" in result.reason


class TestCorporateActions:
    @pytest.mark.parametrize(
        "action_type",
        (
            "stock_split",
            "reverse_split",
            "bonus",
            "rights",
            "new_issue",
            "buyback",
            "cancellation",
            "merger",
            "demerger",
            "conversion",
            "treasury",
        ),
    )
    def test_unreflected_share_changing_event_blocks(self, action_type: str) -> None:
        assert action_type in SHARE_CHANGING_ACTION_TYPES
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type=action_type,
                        effective_date=date(2026, 7, 15),
                        changes_outstanding_shares=True,
                    ),
                )
            ),
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert result.candidate is None

    def test_unclassified_event_is_unproven(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type="mystery_reorg",
                        effective_date=date(2026, 7, 15),
                    ),
                )
            ),
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert "not classified" in result.reason
        assert result.candidate is None

    def test_announced_future_split_does_not_change_outstanding_yet(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                complete_through=date(2026, 9, 5),
                events=(
                    ShareChangingCorporateAction(
                        action_type="stock_split",
                        effective_date=date(2026, 12, 1),
                        changes_outstanding_shares=True,
                        description="announced; not yet effective",
                    ),
                ),
            ),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.shares_outstanding == _SYNTHETIC_SHARES

    def test_already_reflected_split_does_not_block(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type="stock_split",
                        effective_date=date(2026, 7, 15),
                        changes_outstanding_shares=True,
                        already_reflected_in_share_count=True,
                    ),
                )
            ),
        )
        assert result.state is CoverageState.VALIDATED


class TestSourceAuthorization:
    def test_authorized_t1_sources_can_validate(self) -> None:
        assert_source_authorized(
            "t1_issuer_disclosure", SourceRole.SHARE_COUNT_OBSERVATION
        )
        assert_source_authorized(
            "t1_corporate_action_completeness",
            SourceRole.CORPORATE_ACTION_COMPLETENESS,
        )
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.source_status is SourceAuthorizationStatus.APPROVED

    def test_pending_twelve_data_cannot_promote(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="twelve_data_statistics",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert result.candidate is None
        assert result.source_status is SourceAuthorizationStatus.PENDING

    def test_rejected_gemini_cannot_promote(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="gemini_grounding",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.UNAVAILABLE
        assert result.candidate is None
        assert SOURCE_CATALOG["gemini_grounding"].status is SourceAuthorizationStatus.REJECTED

    def test_pending_nse_connector_cannot_attest_completeness(self) -> None:
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
            ca_source_id="nse_public_api_connector",
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert result.candidate is None

    def test_upstox_is_rejected(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="upstox_market_data",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.UNAVAILABLE


class TestIntegrityAndConflict:
    def test_tampered_snapshot_is_unavailable(self) -> None:
        snapshot = _tcs_snapshot()
        snapshot["shares_outstanding"] = "1"
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=snapshot,
        )
        assert result.state is CoverageState.INVALID
        assert "integrity" in result.reason

    def test_conflicting_observation_same_as_of(self) -> None:
        result = _refresh(
            identity=_tcs_identity(),
            lookup_horizon=_HORIZON,
            current_snapshot=_tcs_snapshot(),
            observation=_observation(
                shares=Decimal("9"),
                source_url="https://www.tcs.com/investor-relations/investor-faqs",
                evidence_reference="conflicting outstanding shares 9",
            ),
            observation_source_id="t1_issuer_disclosure",
        )
        assert result.state is CoverageState.INVALID
        assert "conflict" in result.reason

    def test_missing_evidence_reference_outstanding_token(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(evidence_reference="issued capital note"),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(),
        )
        assert result.state is CoverageState.UNAVAILABLE

    def test_incomplete_identity_is_unknown(self) -> None:
        result = _refresh(
            identity=InstrumentIdentity(symbol="TCS", exchange="NSE", mic="", isin=""),
            lookup_horizon=_HORIZON,
        )
        assert result.state is CoverageState.UNKNOWN


class TestCoverageAndNewListings:
    def test_unknown_equity_is_discovered_not_fabricated(self) -> None:
        result = _refresh(
            identity=InstrumentIdentity(
                symbol="INFY",
                exchange="NSE",
                mic="XNSE",
                isin="INE009A01021",
            ),
            lookup_horizon=_HORIZON,
        )
        assert result.state is CoverageState.DISCOVERED
        assert result.candidate is None
        assert result.shares_outstanding is None

    def test_new_listing_without_observation_fails_closed(self) -> None:
        result = _refresh(
            identity=InstrumentIdentity(
                symbol="NEWCO",
                exchange="NSE",
                mic="XNSE",
                isin="INE123A01011",
            ),
            lookup_horizon=_HORIZON,
        )
        assert result.state is CoverageState.DISCOVERED
        assert result.candidate is None

    def test_observation_without_ca_is_candidate_not_promoted(self) -> None:
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
        )
        assert result.state is CoverageState.CANDIDATE
        assert result.candidate is None


class TestGenericity:
    def test_synthetic_second_equity_validates_without_production_write(self) -> None:
        before = {path.name for path in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        result = _refresh(
            identity=_synth_identity(),
            lookup_horizon=_HORIZON,
            observation=_observation(),
            observation_source_id="t1_issuer_disclosure",
            corporate_action_evidence=_ca_evidence(
                events=(
                    ShareChangingCorporateAction(
                        action_type="dividend",
                        effective_date=date(2026, 7, 1),
                        changes_outstanding_shares=False,
                    ),
                )
            ),
        )
        assert result.state is CoverageState.VALIDATED
        assert result.shares_outstanding == _SYNTHETIC_SHARES
        assert "SYNTHETIC — NOT PRODUCTION DATA" in (
            result.candidate or {}
        ).get("source", {}).get("evidence_reference", "")
        after = {path.name for path in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        assert after == before
        assert "INE999Z01019_XNSE.json" not in after

    def test_production_directory_still_only_tcs(self) -> None:
        names = {path.name for path in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        assert names == {"INE467B01029_XNSE.json"}
        text = _TCS_JSON.read_text(encoding="utf-8")
        assert "SYNTHETIC — NOT PRODUCTION DATA" not in text
        assert str(_SYNTHETIC_SHARES) not in text
