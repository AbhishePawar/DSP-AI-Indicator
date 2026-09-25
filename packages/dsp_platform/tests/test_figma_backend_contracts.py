"""Figma-first backend contracts: coverage registry, investor workspace,
Financial Health Score, fundamental metrics strip.

Everything the frozen Figma UI renders must come from these server contracts.
CV-001/002/004/005: no fabrication, mandatory inputs, determinism, honest
unavailability.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from dsp_platform.composition.fundamental_metrics import fundamental_metrics_public
from dsp_platform.coverage_registry import (
    CoverageRegistryService,
    CoverageRegistryStore,
    DatabaseCoverageRegistryStore,
    letter_rating,
)
from dsp_platform.investor_workspace import (
    DatabaseInvestorWorkspaceStore,
    InvestorWorkspaceService,
    InvestorWorkspaceStore,
    WorkspaceValidationError,
    compute_financial_health,
    health_category,
)


def _payload(score: float, *, risk: float = 20.0, mos: float = 0.12, price: float = 3850.4) -> dict:
    return {
        "business_quality": {"score": score},
        "recommendation_summary": {
            "label": "BUY",
            "margin_of_safety_assessment": {"margin_of_safety": mos},
        },
        "server_valuation": {"current_market_price": price, "intrinsic_value_per_share": 4300.0},
        "dsp_analysis": {
            "identity": {
                "ticker": "TCS",
                "company_name": "Tata Consultancy Services",
                "sector": "Technology",
                "industry": "IT Services",
            }
        },
        "fundamental_metrics": {
            "pe": {"value": 28.1},
            "roe": {"value": 0.46},
            "revenue_growth": {"value": 0.09},
            "market_cap": {"value": 1.4e13},
        },
        "risk": {"score": risk},
    }


class TestLetterRating:
    @pytest.mark.parametrize(
        ("score", "grade"),
        [(95, "A+"), (90, "A+"), (86, "A"), (80, "A"), (72, "B+"), (65, "B"), (55, "C"), (45, "D"), (10, "F")],
    )
    def test_arch002_thresholds(self, score: float, grade: str) -> None:
        assert letter_rating(score) == grade

    def test_missing_score_is_unrated(self) -> None:
        assert letter_rating(None) is None
        assert letter_rating(float("nan")) is None


class TestCoverageRegistry:
    def test_records_public_fields_without_recompute(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        rec = svc.record_from_payload(_payload(86.0), ticker="tcs", exchange="NSE", owner_user_id="u1")
        assert rec is not None
        assert rec.symbol == "TCS"
        assert rec.rating == "A"
        assert rec.sector == "Technology"
        assert rec.pe == 28.1 and rec.roe == 0.46 and rec.revenue_growth == 0.09
        assert rec.price == 3850.4 and rec.margin_of_safety == 0.12
        assert rec.owner_user_id == "u1"

    def test_no_symbol_no_record(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        assert svc.record_from_payload({}, ticker=None) is None

    def test_stats_screener_distribution(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        svc.record_from_payload(_payload(86.0), ticker="TCS")
        infy = _payload(92.0)
        infy["dsp_analysis"]["identity"]["ticker"] = "INFY"
        svc.record_from_payload(infy, ticker="INFY")
        unrated = _payload(50.0)
        unrated["business_quality"] = {"score": None}
        svc.record_from_payload(unrated, ticker="XYZ")

        stats = svc.stats()
        assert stats == {
            "securities_covered": 3,
            "dsp_rated": 2,
            "a_rated": 2,
            "a_plus_rated": 1,
            "last_updated": stats["last_updated"],
        }
        assert [r["symbol"] for r in svc.screener("A+")] == ["INFY"]
        assert [r["symbol"] for r in svc.screener()] == ["INFY", "TCS", "XYZ"]
        dist = {d["rating"]: d["count"] for d in svc.rating_distribution()}
        assert dist["A+"] == 1 and dist["A"] == 1 and dist["B"] == 0

    def test_signals_are_two_record_comparisons(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        svc.record_from_payload(_payload(86.0, risk=20, mos=0.12), ticker="TCS", as_of="2026-08-10T00:00:00+00:00")
        svc.record_from_payload(_payload(91.0, risk=30, mos=-0.05), ticker="TCS", as_of="2026-09-25T00:00:00+00:00")
        signals = svc.signals()
        kinds = {s["type"] for s in signals}
        assert kinds == {"upgrade", "risk", "valuation"}
        up = next(s for s in signals if s["type"] == "upgrade")
        assert up["from_rating"] == "A" and up["to_rating"] == "A+"
        assert "86" in up["text"] and "91" in up["text"]
        # single record → no signal (nothing to compare)
        assert svc.signals(symbol="UNKNOWN") == []

    def test_coverage_growth_is_cumulative(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        svc.record_from_payload(_payload(86.0), ticker="TCS", as_of="2026-08-10T00:00:00+00:00")
        svc.record_from_payload(_payload(70.0), ticker="INFY", as_of="2026-09-01T00:00:00+00:00")
        growth = svc.coverage_growth(3, now=datetime(2026, 9, 25, tzinfo=UTC))
        assert [g["month"] for g in growth] == ["Jul", "Aug", "Sep"]
        assert [g["covered"] for g in growth] == [0, 1, 2]

    def test_recent_research_is_owner_scoped(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        svc.record_from_payload(_payload(86.0), ticker="TCS", owner_user_id="u1")
        svc.record_from_payload(_payload(86.0), ticker="INFY", owner_user_id="u2")
        assert [r["symbol"] for r in svc.recent_research("u1")] == ["TCS"]
        assert svc.recent_research("nobody") == []

    def test_state_round_trip(self) -> None:
        store = CoverageRegistryStore()
        CoverageRegistryService(store).record_from_payload(_payload(86.0), ticker="TCS")
        restored = CoverageRegistryStore()
        restored.import_state(json.loads(json.dumps(store.export_state())))
        assert restored.latest_for("TCS").rating == "A"

    def test_compare_is_server_side_and_unavailable_without_both(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        tcs = _payload(92.0)
        tcs["fundamental_metrics"]["roce"] = {"value": 0.48}
        tcs["fundamental_metrics"]["fcf"] = {"value": 518.0}
        infy = _payload(80.0)
        infy["dsp_analysis"]["identity"]["ticker"] = "INFY"
        infy["fundamental_metrics"]["pe"] = {"value": 24.1}
        infy["fundamental_metrics"]["roe"] = {"value": 0.33}
        svc.record_from_payload(tcs, ticker="TCS")
        svc.record_from_payload(infy, ticker="INFY")
        out = svc.compare("TCS", "INFY")
        assert out["available"] is True
        pe = next(m for m in out["metrics"] if m["key"] == "pe")
        assert pe["winner"] == "INFY"  # inverse: lower P/E wins
        roe = next(m for m in out["metrics"] if m["key"] == "roe")
        assert roe["winner"] == "TCS"
        assert out["radar"]["a"]["Quality"] == 92.0
        missing = svc.compare("TCS", "NOPE")
        assert missing["available"] is False and missing["message"].startswith("Data unavailable.")

    def test_signals_carry_severity_status_and_dsp_context(self) -> None:
        svc = CoverageRegistryService(CoverageRegistryStore())
        svc.record_from_payload(_payload(86.0), ticker="TCS", as_of="2026-08-10T00:00:00+00:00")
        svc.record_from_payload(_payload(91.0), ticker="TCS", as_of="2026-09-25T00:00:00+00:00")
        up = next(s for s in svc.signals() if s["type"] == "upgrade")
        assert up["severity"] == "info" and up["status"] == "active"
        assert up["dsp_context"]["from_rating"] == "A"
        assert up["source"] == "coverage_registry"


class _FakeDb:
    """Minimal DatabasePort double for durable snapshot stores."""

    def __init__(self) -> None:
        self.rows: dict[str, str] = {}
        self.executed: list[str] = []

    def execute(self, sql: str, params=None):  # noqa: ANN001
        self.executed.append(sql)
        low = sql.lower()
        if "insert" in low or "update" in low or "merge" in low:
            self._last_write = sql
        return None

    def fetchall(self, sql: str, params=None):  # noqa: ANN001
        return []

    def ping(self) -> bool:
        return True


class TestDurableStores:
    def test_database_stores_write_through(self) -> None:
        db = _FakeDb()
        store = DatabaseCoverageRegistryStore(db)
        before = len(db.executed)
        CoverageRegistryService(store).record_from_payload(_payload(86.0), ticker="TCS")
        assert len(db.executed) > before  # append flushed to DatabasePort

        ws = DatabaseInvestorWorkspaceStore(db)
        before = len(db.executed)
        ws.add_watchlist("u1", "TCS")
        assert len(db.executed) > before


class TestInvestorWorkspace:
    def _service(self, quotes: dict[str, float | None]) -> tuple[InvestorWorkspaceService, InvestorWorkspaceStore]:
        cov = CoverageRegistryService(CoverageRegistryStore())
        cov.record_from_payload(_payload(86.0), ticker="TCS")
        store = InvestorWorkspaceStore()

        def fetch(symbol: str, exchange: str | None):  # noqa: ANN202
            price = quotes.get(symbol)
            if price is None:
                return None
            return {"fields": {"current_price": price, "change": -31.2, "change_percent": -0.8}, "currency": "INR"}

        return InvestorWorkspaceService(store, coverage=cov, quote_fetcher=fetch), store

    def test_watchlist_joins_quote_and_rating(self) -> None:
        svc, store = self._service({"TCS": 3850.4})
        store.add_watchlist("u1", "tcs")
        store.add_watchlist("u1", "TCS")  # idempotent
        view = svc.watchlist_view("u1")
        assert view["count"] == 1
        item = view["items"][0]
        assert item["rating"] == "A"
        assert item["quote"]["price"] == 3850.4 and item["quote"]["change_percent"] == -0.8
        assert store.remove_watchlist("u1", "TCS") is True
        assert svc.watchlist_view("u1")["count"] == 0

    def test_portfolio_arithmetic_is_server_side(self) -> None:
        svc, store = self._service({"TCS": 4000.0})
        store.upsert_holding("u1", symbol="TCS", quantity=10, average_cost=3500)
        view = svc.portfolio_view("u1")
        row = view["holdings"][0]
        assert row["invested"] == 35000.0
        assert row["current_value"] == 40000.0
        assert row["pnl"] == 5000.0
        assert row["return_pct"] == pytest.approx(5000 / 35000)
        assert row["weight"] == 1.0
        assert row["sector"] == "Technology" and row["rating"] == "A"
        s = view["summary"]
        assert s["complete"] is True
        assert s["current_value"] == 40000.0 and s["total_pnl"] == 5000.0
        assert view["sector_allocation"] == [{"sector": "Technology", "value": 40000.0, "weight": 1.0}]

    def test_unpriced_holding_makes_totals_unavailable(self) -> None:
        svc, store = self._service({"TCS": 4000.0, "INFY": None})
        store.upsert_holding("u1", symbol="TCS", quantity=10, average_cost=3500)
        store.upsert_holding("u1", symbol="INFY", quantity=5, average_cost=1500)
        view = svc.portfolio_view("u1")
        s = view["summary"]
        assert s["complete"] is False
        assert s["total_invested"] == 42500.0
        assert s["current_value"] is None and s["total_pnl"] is None and s["return_pct"] is None
        assert view["message"].startswith("Data unavailable.")
        infy = next(h for h in view["holdings"] if h["symbol"] == "INFY")
        assert infy["cmp"] is None and infy["pnl"] is None

    def test_workspace_survives_process_restart(self) -> None:
        store = InvestorWorkspaceStore()
        store.add_watchlist("u1", "TCS", exchange="NSE")
        store.upsert_holding("u1", symbol="INFY", quantity=2, average_cost=100)
        store.save_research("u1", symbol="TCS", title="Moat", tags=["IT"])
        store.save_canvas("u1", title="Thesis", blocks=[{"type": "heading", "content": "Head"}])
        store.put_profile("u1", {"city": "Pune", "monthly_income": 100000})
        revived = InvestorWorkspaceStore()
        revived.import_state(json.loads(json.dumps(store.export_state())))
        assert revived.list_watchlist("u1")[0]["symbol"] == "TCS"
        assert revived.list_holdings("u1")[0]["symbol"] == "INFY"
        assert revived.list_saved_research("u1")[0]["title"] == "Moat"
        assert revived.list_canvases("u1")[0]["title"] == "Thesis"
        assert revived.get_profile("u1")["city"] == "Pune"
        assert revived.list_watchlist("u2") == []

    def test_holding_validation(self) -> None:
        store = InvestorWorkspaceStore()
        with pytest.raises(WorkspaceValidationError):
            store.upsert_holding("u1", symbol="TCS", quantity=0, average_cost=10)
        with pytest.raises(WorkspaceValidationError):
            store.upsert_holding("u1", symbol="TCS", quantity=1, average_cost=-1)
        with pytest.raises(WorkspaceValidationError):
            store.upsert_holding("u1", symbol="", quantity=1, average_cost=1)
        store.upsert_holding("u1", symbol="TCS", quantity=1, average_cost=1)
        assert store.clear_holdings("u1") == 1

    def test_saved_research_and_canvas(self) -> None:
        store = InvestorWorkspaceStore()
        saved = store.save_research("u1", symbol="TCS", title="Q2 review", tags=["IT", "Quality"], turns=12)
        assert saved["turns"] == 12 and saved["tags"] == ["IT", "Quality"]
        assert store.list_saved_research("u1")[0]["saved_id"] == saved["saved_id"]
        assert store.list_saved_research("u2") == []
        canvas = store.save_canvas("u1", title="Thesis", blocks=[{"type": "heading", "content": "TCS"}])
        assert canvas["version"] == 1
        canvas2 = store.save_canvas("u1", title="Thesis", blocks=[], canvas_id=canvas["canvas_id"])
        assert canvas2["version"] == 2
        with pytest.raises(WorkspaceValidationError):
            store.save_canvas("u1", title="x", blocks=[{"type": "iframe"}])

    def test_profile_locked_fields_from_account(self) -> None:
        svc, store = self._service({})
        view = svc.profile_view("u1", account={"name": "Asha", "email": "asha@example.com"})
        assert view["profile"]["full_name"] == "Asha"
        assert view["health"]["status"] == "incomplete"
        assert view["completeness"]["percent"] < 100


class TestFinancialHealth:
    PROFILE = {
        "monthly_income": 150000,
        "monthly_expenses": 60000,
        "monthly_emi": 20000,
        "total_savings": 800000,
        "total_investments": 2500000,
        "emergency_fund": 400000,
        "health_insurance": 1000000,
        "life_insurance": 5000000,
        "primary_goal": "retirement",
        "target_amount": 30000000,
        "target_year": 2045,
    }

    def test_zones(self) -> None:
        assert health_category(0) == "Very Poor"
        assert health_category(199) == "Very Poor"
        assert health_category(200) == "Poor"
        assert health_category(400) == "Fair"
        assert health_category(600) == "Good"
        assert health_category(749) == "Good"
        assert health_category(750) == "Excellent"
        assert health_category(1000) == "Excellent"

    def test_incomplete_inputs_never_score(self) -> None:
        out = compute_financial_health({"monthly_income": 100000})
        assert out["status"] == "incomplete" and out["score"] is None
        assert "monthly_expenses" in out["missing_inputs"]
        assert out["insight"].startswith("Unable to calculate.")

    def test_deterministic_and_bounded(self) -> None:
        now = datetime(2026, 9, 25, tzinfo=UTC)
        a = compute_financial_health(self.PROFILE, now=now)
        b = compute_financial_health(dict(self.PROFILE), now=now)
        assert a == b
        assert a["status"] == "complete"
        assert 0 <= a["score"] <= 1000
        assert [c["key"] for c in a["components"]] == [
            "income_strength",
            "savings_investments",
            "debt_management",
            "emergency_protection",
            "goal_readiness",
        ]
        assert all(0 <= c["score"] <= 100 for c in a["components"])
        assert a["score"] == sum(c["score"] for c in a["components"]) * 2
        assert a["category"] == health_category(a["score"])
        assert "Priority:" in a["insight"]

    def test_no_debt_flag_scores_full_debt_component(self) -> None:
        profile = {**self.PROFILE, "no_outstanding_debt": True, "monthly_emi": 50000, "credit_card_outstanding": 900000}
        out = compute_financial_health(profile, now=datetime(2026, 9, 25, tzinfo=UTC))
        debt = next(c for c in out["components"] if c["key"] == "debt_management")
        assert debt["score"] == 100

    def test_zero_income_is_unable_to_calculate(self) -> None:
        out = compute_financial_health({**self.PROFILE, "monthly_income": 0})
        assert out["status"] == "incomplete"


class TestFundamentalMetrics:
    def test_copies_engine_outputs_and_derives_pe(self) -> None:
        result = SimpleNamespace(
            authenticated_valuation_trace={
                "current_market_price": 100.0,
                "market_cap": 1e12,
                "sector": "Technology",
                "industry": "IT Services",
            },
            financial_analysis=SimpleNamespace(
                ratios=SimpleNamespace(
                    profitability=[SimpleNamespace(name="roa", value=0.1), SimpleNamespace(name="roe", value=0.46)],
                    leverage=[SimpleNamespace(name="debt_to_equity", value=0.08)],
                ),
                income=SimpleNamespace(
                    revenue=SimpleNamespace(revenue_growth=0.09),
                    growth=SimpleNamespace(revenue_growth=None),
                    profitability=SimpleNamespace(diluted_eps=4.0, eps=4.2),
                ),
            ),
        )
        out = fundamental_metrics_public(result)
        assert out["authority"] == "server"
        assert out["sector"]["value"] == "Technology"
        assert out["roe"]["value"] == 0.46 and out["roe"]["category"] == "calculated"
        assert out["debt_to_equity"]["value"] == 0.08
        assert out["revenue_growth"]["value"] == 0.09
        assert out["eps"]["value"] == 4.0
        assert out["pe"]["value"] == 25.0
        assert "eps_diluted" in out["pe"]["formula"]

    def test_missing_inputs_are_unavailable_not_guessed(self) -> None:
        out = fundamental_metrics_public(SimpleNamespace(authenticated_valuation_trace=None, financial_analysis=None))
        for key in (
            "price",
            "change",
            "change_percent",
            "as_of",
            "market_cap",
            "sector",
            "revenue",
            "profit",
            "gross_margin",
            "operating_margin",
            "net_margin",
            "roe",
            "roce",
            "debt_to_equity",
            "revenue_growth",
            "eps",
            "pe",
            "fcf",
        ):
            assert out[key]["value"] is None
            assert out[key]["status"] == "unavailable"

    def test_negative_eps_has_no_pe(self) -> None:
        result = SimpleNamespace(
            authenticated_valuation_trace={"current_market_price": 100.0},
            financial_analysis=SimpleNamespace(
                ratios=None,
                income=SimpleNamespace(
                    revenue=None, growth=None, profitability=SimpleNamespace(diluted_eps=-2.0, eps=None)
                ),
            ),
        )
        assert fundamental_metrics_public(result)["pe"]["value"] is None
