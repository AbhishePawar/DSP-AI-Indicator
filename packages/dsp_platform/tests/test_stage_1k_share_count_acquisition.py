"""Stage 1K — generic listed-equity share-count acquisition engine.

Synthetic fixtures are SYNTHETIC — NOT PRODUCTION DATA. TCS is the first
acceptance identity only; acquisition code has no ticker branch.
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
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    DurablePromotedShareCountAdapter,
    SHARES_OUTSTANDING_STALE,
    ShareCountResolutionError,
)
from dsp_platform.share_count_acquisition import (
    IssuerEvidenceSource,
    RecordedJsonHttp,
    ShareCountCoverageIndex,
    acquire_bse_disclosures,
    acquire_nse_disclosures,
    extract_outstanding_observation,
    refresh_from_acquired_evidence,
)
from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionRequest
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
from dsp_platform.share_count_source_authorization import (
    SOURCE_CATALOG,
    SourceAuthorityClass,
    SourceAuthorizationStatus,
    SourceRole,
    iter_sources_for_role,
)

_TCS_JSON = DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json"
_HORIZON = datetime(2026, 9, 5, 18, 7, tzinfo=UTC)
_NEXT = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)
_AS_OF = date(2026, 6, 30)
_SYNTH_ISIN = "INE999Z01019"
_SYNTH_SHARES = Decimal("1000000001")
_FAQ = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "primary_sources"
    / "TCS-IR-FAQ-outstanding-2026-06-30.txt"
)


def _tcs_identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="TCS",
        exchange="NSE",
        mic="XNSE",
        isin="INE467B01029",
        issuer="Tata Consultancy Services Limited",
    )


def _tcs_snapshot() -> dict:
    return json.loads(_TCS_JSON.read_text(encoding="utf-8"))


def _synth_identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="SYNTH",
        exchange="NSE",
        mic="XNSE",
        isin=_SYNTH_ISIN,
        issuer="SYNTHETIC — NOT PRODUCTION DATA",
    )


def _infy_identity() -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol="INFY", exchange="NSE", mic="XNSE", isin="INE009A01021"
    )


def _obs(
    *,
    shares: Decimal = _SYNTH_SHARES,
    as_of: date = _AS_OF,
    url: str = "https://fixtures.dsp.test/synthetic/outstanding",
) -> ShareCountObservation:
    return ShareCountObservation(
        shares_outstanding=shares,
        as_of=as_of,
        effective_date=as_of,
        retrieved_at=_HORIZON,
        publication_at=as_of,
        source_id="t1_issuer_disclosure",
        source_url=url,
        evidence_reference=(
            "SYNTHETIC — NOT PRODUCTION DATA. As of June 30, 2026, "
            f"outstanding shares were {shares}."
        ),
        source_tier="TIER_1_PRIMARY",
    )


def _ca(
    *,
    complete_through: date,
    events: tuple[ShareChangingCorporateAction, ...] = (),
    as_of: date = _AS_OF,
) -> CorporateActionCurrentnessEvidence:
    return CorporateActionCurrentnessEvidence(
        events=events,
        complete_through=complete_through,
        share_count_as_of=as_of,
        source_tier="TIER_1_PRIMARY",
        source_url="https://fixtures.dsp.test/corporate-actions",
        evidence_reference="DSP-attested T1 corporate-action completeness outstanding.",
    )


def _dividend() -> ShareChangingCorporateAction:
    return ShareChangingCorporateAction(
        action_type="dividend",
        effective_date=date(2026, 7, 15),
        changes_outstanding_shares=False,
    )


class TestSourceRegistry:
    def test_t1_t2_t3_t4_are_explicit(self) -> None:
        classes = {row.authority_class for row in SOURCE_CATALOG.values()}
        assert SourceAuthorityClass.T1 in classes
        assert SourceAuthorityClass.T2 in classes
        assert SourceAuthorityClass.T3 in classes
        assert SourceAuthorityClass.T4 in classes
        assert SOURCE_CATALOG["twelve_data_statistics"].status is (
            SourceAuthorizationStatus.PENDING
        )
        assert SOURCE_CATALOG["gemini_grounding"].authority_class is (
            SourceAuthorityClass.T3
        )
        approved = iter_sources_for_role(
            SourceRole.SHARE_COUNT_OBSERVATION,
            status=SourceAuthorizationStatus.APPROVED,
        )
        assert any(row.source_id == "t1_issuer_disclosure" for row in approved)
        assert all(
            row.source_id != "twelve_data_statistics" for row in approved
        )


class TestFixturesAtoE:
    def test_fixture_a_current_at_complete_through(self) -> None:
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
        assert result.shares_outstanding == Decimal("3618087518")
        assert result.candidate is None

    def test_fixture_b_stale_after_complete_through(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_NEXT,
                current_snapshot=_tcs_snapshot(),
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 5), events=(_dividend(),)
                ),
            )
        )
        assert result.state is CoverageState.STALE
        with pytest.raises(ShareCountPromotionError):
            promote_validated_candidate(
                result,
                destination_dir=Path("."),
                history_dir=Path("."),
                human_approved=True,
                lookup_horizon=_NEXT,
                promoter="stage-1k",
            )

    def test_fixture_c_unresolved_bonus_is_refresh_pending(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_synth_identity(),
                lookup_horizon=_NEXT,
                observation=_obs(),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=_ca(
                    complete_through=date(2026, 9, 6),
                    events=(
                        ShareChangingCorporateAction(
                            action_type="bonus",
                            effective_date=date(2026, 8, 1),
                            changes_outstanding_shares=True,
                            already_reflected_in_share_count=False,
                        ),
                    ),
                ),
            )
        )
        assert result.state is CoverageState.REFRESH_PENDING
        assert result.candidate is None

    def test_fixture_d_reflected_issuance_validates_new_count(self, tmp_path: Path) -> None:
        new_shares = Decimal("1100000001")
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_synth_identity(),
                lookup_horizon=_NEXT,
                observation=_obs(shares=new_shares, as_of=date(2026, 8, 1)),
                observation_source_id="t1_issuer_disclosure",
                corporate_action_evidence=_ca(
                    as_of=date(2026, 8, 1),
                    complete_through=date(2026, 9, 6),
                    events=(
                        ShareChangingCorporateAction(
                            action_type="new_issue",
                            effective_date=date(2026, 8, 1),
                            changes_outstanding_shares=True,
                            already_reflected_in_share_count=True,
                            description="SYNTHETIC — NOT PRODUCTION DATA issuance",
                        ),
                    ),
                ),
            )
        )
        assert result.state is CoverageState.VALIDATED
        assert result.shares_outstanding == new_shares
        assert result.candidate is not None
        record = promote_validated_candidate(
            result,
            destination_dir=tmp_path / "promoted",
            history_dir=tmp_path / "history",
            human_approved=True,
            lookup_horizon=_NEXT,
            promoter="stage-1k-test",
        )
        assert record.promoted is True
        names = {p.name for p in DEFAULT_PROMOTED_SHARE_COUNT_DIR.glob("*.json")}
        assert "INE999Z01019_XNSE.json" not in names

    def test_fixture_e_conflict_cannot_promote(self) -> None:
        result = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
                observation=_obs(
                    shares=Decimal("9"),
                    url="https://www.tcs.com/investor-relations/investor-faqs",
                ),
                observation_source_id="t1_issuer_disclosure",
            )
        )
        assert result.state is CoverageState.INVALID
        assert "conflict" in result.reason
        with pytest.raises(ShareCountPromotionError):
            promote_validated_candidate(
                result,
                destination_dir=Path("."),
                history_dir=Path("."),
                human_approved=True,
                lookup_horizon=_HORIZON,
                promoter="stage-1k",
            )


class TestNseBseAcquisition:
    def test_nse_paginates_and_filters_identity(self) -> None:
        identity = _synth_identity()
        start, end = date(2026, 6, 30), date(2026, 9, 5)
        ca_url = (
            "https://www.nseindia.com/api/corporates-corporateActions"
            "?index=equities&symbol=SYNTH&from_date=30-06-2026&to_date=05-09-2026"
        )
        http = RecordedJsonHttp(
            {
                ca_url: [
                    {
                        "symbol": "SYNTH",
                        "isin": _SYNTH_ISIN,
                        "subject": "Interim Dividend - Rs 1",
                        "exDate": "15-Jul-2026",
                        "comp": "SYNTHETIC — NOT PRODUCTION DATA",
                    },
                    {
                        "symbol": "OTHER",
                        "isin": "INE000A01000",
                        "subject": "Bonus 1:1",
                        "exDate": "01-Aug-2026",
                    },
                ],
                "corporate-announcements": [
                    {
                        "symbol": "SYNTH",
                        "isin": _SYNTH_ISIN,
                        "desc": "Press Release",
                        "attchmntText": "ordinary update",
                    }
                ],
            }
        )
        bundle = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=start,
                end=end,
                retrieved_at=_HORIZON,
            ),
            http,
        )
        assert bundle.pagination_exhausted is True
        assert bundle.truncated is False
        assert len(bundle.corporate_actions) == 1
        assert bundle.corporate_actions[0]["isin"] == _SYNTH_ISIN
        assert all(item.get("symbol") != "OTHER" for item in bundle.corporate_actions)

    def test_nse_missing_page_is_not_exhausted(self) -> None:
        http = RecordedJsonHttp({})
        bundle = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=_synth_identity(),
                start=date(2026, 6, 30),
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
            ),
            http,
        )
        assert bundle.pagination_exhausted is False

    def test_bse_fetches_until_short_page(self) -> None:
        page1 = [{"HEADLINE": f"item-{i}", "SCRIP_CD": 999999} for i in range(50)]
        page2 = [{"HEADLINE": "last", "SCRIP_CD": 999999}]
        http = RecordedJsonHttp(
            {
                "pageno=1": {"Table": page1},
                "pageno=2": {"Table": page2},
            }
        )
        bundle = acquire_bse_disclosures(
            ExchangeAcquisitionRequest(
                identity=_synth_identity(),
                start=date(2026, 6, 30),
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
                scrip_code="999999",
            ),
            http,
        )
        assert bundle.pagination_exhausted is True
        assert bundle.record_count == 51
        assert "pageno=1" in "".join(http.calls)
        assert "pageno=2" in "".join(http.calls)

    def test_bse_requires_scrip_code(self) -> None:
        bundle = acquire_bse_disclosures(
            ExchangeAcquisitionRequest(
                identity=_synth_identity(),
                start=date(2026, 6, 30),
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
            ),
            RecordedJsonHttp({}),
        )
        assert bundle.pagination_exhausted is False
        assert bundle.record_count == 0


class TestIssuerExtraction:
    def test_explicit_outstanding_sentence(self) -> None:
        if not _FAQ.exists():
            pytest.skip("TCS IR fixture not present")
        source = IssuerEvidenceSource(
            identity=_tcs_identity(),
            ir_url="https://www.tcs.com/investor-relations/investor-faqs",
            issuer_name="Tata Consultancy Services Limited",
        )
        observation = extract_outstanding_observation(
            source,
            document_text=_FAQ.read_text(encoding="utf-8"),
            retrieved_at=_HORIZON,
            publication_at=date(2026, 6, 30),
        )
        assert observation is not None
        assert observation.shares_outstanding == Decimal("3618087518")
        assert observation.as_of == date(2026, 6, 30)
        assert observation.retrieved_at.date() != observation.as_of or (
            observation.publication_at == date(2026, 6, 30)
        )

    def test_float_and_was_rejected(self) -> None:
        source = IssuerEvidenceSource(
            identity=_synth_identity(),
            ir_url="https://fixtures.dsp.test/synthetic/outstanding",
            issuer_name="SYNTHETIC — NOT PRODUCTION DATA",
        )
        assert (
            extract_outstanding_observation(
                source,
                document_text="Free float shares outstanding were 1,000 shares as of June 30, 2026.",
                retrieved_at=_HORIZON,
            )
            is None
        )
        assert (
            extract_outstanding_observation(
                source,
                document_text=(
                    "Weighted-average shares outstanding were 1,000,000,001 "
                    "as of June 30, 2026."
                ),
                retrieved_at=_HORIZON,
            )
            is None
        )


class TestPipelineAndCoverage:
    def test_nse_bundle_feeds_generic_refresh(self) -> None:
        identity = _synth_identity()
        http = RecordedJsonHttp(
            {
                "corporateActions": [
                    {
                        "symbol": "SYNTH",
                        "isin": _SYNTH_ISIN,
                        "subject": "Interim Dividend - Rs 1",
                        "exDate": "15-Jul-2026",
                        "comp": "SYNTHETIC — NOT PRODUCTION DATA",
                    }
                ],
                "corporate-announcements": [],
            }
        )
        nse = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=_AS_OF,
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
            ),
            http,
        )
        result = refresh_from_acquired_evidence(
            identity=identity,
            lookup_horizon=_HORIZON,
            observation=_obs(),
            nse_bundle=nse,
        )
        assert result.state is CoverageState.VALIDATED
        assert result.candidate is not None
        assert result.candidate["refresh"]["human_promotion_required"] is True

    def test_coverage_index_multi_equity(self) -> None:
        tcs_key = "INE467B01029_XNSE"
        index = ShareCountCoverageIndex.evaluate(
            (_tcs_identity(), _infy_identity(), _synth_identity()),
            lookup_horizon=_HORIZON,
            snapshots={tcs_key: _tcs_snapshot()},
        )
        by_isin = {row.identity.isin: row for row in index.rows}
        assert by_isin["INE467B01029"].state is CoverageState.CURRENT
        assert by_isin["INE009A01021"].state is CoverageState.DISCOVERED
        assert by_isin[_SYNTH_ISIN].state is CoverageState.DISCOVERED
        assert index.current()[0].identity.isin == "INE467B01029"
        assert any(row.identity.isin == "INE009A01021" for row in index.need_evidence())
        assert index.stale() == ()

    def test_coverage_stale_and_unknown(self) -> None:
        index = ShareCountCoverageIndex.evaluate(
            (_tcs_identity(), InstrumentIdentity(symbol="", exchange="", mic="", isin="")),
            lookup_horizon=_NEXT,
            snapshots={"INE467B01029_XNSE": _tcs_snapshot()},
        )
        assert index.stale()[0].identity.isin == "INE467B01029"
        assert index.unsupported()[0].state is CoverageState.UNKNOWN


class TestRuntimeAcceptance:
    def test_tcs_promoted_snapshot_accepted(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        snap = adapter.get_share_count(
            Instrument(
                symbol="TCS",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="NSE",
                isin="INE467B01029",
            )
        )
        assert snap is not None
        assert int(snap.shares_value() or 0) == 3618087518

    def test_infy_fail_closed(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _HORIZON)
        assert (
            adapter.get_share_count(
                Instrument(
                    symbol="INFY",
                    asset_class=AssetClass.EQUITY,
                    currency="INR",
                    exchange="NSE",
                    isin="INE009A01021",
                )
            )
            is None
        )

    def test_future_horizon_stale(self) -> None:
        adapter = DurablePromotedShareCountAdapter(now=lambda: _NEXT)
        with pytest.raises(ShareCountResolutionError, match=SHARES_OUTSTANDING_STALE):
            adapter.get_share_count(
                Instrument(
                    symbol="TCS",
                    asset_class=AssetClass.EQUITY,
                    currency="INR",
                    exchange="NSE",
                    isin="INE467B01029",
                )
            )

    def test_identity_mismatch_and_tamper(self) -> None:
        bad_isin = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="NSE", mic="XNSE", isin="INE009A01021"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=_tcs_snapshot(),
            )
        )
        tampered = _tcs_snapshot()
        tampered["shares_outstanding"] = "1"
        tamper = refresh_share_count(
            ShareCountRefreshRequest(
                identity=_tcs_identity(),
                lookup_horizon=_HORIZON,
                current_snapshot=tampered,
            )
        )
        assert bad_isin.state is CoverageState.INVALID
        assert tamper.state is CoverageState.INVALID

    def test_no_tcs_branch_in_generic_engine(self) -> None:
        src = Path(__file__).resolve().parents[1] / "src" / "dsp_platform"
        roots = (
            src / "share_count_acquisition",
            src / "share_count_refresh.py",
            src / "share_count_promotion.py",
            src / "share_count_source_authorization.py",
            src / "current_outstanding_protocol" / "queries.py",
            src / "current_outstanding_protocol" / "ledger.py",
            src / "current_outstanding_protocol" / "currentness.py",
        )
        files: list[Path] = []
        for root in roots:
            if root.is_dir():
                files.extend(root.glob("*.py"))
            else:
                files.append(root)
        for path in files:
            text = path.read_text(encoding="utf-8")
            assert "TCS" not in text, path
            assert "INE467B01029" not in text, path
            assert "3618087518" not in text, path
            assert 'symbol == "TCS"' not in text, path
            assert "tata consultancy" not in text.lower(), path
