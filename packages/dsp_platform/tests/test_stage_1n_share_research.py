"""Stage 1N — generic client share-research engine."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.market_quote.service import is_provider_circuit_failure
from data_engine.exceptions import DataValidationError, ProviderRequestError

from dsp_platform.promoted_share_count import ShareCountResolutionError
from dsp_platform.share_research.engine import ShareResearchEngine
from dsp_platform.share_research.gemini import (
    FixedShareResearchGemini,
    ShareResearchGeminiError,
)
from dsp_platform.share_research.models import (
    ShareResearchCheck,
    ShareResearchCorporateAction,
    ShareResearchRecord,
    ShareResearchRequest,
    ShareResearchSource,
    ShareResearchStatus,
)
from dsp_platform.share_research.overlay import current_share_research_snapshot
from dsp_platform.share_research.store import ShareResearchStore

_HORIZON = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
_TCS_SHARES = Decimal("3618087518")
_INFY_SHARES = Decimal("4049645811")
_RIL_SHARES = Decimal("13532634002")


def _ok_payload(
    ticker: str,
    isin: str,
    exchange: str,
    mic: str,
    company: str,
    shares: int,
    source_1: str,
    source_2: str,
    as_of: str = "2026-06-30",
    through: str = "2026-09-06",
    actions: list[object] | None = None,
    status: str = "CURRENT",
) -> dict:
    return {
        "STATUS": status,
        "COMPANY": company,
        "TICKER": ticker,
        "ISIN": isin,
        "EXCHANGE": exchange,
        "MIC": mic,
        "SECURITY_TYPE": "common_equity",
        "OUTSTANDING_SHARES": shares,
        "AS_OF": as_of,
        "CURRENT_THROUGH": through,
        "NEW_PRIMARY_SOURCE_1": source_1,
        "NEW_PRIMARY_SOURCE_2": source_2,
        "SOURCE_URLS": [source_1, source_2],
        "CORPORATE_ACTION_CHECK": "PASS",
        "CORPORATE_ACTIONS_FOUND": actions
        if actions is not None
        else [{"description": "Interim Dividend - Rs 12 Per Share", "effective_date": "2026-07-15"}],
        "SHARE_COUNT_EFFECT": "NONE",
        "IDENTITY_CHECK": "PASS",
        "CROSS_CHECK": "PASS",
        "CONFIDENCE": "HIGH",
        "EVIDENCE": ["official outstanding disclosure"],
        "CA_COVERAGE_START": as_of,
        "CA_COVERAGE_END": through,
        "CA_PAGINATION_EXHAUSTED": True,
        "CA_SOURCE_URL": source_2,
        "UNRESOLVED_ISSUES": [],
    }


def _tcs_payload(**overrides: object) -> dict:
    payload = _ok_payload(
        ticker="TCS",
        isin="INE467B01029",
        exchange="NSE",
        mic="XNSE",
        company="Tata Consultancy Services Limited",
        shares=3618087518,
        source_1="https://www.tcs.com/investor-relations/investor-faqs",
        source_2="https://www.nseindia.com/get-quotes/equity?symbol=TCS",
    )
    payload.update(overrides)
    return payload


def _engine(tmp_path: Path, gemini) -> ShareResearchEngine:
    return ShareResearchEngine(
        store=ShareResearchStore(tmp_path / "share_research"),
        gemini=gemini,
    )


def _current_record(*, shares: Decimal = _TCS_SHARES, through: str = "2026-09-06") -> ShareResearchRecord:
    now = _HORIZON
    return ShareResearchRecord(
        research_id="rec-current",
        company_name="Tata Consultancy Services Limited",
        ticker="TCS",
        isin="INE467B01029",
        exchange="NSE",
        mic="XNSE",
        security_type="common_equity",
        outstanding_shares=shares,
        as_of=date(2026, 6, 30),
        effective_date=date(2026, 6, 30),
        current_through=date.fromisoformat(through),
        researched_at=now,
        last_verified_at=now,
        status=ShareResearchStatus.CURRENT,
        stored_previous_share_count=None,
        stored_previous_as_of=None,
        stored_previous_current_through=None,
        primary_sources=(
            ShareResearchSource(
                url="https://www.tcs.com/investor-relations/investor-faqs",
                label="tcs.com",
                accepted=True,
                reason="issuer official host",
            ),
            ShareResearchSource(
                url="https://www.nseindia.com/get-quotes/equity?symbol=TCS",
                label="nseindia.com",
                accepted=True,
                reason="approved primary host",
            ),
        ),
        evidence=("stored current outstanding",),
        corporate_actions=(
            ShareResearchCorporateAction(
                action_type="dividend",
                description="Interim Dividend - Rs 12 Per Share",
                effective_date=date(2026, 7, 15),
                changes_outstanding_shares=False,
            ),
        ),
        share_count_effect="NONE",
        identity_check=ShareResearchCheck.PASS,
        cross_check=ShareResearchCheck.PASS,
        corporate_action_check=ShareResearchCheck.PASS,
        confidence="HIGH",
        gemini_invoked=True,
        gemini_research_reference="prior",
        integrity_hash="abc",
        valuation_eligible=True,
        unresolved_issues=(),
        created_at=now,
        updated_at=now,
        reason="proven",
        stored_record_status="CURRENT",
    )


class TestShareResearchEngine:
    def test_a_stored_current_skips_gemini(self, tmp_path: Path) -> None:
        gemini = FixedShareResearchGemini(_tcs_payload())
        engine = _engine(tmp_path, gemini)
        engine._store.save(_current_record())
        result = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.CURRENT
        assert result.gemini_invoked is False
        assert gemini.calls == 0
        assert result.record.valuation_eligible is True
        assert result.record.outstanding_shares == _TCS_SHARES

    def test_b_stored_stale_invokes_gemini(self, tmp_path: Path) -> None:
        gemini = FixedShareResearchGemini(_tcs_payload())
        engine = _engine(tmp_path, gemini)
        engine._store.save(_current_record(through="2026-09-05"))
        result = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert gemini.calls == 1
        assert result.gemini_invoked is True
        assert result.record.status is ShareResearchStatus.CURRENT

    def test_c_fresh_confirms_stored_preserves_history(self, tmp_path: Path) -> None:
        gemini = FixedShareResearchGemini(_tcs_payload())
        engine = _engine(tmp_path, gemini)
        engine._store.save(_current_record(through="2026-09-05"))
        result = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        client = result.to_client_dict()
        assert client["stored_vs_fresh"]["result"] == "MATCH"
        assert result.history
        assert result.history[0]["research_id"] == "rec-current"

    def test_d_changed_count_preserves_old_record(self, tmp_path: Path) -> None:
        payload = _tcs_payload(OUTSTANDING_SHARES=3618087519, AS_OF="2026-09-01")
        engine = _engine(tmp_path, FixedShareResearchGemini(payload))
        engine._store.save(_current_record(through="2026-09-05"))
        result = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.outstanding_shares == Decimal("3618087519")
        assert result.record.stored_previous_share_count == _TCS_SHARES
        assert result.history[0]["outstanding_shares"] == str(_TCS_SHARES)
        assert result.record.status is ShareResearchStatus.CURRENT
        assert result.record.valuation_eligible is True

    def test_e_share_changing_event_after_as_of_blocks(self, tmp_path: Path) -> None:
        payload = _tcs_payload(
            CORPORATE_ACTIONS_FOUND=[
                {
                    "description": "Bonus issue 1:1",
                    "effective_date": "2026-08-01",
                }
            ]
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.REFRESH_REQUIRED
        assert result.record.valuation_eligible is False

    def test_e_bonus_reflected_in_later_as_of(self, tmp_path: Path) -> None:
        payload = _tcs_payload(
            OUTSTANDING_SHARES=7236175036,
            AS_OF="2026-08-15",
            CORPORATE_ACTIONS_FOUND=[
                {"description": "Bonus issue 1:1", "effective_date": "2026-08-01"}
            ],
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.CURRENT
        assert result.record.outstanding_shares == Decimal("7236175036")
        assert result.record.valuation_eligible is True

    def test_f_ambiguous_acquisition_blocks(self, tmp_path: Path) -> None:
        payload = _tcs_payload(
            CORPORATE_ACTIONS_FOUND=[{"description": "Acquisition", "effective_date": "2026-08-24"}]
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.UNKNOWN
        assert result.record.valuation_eligible is False

    def test_g_conflicting_primary_sources(self, tmp_path: Path) -> None:
        payload = _tcs_payload(STATUS="CONFLICT")
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.CONFLICT
        assert result.record.valuation_eligible is False

    def test_h_secondary_only_not_sufficient(self, tmp_path: Path) -> None:
        payload = _tcs_payload(
            NEW_PRIMARY_SOURCE_1="https://www.screener.in/company/TCS/",
            NEW_PRIMARY_SOURCE_2="https://finance.yahoo.com/quote/TCS.NS",
            SOURCE_URLS=[
                "https://www.screener.in/company/TCS/",
                "https://finance.yahoo.com/quote/TCS.NS",
            ],
            CA_SOURCE_URL="https://www.screener.in/company/TCS/",
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is not ShareResearchStatus.CURRENT
        assert result.record.valuation_eligible is False
        assert result.record.cross_check is ShareResearchCheck.FAIL

    def test_i_malformed_gemini_json(self, tmp_path: Path) -> None:
        gemini = FixedShareResearchGemini(kind="malformed", message="bad json")
        result = _engine(tmp_path, gemini).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.INVALID
        assert result.record.valuation_eligible is False

    def test_j_wrong_isin(self, tmp_path: Path) -> None:
        payload = _tcs_payload(ISIN="INE009A01021")
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.INVALID
        assert result.record.identity_check is ShareResearchCheck.FAIL
        assert result.record.valuation_eligible is False

    def test_j_wrong_company(self, tmp_path: Path) -> None:
        payload = _tcs_payload(COMPANY="Infosys Limited")
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.INVALID
        assert result.record.identity_check is ShareResearchCheck.FAIL
        assert result.record.valuation_eligible is False

    def test_j_wrong_exchange(self, tmp_path: Path) -> None:
        payload = _tcs_payload(EXCHANGE="NYSE", MIC="XNYS")
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.INVALID
        assert result.record.identity_check is ShareResearchCheck.FAIL
        assert result.record.valuation_eligible is False

    def test_missing_as_of(self, tmp_path: Path) -> None:
        payload = _tcs_payload(AS_OF=None)
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.UNKNOWN
        assert result.record.valuation_eligible is False

    def test_fabricated_market_cap_language(self, tmp_path: Path) -> None:
        payload = _tcs_payload(EVIDENCE=["implied shares from market cap"])
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.UNKNOWN
        assert result.record.valuation_eligible is False

    def test_stale_ca_coverage(self, tmp_path: Path) -> None:
        payload = _tcs_payload(
            CURRENT_THROUGH="2026-09-01",
            CA_COVERAGE_END="2026-09-01",
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.REFRESH_REQUIRED
        assert result.record.valuation_eligible is False

    def test_k_nse_bse_same_isin_not_duplicated(self, tmp_path: Path) -> None:
        gemini = FixedShareResearchGemini(_tcs_payload())
        engine = _engine(tmp_path, gemini)
        first = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        second = engine.research(
            ShareResearchRequest(ticker="TCS", exchange="BSE", lookup_horizon=_HORIZON)
        )
        assert first.record.isin == second.record.isin == "INE467B01029"
        assert gemini.calls == 1
        assert second.gemini_invoked is False

    def test_l_no_share_count(self, tmp_path: Path) -> None:
        payload = _tcs_payload(OUTSTANDING_SHARES=None)
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.status is ShareResearchStatus.UNKNOWN
        assert result.record.valuation_eligible is False

    def test_infy_generic_fixture(self, tmp_path: Path) -> None:
        payload = _ok_payload(
            ticker="INFY",
            isin="INE009A01021",
            exchange="NSE",
            mic="XNSE",
            company="Infosys Limited",
            shares=4049645811,
            source_1="https://www.infosys.com/investors/shares/share-details.html",
            source_2="https://www.nseindia.com/get-quotes/equity?symbol=INFY",
            actions=[{"description": "Dividend - Rs 25 Per Share", "effective_date": "2026-06-04"}],
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="INFY", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.ticker == "INFY"
        assert result.record.outstanding_shares == _INFY_SHARES
        assert result.record.status is ShareResearchStatus.CURRENT

    def test_reliance_generic_fixture(self, tmp_path: Path) -> None:
        payload = _ok_payload(
            ticker="RELIANCE",
            isin="INE002A01018",
            exchange="NSE",
            mic="XNSE",
            company="Reliance Industries Limited",
            shares=13532634002,
            source_1="https://www.ril.com/investors",
            source_2="https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE",
        )
        result = _engine(tmp_path, FixedShareResearchGemini(payload)).research(
            ShareResearchRequest(ticker="RELIANCE", exchange="NSE", lookup_horizon=_HORIZON)
        )
        assert result.record.ticker == "RELIANCE"
        assert result.record.outstanding_shares == _RIL_SHARES
        assert result.record.status is ShareResearchStatus.CURRENT

    def test_no_tcs_special_case_in_engine_source(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src/dsp_platform/share_research"
        blob = "\n".join(path.read_text(encoding="utf-8") for path in source.glob("*.py"))
        assert "if ticker == \"TCS\"" not in blob
        assert "INE467B01029" not in blob
        assert "3618087518" not in blob

    def test_master_policy_forbids_investment_outputs(self) -> None:
        from dsp_platform.share_research.policy import SHARE_RESEARCH_MASTER_POLICY

        policy = SHARE_RESEARCH_MASTER_POLICY
        for token in (
            "BUY",
            "SELL",
            "intrinsic value",
            "margin of safety",
            "DCF",
            "investment recommendation",
            "ISIN",
            "primary",
            "corporate action",
        ):
            assert token in policy


class TestGeminiFailures:
    @pytest.mark.parametrize(
        ("kind", "status"),
        [
            ("timeout", ShareResearchStatus.REFRESH_REQUIRED),
            ("rate_limited", ShareResearchStatus.REFRESH_REQUIRED),
            ("http_5xx", ShareResearchStatus.REFRESH_REQUIRED),
            ("http_4xx", ShareResearchStatus.REFRESH_REQUIRED),
            ("http_401", ShareResearchStatus.REFRESH_REQUIRED),
            ("http_403", ShareResearchStatus.REFRESH_REQUIRED),
            ("http_404", ShareResearchStatus.REFRESH_REQUIRED),
            ("transport", ShareResearchStatus.REFRESH_REQUIRED),
            ("empty", ShareResearchStatus.REFRESH_REQUIRED),
            ("tool_only", ShareResearchStatus.REFRESH_REQUIRED),
            ("unavailable", ShareResearchStatus.REFRESH_REQUIRED),
            ("malformed", ShareResearchStatus.INVALID),
        ],
    )
    def test_provider_failures_fail_closed(
        self, tmp_path: Path, kind: str, status: ShareResearchStatus
    ) -> None:
        result = _engine(
            tmp_path, FixedShareResearchGemini(kind=kind, message=kind)
        ).research(ShareResearchRequest(ticker="TCS", exchange="NSE", lookup_horizon=_HORIZON))
        assert result.record.status is status
        assert result.record.valuation_eligible is False

    def test_domain_errors_are_not_breaker_failures(self) -> None:
        assert not is_provider_circuit_failure(
            ShareCountResolutionError("SHARES_OUTSTANDING_STALE", "stale")
        )
        assert not is_provider_circuit_failure(DataValidationError("identity"))
        assert is_provider_circuit_failure(ProviderRequestError("timeout"))
        # Gemini share-research errors are not share-count circuit events.
        err = ShareResearchGeminiError("timeout", "timeout")
        assert not isinstance(err, DataValidationError)


class TestValuationOverlay:
    def test_current_record_is_eligible(self, tmp_path: Path) -> None:
        store = ShareResearchStore(tmp_path / "share_research")
        store.save(_current_record())
        snapshot = current_share_research_snapshot(
            Instrument(
                symbol="TCS",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="NSE",
                isin="INE467B01029",
            ),
            store=store,
            now=_HORIZON,
        )
        assert snapshot is not None
        assert snapshot.shares_value() == 3618087518.0

    def test_non_current_does_not_overlay(self, tmp_path: Path) -> None:
        store = ShareResearchStore(tmp_path / "share_research")
        record = _current_record()
        store.save(replace(
            record,
            status=ShareResearchStatus.UNKNOWN,
            valuation_eligible=False,
        ))
        snapshot = current_share_research_snapshot(
            Instrument(
                symbol="TCS",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="NSE",
                isin="INE467B01029",
            ),
            store=store,
            now=_HORIZON,
        )
        assert snapshot is None

    def test_wrong_ticker_does_not_overlay(self, tmp_path: Path) -> None:
        store = ShareResearchStore(tmp_path / "share_research")
        store.save(_current_record())
        snapshot = current_share_research_snapshot(
            Instrument(
                symbol="INFY",
                asset_class=AssetClass.EQUITY,
                currency="INR",
                exchange="NSE",
                isin="INE467B01029",
            ),
            store=store,
            now=_HORIZON,
        )
        assert snapshot is None


class TestDurableShareResearchStore:
    def test_current_survives_new_store_instance(self) -> None:
        from production_platform import InMemoryDatabasePort

        from dsp_platform.share_research.db_store import DatabaseShareResearchStore

        db = InMemoryDatabasePort()
        DatabaseShareResearchStore(db).save(_current_record())
        restored = DatabaseShareResearchStore(db).load_current("INE467B01029")
        assert restored is not None
        assert restored.outstanding_shares == _TCS_SHARES
        assert restored.integrity_hash == "abc"
        assert restored.status is ShareResearchStatus.CURRENT

    def test_history_is_append_only_across_replacements(self) -> None:
        from production_platform import InMemoryDatabasePort

        from dsp_platform.share_research.db_store import DatabaseShareResearchStore

        db = InMemoryDatabasePort()
        store = DatabaseShareResearchStore(db)
        store.save(_current_record())
        store.save(
            replace(
                _current_record(),
                research_id="rec-next",
                outstanding_shares=Decimal("3618087519"),
            )
        )
        store.save(
            replace(
                _current_record(),
                research_id="rec-third",
                outstanding_shares=Decimal("3618087520"),
            )
        )
        current = store.load_current("INE467B01029")
        assert current is not None
        assert current.research_id == "rec-third"
        assert current.outstanding_shares == Decimal("3618087520")
        ids = {row["research_id"] for row in store.load_history("INE467B01029")}
        assert ids == {"rec-current", "rec-next"}

    def test_two_isins_do_not_clobber(self) -> None:
        from production_platform import InMemoryDatabasePort

        from dsp_platform.share_research.db_store import DatabaseShareResearchStore

        db = InMemoryDatabasePort()
        store = DatabaseShareResearchStore(db)
        store.save(_current_record())
        store.save(
            replace(
                _current_record(),
                research_id="rec-infy",
                ticker="INFY",
                isin="INE009A01021",
                outstanding_shares=_INFY_SHARES,
            )
        )
        tcs = store.load_current("INE467B01029")
        infy = store.load_current("INE009A01021")
        assert tcs is not None and tcs.ticker == "TCS"
        assert tcs.outstanding_shares == _TCS_SHARES
        assert infy is not None and infy.ticker == "INFY"
        assert infy.outstanding_shares == _INFY_SHARES
