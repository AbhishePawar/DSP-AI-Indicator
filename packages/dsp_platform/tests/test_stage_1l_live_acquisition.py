"""Stage 1L — live T1 acquisition, coverage, and explicit promotion.

Live network tests are opt-in via DSP_LIVE_T1=1. Recorded tests stay offline.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from dsp_platform.current_outstanding_protocol.ledger import classify_exchange_event
from dsp_platform.promoted_share_count import (
    DEFAULT_PROMOTED_SHARE_COUNT_DIR,
    DurablePromotedShareCountAdapter,
)
from dsp_platform.share_count_acquisition.artifacts import public_json
from dsp_platform.share_count_acquisition.http import RecordedJsonHttp
from dsp_platform.share_count_acquisition.live_http import AllowlistedLiveJsonHttp
from dsp_platform.share_count_acquisition.operator import (
    acquire_listed_equity,
    promote_candidate_file,
)
from dsp_platform.share_count_acquisition.policy import (
    ConnectorAvailability,
    iter_source_policy,
    policy_for,
)
from dsp_platform.share_count_acquisition.universe import get_listed_equity, iter_listed_equities
from dsp_platform.share_count_acquisition.__main__ import main
from dsp_platform.share_count_promotion import ShareCountPromotionError
from dsp_platform.share_count_refresh import (
    CoverageState,
    InstrumentIdentity,
    ShareCountRefreshRequest,
    refresh_share_count,
)
from dsp_platform.share_count_source_authorization import SourceAuthorityClass

_HORIZON = datetime(2026, 9, 6, 9, 0, tzinfo=UTC)


def _recorded_http() -> RecordedJsonHttp:
    return RecordedJsonHttp(
        {
            "corporateActions": [
                {
                    "symbol": "TCS",
                    "isin": "INE467B01029",
                    "subject": "Interim Dividend - Rs 12 Per Share",
                    "exDate": "15-Jul-2026",
                    "comp": "Tata Consultancy Services Limited",
                }
            ],
            "corporate-announcements": [
                {
                    "symbol": "TCS",
                    "isin": "INE467B01029",
                    "desc": "General Updates",
                    "attchmntText": "Press release",
                }
            ],
            "AnnSubCategoryGetData": {"Table": []},
        }
    )


class TestUniverseAndPolicy:
    def test_catalog_is_isin_mic_and_covers_required_names(self) -> None:
        rows = {row.identity.symbol: row for row in iter_listed_equities()}
        assert set(rows) >= {"TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"}
        tcs = get_listed_equity("INE467B01029", "XNSE")
        assert tcs is not None
        assert tcs.identity.mic == "XNSE"
        assert get_listed_equity("INE009A01021", "XNAS") is None

    def test_predecessor_isin_accepted_for_symbol_scoped_nse(self) -> None:
        from dsp_platform.share_count_acquisition.nse import acquire_nse_disclosures
        from dsp_platform.share_count_acquisition.models import ExchangeAcquisitionRequest
        from dsp_platform.share_count_refresh import InstrumentIdentity

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
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
            ),
            http,
        )
        accepted = acquire_nse_disclosures(
            ExchangeAcquisitionRequest(
                identity=identity,
                start=date(2026, 1, 1),
                end=date(2026, 9, 5),
                retrieved_at=_HORIZON,
                equivalent_isins=("INE040A01018",),
            ),
            http,
        )
        assert rejected.record_count == 0
        assert accepted.record_count == 1

    def test_unknown_equity_fail_closed(self) -> None:
        run = acquire_listed_equity(
            isin="INE000000000",
            mic="XNSE",
            lookup_horizon=_HORIZON,
            http=_recorded_http(),
            fetch_issuer=False,
        )
        assert run.state is CoverageState.UNKNOWN
        assert run.candidate is None

    def test_source_policy_distinguishes_available_from_pending(self) -> None:
        nse = policy_for("nse_public_api_connector")
        issuer = policy_for("t1_issuer_disclosure")
        gemini = policy_for("gemini_grounding")
        assert nse is not None
        assert nse.availability is ConnectorAvailability.PENDING_AUTHORIZATION
        assert nse.tier is SourceAuthorityClass.T1
        assert issuer is not None
        assert issuer.availability is ConnectorAvailability.AVAILABLE
        assert gemini is not None
        assert gemini.availability is ConnectorAvailability.REJECTED
        assert all(row.source_id for row in iter_source_policy())


class TestSecurity:
    def test_live_http_rejects_non_allowlisted_and_localhost(self) -> None:
        client = AllowlistedLiveJsonHttp()
        assert client.get_json("https://example.com/api") is None
        assert client.get_json("http://127.0.0.1/") is None
        assert client.get_json("https://localhost/secret") is None
        errors = [row["error"] or "" for row in client.public_traces()]
        blob = " ".join(errors).lower()
        assert "allowlisted" in blob or "https" in blob or "blocked" in blob
        serialized = json.dumps(client.public_traces())
        assert "cookie" not in serialized.lower()
        assert "set-cookie" not in serialized.lower()

    def test_artifacts_strip_secrets(self) -> None:
        cleaned = public_json(
            {
                "url": "https://www.nseindia.com/api/x",
                "cookie": "session=secret",
                "authorization": "Bearer secret",
                "ok": True,
            }
        )
        encoded = json.dumps(cleaned).lower()
        assert "session=secret" not in encoded
        assert "bearer secret" not in encoded
        assert "artifact_integrity" in cleaned


class TestCorporateActionMatrix:
    @pytest.mark.parametrize(
        ("text", "expected", "changes"),
        [
            ("Stock split 1:1", "stock_split", True),
            ("Reverse split of equity shares", "reverse_split", True),
            ("Bonus issue of equity shares", "bonus_issue", True),
            ("Rights issue of equity shares", "rights_issue", True),
            ("Fresh issue of equity shares", "new_issue", True),
            ("Buyback of equity shares", "buyback", True),
            ("Cancellation of shares", "cancellation", True),
            ("Scheme of merger of equity shares", "merger", True),
            ("Demerger of equity shares", "demerger", True),
            ("Conversion of warrants into equity shares", "conversion", True),
            ("Treasury share change", "treasury", True),
            ("Interim Dividend - Rs 12 Per Share", "dividend", False),
            ("Acquisition for cash consideration", "acquisition_cash", False),
            ("Board meeting", "non_capital_disclosure", False),
            ("Symbol change of the company", "symbol_change", False),
        ],
    )
    def test_classification(self, text: str, expected: str, changes: bool) -> None:
        event_type, flag = classify_exchange_event(text)
        assert event_type == expected
        assert flag is changes


class TestRecordedAcquisitionAndPromotion:
    def test_tcs_recorded_path_can_validate(self, tmp_path: Path) -> None:
        run = acquire_listed_equity(
            isin="INE467B01029",
            mic="XNSE",
            lookup_horizon=_HORIZON,
            http=_recorded_http(),
            artifact_dir=tmp_path,
            fetch_issuer=False,
        )
        assert run.state in {CoverageState.VALIDATED, CoverageState.CURRENT}
        assert run.production_written is False
        assert run.artifact_path is not None
        payload = json.loads(run.artifact_path.read_text(encoding="utf-8"))
        assert "cookie" not in json.dumps(payload).lower()
        if run.state is CoverageState.CURRENT:
            with pytest.raises(ShareCountPromotionError):
                promote_candidate_file(
                    run.artifact_path,
                    destination_dir=tmp_path / "prod",
                    history_dir=tmp_path / "hist",
                    promoter="stage-1l",
                    human_approved=True,
                    lookup_horizon=_HORIZON,
                )
            return
        first = promote_candidate_file(
            run.artifact_path,
            destination_dir=tmp_path / "prod",
            history_dir=tmp_path / "hist",
            promoter="stage-1l",
            human_approved=True,
            lookup_horizon=_HORIZON,
        )
        assert first.promoted is True
        with pytest.raises(ShareCountPromotionError):
            promote_candidate_file(
                run.artifact_path,
                destination_dir=tmp_path / "prod",
                history_dir=tmp_path / "hist",
                promoter="stage-1l",
                human_approved=True,
                lookup_horizon=_HORIZON,
            )

    def test_stale_cannot_promote(self, tmp_path: Path) -> None:
        artifact = tmp_path / "stale.json"
        artifact.write_text(
            json.dumps(
                {
                    "candidate_state": "STALE",
                    "option_b": {"state": "STALE", "reason": "horizon not covered"},
                    "candidate": {"refresh": {"human_promotion_required": True}},
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ShareCountPromotionError):
            promote_candidate_file(
                artifact,
                destination_dir=tmp_path,
                history_dir=tmp_path,
                promoter="stage-1l",
                human_approved=True,
                lookup_horizon=_HORIZON,
            )

    def test_identity_mismatch_and_tamper_invalid(self) -> None:
        snapshot = json.loads(
            (DEFAULT_PROMOTED_SHARE_COUNT_DIR / "INE467B01029_XNSE.json").read_text(
                encoding="utf-8"
            )
        )
        bad = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="NSE", mic="XNSE", isin="INE009A01021"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=snapshot,
            )
        )
        snapshot["shares_outstanding"] = "1"
        tamper = refresh_share_count(
            ShareCountRefreshRequest(
                identity=InstrumentIdentity(
                    symbol="TCS", exchange="NSE", mic="XNSE", isin="INE467B01029"
                ),
                lookup_horizon=_HORIZON,
                current_snapshot=snapshot,
            )
        )
        assert bad.state is CoverageState.INVALID
        assert tamper.state is CoverageState.INVALID

    def test_dual_listing_mic_equivalence(self) -> None:
        adapter = DurablePromotedShareCountAdapter(
            now=lambda: datetime(2026, 9, 5, 18, 7, tzinfo=UTC)
        )
        snap = adapter.get_share_count(
            Instrument(
                symbol="TCS",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="BSE",
                isin="INE467B01029",
            )
        )
        assert snap is not None
        assert int(snap.shares_value() or 0) == 3618087518

    def test_cli_sources_and_dry_unknown(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["sources"]) == 0
        out = capsys.readouterr().out
        assert "nse_public_api_connector" in out
        assert main(["acquire", "--isin", "INE000000000", "--mic", "XNSE", "--no-issuer"]) == 2


class TestRuntimeFailClosed:
    def test_infy_without_snapshot_is_none(self) -> None:
        adapter = DurablePromotedShareCountAdapter(
            now=lambda: datetime(2026, 9, 5, 18, 7, tzinfo=UTC)
        )
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


@pytest.mark.skipif(os.environ.get("DSP_LIVE_T1") != "1", reason="live T1 opt-in")
def test_live_universe_opt_in() -> None:
    from dsp_platform.share_count_acquisition.operator import acquire_universe

    runs = acquire_universe(lookup_horizon=datetime.now(tz=UTC), fetch_issuer=False)
    assert len(runs) >= 5
    assert all(run.production_written is False for run in runs)
