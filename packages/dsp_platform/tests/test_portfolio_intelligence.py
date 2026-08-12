"""EPIC-A002 Portfolio Intelligence unit tests."""

from __future__ import annotations

from dsp_platform.portfolio_intelligence import (
    PORTFOLIO_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    evaluate_portfolio_intelligence,
    portfolio_intelligence_from_dict,
    portfolio_intelligence_to_dict,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


def _ro(symbol: str, *, sector: str | None = "Technology", mos: float | None = 0.2) -> dict:
    identity = {
        "symbol": symbol,
        "ticker": symbol,
        "company_name": f"{symbol} Inc",
    }
    if sector:
        identity["sector"] = sector
    analysis = {
        "ok": True,
        "recommendation_summary": {"label": "Research Mode"},
        "stage_summaries": [],
    }
    if mos is not None:
        analysis["recommendation_summary"]["margin_of_safety"] = mos
        analysis["stage_summaries"] = [
            {"stage": "business_quality_aggregator", "has_result": True, "summary": "q"},
        ]
        analysis["risk"] = {"overall": "moderate"}
    return research_object_to_dict(
        build_research_object(
            symbol=symbol,
            object_id=f"ro-{symbol.lower()}",
            created_at=FIXED,
            data_bundle={
                "identity": identity,
                "market_quote": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "financial_statements": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "corporate_actions": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "historical_series": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
            },
            analysis_payload=analysis,
        )
    )


def test_portfolio_loading_and_linking() -> None:
    result = evaluate_portfolio_intelligence(
        portfolio={
            "portfolio_id": "pf-1",
            "holdings": [
                {"symbol": "AAPL", "weight": 0.6},
                {"symbol": "MSFT", "weight": 0.4},
            ],
        },
        research_objects={"AAPL": _ro("AAPL"), "MSFT": _ro("MSFT", sector="Technology")},
        result_id="pi-1",
        created_at=FIXED,
    )
    assert result["schema_version"] == PORTFOLIO_SCHEMA_VERSION
    assert result["portfolio_summary"]["holding_count"] == 2
    assert result["portfolio_summary"]["linked_research_count"] == 2
    assert result["provenance"]["providers_called"] is False


def test_missing_holdings_research() -> None:
    result = evaluate_portfolio_intelligence(
        portfolio={
            "portfolio_id": "pf-2",
            "holdings": [
                {"symbol": "AAPL", "weight": 0.5},
                {"symbol": "XYZ", "weight": 0.5},
            ],
        },
        research_objects={"AAPL": _ro("AAPL")},
        result_id="pi-2",
        created_at=FIXED,
    )
    assert result["portfolio_summary"]["missing_research_count"] == 1
    assert any(m["symbol"] == "XYZ" for m in result["missing_research"])
    assert any(
        c["symbol"] == "XYZ" and c["available"] is False for c in result["citations"]
    )


def test_citations_and_mos_pass_through() -> None:
    result = evaluate_portfolio_intelligence(
        portfolio={
            "portfolio_id": "pf-3",
            "holdings": [{"symbol": "AAPL", "weight": 1.0}],
        },
        research_objects={"AAPL": _ro("AAPL", mos=0.25)},
        result_id="pi-3",
        created_at=FIXED,
    )
    assert result["margin_of_safety_summary"]["positions"][0]["margin_of_safety"] == 0.25
    assert any(c["section"] == "margin_of_safety" for c in result["citations"])


def test_watchlist_summary() -> None:
    result = evaluate_portfolio_intelligence(
        watchlist={"watchlist_id": "wl-1", "symbols": ["AAPL", "IBM"]},
        research_objects={"AAPL": _ro("AAPL")},
        result_id="pi-4",
        created_at=FIXED,
    )
    assert result["watchlist_summary"]["symbol_count"] == 2
    assert len(result["watchlist_summary"]["linked"]) == 1
    assert result["watchlist_summary"]["missing_research"][0]["symbol"] == "IBM"


def test_determinism_and_serde() -> None:
    kwargs = dict(
        portfolio={
            "portfolio_id": "pf-d",
            "holdings": [
                {"symbol": "MSFT", "weight": 0.3},
                {"symbol": "AAPL", "weight": 0.7},
            ],
        },
        research_objects={"AAPL": _ro("AAPL"), "MSFT": _ro("MSFT")},
        result_id="pi-d",
        created_at=FIXED,
    )
    a = evaluate_portfolio_intelligence(**kwargs)
    b = evaluate_portfolio_intelligence(**kwargs)
    assert a == b
    restored = portfolio_intelligence_from_dict(a)
    assert portfolio_intelligence_to_dict(restored) == a


def test_sector_allocation_uses_weights() -> None:
    result = evaluate_portfolio_intelligence(
        portfolio={
            "portfolio_id": "pf-s",
            "holdings": [
                {"symbol": "AAPL", "weight": 0.5},
                {"symbol": "JPM", "weight": 0.5},
            ],
        },
        research_objects={
            "AAPL": _ro("AAPL", sector="Technology"),
            "JPM": _ro("JPM", sector="Financials"),
        },
        result_id="pi-s",
        created_at=FIXED,
    )
    by_sector = {
        row["sector"]: row["weight_sum"]
        for row in result["sector_allocation"]["by_sector"]
    }
    assert by_sector["Technology"] == 0.5
    assert by_sector["Financials"] == 0.5
