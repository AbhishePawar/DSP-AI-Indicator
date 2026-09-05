"""Stage 1J — generic human-gated promotion of VALIDATED refresh candidates.

Does not write production promoted_share_counts unless a test uses tmp_path.
The TCS production artifact is asserted unchanged.
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
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
)
from dsp_platform.current_outstanding_protocol.ledger import classify_exchange_event
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    DurablePromotedShareCountAdapter,
    SHARES_OUTSTANDING_STALE,
    ShareCountResolutionError,
    canonical_promoted_snapshot_digest,
)
from dsp_platform.share_count_promotion import (
    ShareCountPromotionError,
    promote_validated_candidate,
)
from dsp_platform.share_count_refresh import (
    CoverageState,
    InstrumentIdentity,
    ShareCountObservation,
    ShareCountRefreshRequest,
    refresh_share_count,
)

_TCS_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"
_HORIZON = datetime(2026, 9, 5, 17, 57, tzinfo=UTC)
_NEXT_DAY = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
_AS_OF = date(2026, 6, 30)
_OLD_HASH = "d554046950f038b59feab960736cc63a4c30525f70ccee6fbe65092e262f2e72"


def _tcs_snapshot() -> dict:
    return json.loads(_TCS_JSON.read_text(encoding="utf-8"))


def _tcs_identity() -> InstrumentIdentity:
    return InstrumentIdentity(symbol="TCS", exchange="NSE", mic="XNSE", isin="INE467B01029")


def _ca(
    *,
    complete_through: date,
    events: tuple[ShareChangingCorporateAction, ...] = (),
) -> CorporateActionCurrentnessEvidence:
    return CorporateActionCurrentnessEvidence(
        events=events,
        complete_through=complete_through,
        share_count_as_of=_AS_OF,
        source_tier="TIER_1_PRIMARY",
        source_url="https://www.nseindia.com/api/corporates-corporateActions",
        evidence_reference=(
            "DSP-attested T1 corporate-action completeness; outstanding shares."
        ),
    )


def _dividend() -> ShareChangingCorporateAction:
    return ShareChangingCorporateAction(
        action_type="dividend",
        effective_date=date(2026, 7, 15),
        changes_outstanding_shares=False,
        description="Interim Dividend - Rs 12 Per Share",
    )


def _synth_observation() -> ShareCountObservation:
    return ShareCountObservation(
        shares_outstanding=Decimal("1000000001"),
        as_of=_AS_OF,
        effective_date=_AS_OF,
        retrieved_at=_HORIZON,
        publication_at=_AS_OF,
        source_id="t1_issuer_disclosure",
        source_url="https://fixtures.dsp.test/synthetic/outstanding",
        evidence_reference=(
            "SYNTHETIC — NOT PRODUCTION DATA. As of June 30, 2026, "
            "outstanding shares were 1,000,000,001."
        ),
        source_tier="TIER_1_PRIMARY",
    )


class TestHorizonAndCurrentSnapshot:
    def test_production_snapshot_fields_and_integrity(self) -> None:
        snap = _tcs_snapshot()
        assert snap["identity"]["isin"] == "INE467B01029"
        assert snap["identity"]["mic"] == "XNSE"
        assert snap["identity"]["symbol"] == "TCS"
        assert snap["shares_outstanding"] == "3618087518"
        assert snap["as_of"] == "2026-06-30"
        assert snap["effective_date"] == "2026-06-30"
        assert snap["complete_through"] == "2026-09-05"
        assert canonical_promoted_snapshot_digest(snap) == _OLD_HASH
        assert snap["integrity"]["sha256"] == _OLD_HASH

    def test_current_snapshot_still_resolves_on_attested_horizon(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        inst = Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
            isin="INE467B01029",
        )
        snap = adapter.get_share_count(inst)
        assert snap is not None
        assert int(snap.shares_value() or 0) == 3618087518

    def test_next_utc_day_is_stale_without_new_corpus(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _NEXT_DAY)
        inst = Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
            isin="INE467B01029",
        )
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            adapter.get_share_count(inst)


class TestGenericRefresh:
    def test_fresh_same_horizon_corpus_is_current_not_auto_written(self) -> None:
        before = _TCS_JSON.read_bytes()
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 5), events=(_dividend(),)
                ),
            )
        )
        assert result.state is CoverageState.CURRENT
        assert result.candidate is None
        assert _TCS_JSON.read_bytes() == before

    def test_incomplete_corpus_cannot_promote(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_NEXT_DAY,
                current_snapshot=_tcs_snapshot(),
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 5), events=(_dividend(),)
                ),
            )
        )
        assert result.state is CoverageState.STALE
        with pytest.raises(ShareCountPromotionError, match="stale"):
            promote_validated_candidate(
                result,
                destination_dir=Path("."),
                history_dir=Path("."),
                human_approved=True,
                lookup_horizon=_NEXT_DAY,
                promoter="stage-1j-test",
            )

    def test_unclassified_event_cannot_promote(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 5),
                    events=(
                        _dividend(),
                        ShareChangingCorporateAction(
                            action_type="mystery_reorg",
                            effective_date=date(2026, 8, 1),
                        ),
                    ),
                ),
            )
        )
        assert result.state is CoverageState.REFRESH_PENDING
        with pytest.raises(ShareCountPromotionError):
            promote_validated_candidate(
                result,
                destination_dir=Path("."),
                history_dir=Path("."),
                human_approved=True,
                lookup_horizon=_HORIZON,
                promoter="stage-1j-test",
            )

    def test_future_effective_split_does_not_change_count(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 5),
                    events=(
                        _dividend(),
                        ShareChangingCorporateAction(
                            action_type="stock_split",
                            effective_date=date(2026, 12, 1),
                            changes_outstanding_shares=True,
                        ),
                    ),
                ),
            )
        )
        assert result.state is CoverageState.CURRENT
        assert result.shares_outstanding == Decimal("3618087518")

    def test_already_reflected_event_can_validate(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="SYNTH", exchange="NSE", mic="XNSE", isin="INE999Z01019"
                ),
                lookup_horizon=_NEXT_DAY,
                observation=_synth_observation(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=CorporateActionCurrentnessEvidence(
                    events=(
                        ShareChangingCorporateAction(
                            action_type="bonus",
                            effective_date=date(2026, 9, 6),
                            changes_outstanding_shares=True,
                            already_reflected_in_share_count=True,
                        ),
                    ),
                    complete_through=date(2026, 9, 6),
                    share_count_as_of=_AS_OF,
                    source_tier="TIER_1_PRIMARY",
                    source_url="https://fixtures.dsp.test/synthetic/ca",
                    evidence_reference="SYNTHETIC — NOT PRODUCTION DATA outstanding.",
                ),
            )
        )
        assert result.state is CoverageState.VALIDATED
        assert result.candidate is not None
        assert result.candidate["refresh"]["human_promotion_required"] is True


class TestIdentityAndSemantics:
    def test_wrong_isin_and_mic(self) -> None:
        wrong_isin = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="NSE", mic="XNSE", isin="INE009A01021"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
            )
        )
        wrong_mic = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="NASDAQ", mic="XNAS", isin="INE467B01029"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
            )
        )
        dual = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="BSE", mic="XBOM", isin="INE467B01029"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
            )
        )
        assert wrong_isin.state is CoverageState.INVALID
        assert wrong_mic.state is CoverageState.INVALID
        assert dual.state is CoverageState.CURRENT

    def test_pending_source_cannot_promote(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
                observation_source_id="twelve_data_statistics",
            )
        )
        assert result.state is CoverageState.REFRESH_PENDING
        with pytest.raises(ShareCountPromotionError):
            promote_validated_candidate(
                result,
                destination_dir=Path("."),
                history_dir=Path("."),
                human_approved=True,
                lookup_horizon=_HORIZON,
                promoter="stage-1j-test",
            )


class TestPromotionGates:
    def test_validated_requires_human_approval(self, tmp_path: Path) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="SYNTH", exchange="NSE", mic="XNSE", isin="INE999Z01019"
                ),
                lookup_horizon=_NEXT_DAY,
                observation=_synth_observation(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=CorporateActionCurrentnessEvidence(
                    events=(),
                    complete_through=date(2026, 9, 6),
                    share_count_as_of=_AS_OF,
                    source_tier="TIER_1_PRIMARY",
                    source_url="https://fixtures.dsp.test/synthetic/ca",
                    evidence_reference="SYNTHETIC outstanding completeness.",
                ),
            )
        )
        assert result.state is CoverageState.VALIDATED
        with pytest.raises(ShareCountPromotionError, match="human approval"):
            promote_validated_candidate(
                result,
                destination_dir=tmp_path / "promoted",
                history_dir=tmp_path / "history",
                human_approved=False,
                lookup_horizon=_NEXT_DAY,
                promoter="stage-1j-test",
            )
        record = promote_validated_candidate(
            result,
            destination_dir=tmp_path / "promoted",
            history_dir=tmp_path / "history",
            human_approved=True,
            lookup_horizon=_NEXT_DAY,
            promoter="stage-1j-test",
        )
        assert record.promoted is True
        assert record.previous_path is None
        assert record.integrity
        written = json.loads(record.path.read_text(encoding="utf-8"))
        assert "refresh" not in written
        assert written["complete_through"] == "2026-09-06"
        assert "SYNTHETIC — NOT PRODUCTION DATA" in written["source"]["evidence_reference"]
        names = {p.name for p in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        assert "INE999Z01019_XNSE.json" not in names

    def test_complete_through_after_horizon_is_rejected(self, tmp_path: Path) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="SYNTH", exchange="NSE", mic="XNSE", isin="INE999Z01019"
                ),
                lookup_horizon=_HORIZON,
                observation=_synth_observation(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=CorporateActionCurrentnessEvidence(
                    events=(),
                    complete_through=date(2026, 9, 5),
                    share_count_as_of=_AS_OF,
                    source_tier="TIER_1_PRIMARY",
                    source_url="https://fixtures.dsp.test/synthetic/ca",
                    evidence_reference="SYNTHETIC outstanding completeness.",
                ),
            )
        )
        assert result.state is CoverageState.VALIDATED
        result.candidate["complete_through"] = "2026-09-06"  # type: ignore[index]
        with pytest.raises(ShareCountPromotionError):
            promote_validated_candidate(
                result,
                destination_dir=tmp_path / "promoted",
                history_dir=tmp_path / "history",
                human_approved=True,
                lookup_horizon=_HORIZON,
                promoter="stage-1j-test",
            )

    def test_rollback_preserves_previous_snapshot(self, tmp_path: Path) -> None:
        first = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="SYNTH", exchange="NSE", mic="XNSE", isin="INE999Z01019"
                ),
                lookup_horizon=_HORIZON,
                observation=_synth_observation(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=CorporateActionCurrentnessEvidence(
                    events=(),
                    complete_through=date(2026, 9, 5),
                    share_count_as_of=_AS_OF,
                    source_tier="TIER_1_PRIMARY",
                    source_url="https://fixtures.dsp.test/synthetic/ca",
                    evidence_reference="SYNTHETIC outstanding completeness.",
                ),
            )
        )
        dest = tmp_path / "promoted"
        hist = tmp_path / "history"
        first_rec = promote_validated_candidate(
            first,
            destination_dir=dest,
            history_dir=hist,
            human_approved=True,
            lookup_horizon=_HORIZON,
            promoter="stage-1j-test",
        )
        second = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="SYNTH", exchange="NSE", mic="XNSE", isin="INE999Z01019"
                ),
                lookup_horizon=_NEXT_DAY,
                observation=_synth_observation(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=CorporateActionCurrentnessEvidence(
                    events=(),
                    complete_through=date(2026, 9, 6),
                    share_count_as_of=_AS_OF,
                    source_tier="TIER_1_PRIMARY",
                    source_url="https://fixtures.dsp.test/synthetic/ca",
                    evidence_reference="SYNTHETIC outstanding completeness.",
                ),
            )
        )
        second_rec = promote_validated_candidate(
            second,
            destination_dir=dest,
            history_dir=hist,
            human_approved=True,
            lookup_horizon=_NEXT_DAY,
            promoter="stage-1j-test",
        )
        assert second_rec.previous_path is not None
        assert second_rec.previous_path.exists()
        previous = json.loads(second_rec.previous_path.read_text(encoding="utf-8"))
        assert previous["integrity"]["sha256"] == first_rec.integrity
        assert second_rec.integrity != first_rec.integrity

    def test_unknown_equity_still_fail_closed(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        unknown = Instrument(
            symbol="INFY",
            asset_class=AssetClass.EQUITY,
            currency="INR",
            exchange="NSE",
            isin="INE009A01021",
        )
        assert adapter.get_share_count(unknown) is None

    def test_production_tcs_file_unchanged_by_this_suite(self) -> None:
        snap = _tcs_snapshot()
        assert snap["integrity"]["sha256"] == _OLD_HASH
        assert snap["complete_through"] == "2026-09-05"
        assert list(DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")) == [_TCS_JSON]

    def test_award_of_order_is_non_capital(self) -> None:
        kind, changes = classify_exchange_event(
            "Announcement under Regulation 30 (LODR)-Award_of_Order_Receipt_of_Order"
        )
        assert kind == "non_capital_disclosure"
        assert changes is False
        snap = _tcs_snapshot()
        assert snap["integrity"]["sha256"] == _OLD_HASH
        assert snap["complete_through"] == "2026-09-05"
        assert list(DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")) == [_TCS_JSON]


class TestGenericity:
    def test_no_tcs_branch_in_refresh_or_promotion_source(self) -> None:
        src_root = Path(__file__).resolve().parents[1] / "src" / "dsp_platform"
        forbidden = (
            src_root / "share_count_refresh.py",
            src_root / "share_count_promotion.py",
            src_root / "share_count_source_authorization.py",
            src_root / "current_outstanding_protocol" / "ledger.py",
        )
        for path in forbidden:
            text = path.read_text(encoding="utf-8")
            assert "TCS" not in text
            assert "INE467B01029" not in text
            assert "3618087518" not in text
            assert 'symbol == "TCS"' not in text
