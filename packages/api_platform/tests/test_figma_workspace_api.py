"""API contracts for the frozen Figma pages: Dashboard · Portfolio · Research Hub
· Research Canvas · Client Profile · Institutional · Directory · Signals.

P0-05: every per-user route requires a server-validated JWT; identity never
comes from the request body.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.coverage_registry import (
    CoverageRegistryStore,
    get_coverage_registry_service,
    reset_coverage_registry_store_for_tests,
)
from dsp_platform.investor_workspace import (
    InvestorWorkspaceStore,
    reset_investor_workspace_store_for_tests,
)


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform) -> Iterator[TestClient]:
    reset_coverage_registry_store_for_tests(CoverageRegistryStore())
    reset_investor_workspace_store_for_tests(InvestorWorkspaceStore())
    yield TestClient(create_app(platform=platform))
    reset_coverage_registry_store_for_tests(None)
    reset_investor_workspace_store_for_tests(None)


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="figma-user", username="figmauser")
    return bearer_headers(client, username="figmauser")


@pytest.fixture
def other_auth(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="figma-other", username="figmaother")
    return bearer_headers(client, username="figmaother")


def _seed_coverage() -> None:
    svc = get_coverage_registry_service()
    payload = {
        "business_quality": {"score": 86.0},
        "recommendation_summary": {"label": "BUY", "margin_of_safety_assessment": {"margin_of_safety": 0.1}},
        "server_valuation": {"current_market_price": 3850.4},
        "dsp_analysis": {"identity": {"ticker": "TCS", "company_name": "TCS Ltd", "sector": "Technology"}},
        "fundamental_metrics": {"pe": {"value": 28.1}, "roe": {"value": 0.46}, "revenue_growth": {"value": 0.09}},
        "risk": {"score": 20},
    }
    svc.record_from_payload(payload, ticker="TCS", exchange="NSE", owner_user_id="figma-user", as_of="2026-08-01T00:00:00+00:00")
    payload2 = {**payload, "business_quality": {"score": 92.0}}
    svc.record_from_payload(payload2, ticker="TCS", exchange="NSE", owner_user_id="figma-user", as_of="2026-09-01T00:00:00+00:00")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/workspace/watchlist",
        "/api/v1/workspace/portfolio",
        "/api/v1/workspace/dashboard",
        "/api/v1/workspace/research/saved",
        "/api/v1/workspace/research/canvas",
        "/api/v1/workspace/profile",
        "/api/v1/coverage/institutional",
        "/api/v1/coverage/directory",
        "/api/v1/coverage/signals",
        "/api/v1/coverage/compare?a=TCS&b=INFY",
    ],
)
def test_per_user_routes_require_auth(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401


def test_market_indices_is_public_and_honest_without_provider(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from dsp_platform.market_indices import reset_market_index_service_for_tests

    monkeypatch.setenv("DSP_INVESTMENT_DATA_PROVIDER", "unavailable")
    reset_market_index_service_for_tests(None)
    try:
        res = client.get("/api/v1/market/indices")
    finally:
        reset_market_index_service_for_tests(None)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True and body["available"] is False
    assert body["capability"] == "INVESTMENT_DATA_UNAVAILABLE"
    assert [i["label"] for i in body["indices"]] == ["NIFTY 50", "SENSEX", "NIFTY IT", "NIFTY BANK"]
    assert all(i["value"] is None and i["available"] is False for i in body["indices"])


def test_watchlist_crud_is_user_scoped(client: TestClient, auth: dict[str, str], other_auth: dict[str, str]) -> None:
    _seed_coverage()
    res = client.post("/api/v1/workspace/watchlist", json={"symbol": "tcs", "exchange": "NSE"}, headers=auth)
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    assert items[0]["symbol"] == "TCS" and items[0]["rating"] == "A+"
    assert "quote" in items[0] and items[0]["quote"]["available"] is False  # no provider in tests
    assert client.get("/api/v1/workspace/watchlist", headers=other_auth).json()["count"] == 0
    res = client.delete("/api/v1/workspace/watchlist/TCS", headers=auth)
    assert res.json()["removed"] is True and res.json()["count"] == 0


def test_portfolio_holdings_and_validation(client: TestClient, auth: dict[str, str]) -> None:
    res = client.post(
        "/api/v1/workspace/portfolio/holdings",
        json={"symbol": "TCS", "quantity": 10, "average_cost": 3500},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["summary"]["total_invested"] == 35000.0
    assert body["summary"]["complete"] is False  # no authenticated CMP in tests
    assert body["summary"]["current_value"] is None
    assert body["holdings"][0]["quantity"] == 10 and body["holdings"][0]["average_cost"] == 3500
    assert body["message"].startswith("Data unavailable.")

    bad = client.post(
        "/api/v1/workspace/portfolio/holdings",
        json={"symbol": "TCS", "quantity": 0, "average_cost": 3500},
        headers=auth,
    )
    assert bad.status_code == 422

    assert client.delete("/api/v1/workspace/portfolio/holdings/TCS", headers=auth).json()["removed"] is True
    client.post("/api/v1/workspace/portfolio/holdings", json={"symbol": "INFY", "quantity": 1, "average_cost": 1}, headers=auth)
    assert client.delete("/api/v1/workspace/portfolio/holdings", headers=auth).json()["cleared"] == 1


def test_dashboard_overview_shape(client: TestClient, auth: dict[str, str]) -> None:
    _seed_coverage()
    body = client.get("/api/v1/workspace/dashboard", headers=auth).json()
    assert set(body) >= {"watchlist", "recent_research", "signals"}
    assert [r["symbol"] for r in body["recent_research"]] == ["TCS", "TCS"]
    assert body["signals"][0]["type"] == "upgrade"
    assert body["signals"][0]["from_rating"] == "A" and body["signals"][0]["to_rating"] == "A+"


def test_saved_research_and_canvas(client: TestClient, auth: dict[str, str], other_auth: dict[str, str]) -> None:
    res = client.post(
        "/api/v1/workspace/research/saved",
        json={"symbol": "TCS", "title": "Moat review", "tags": ["IT"], "turns": 7},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    saved_id = res.json()["item"]["saved_id"]
    assert client.get("/api/v1/workspace/research/saved", headers=auth).json()["count"] == 1
    assert client.get("/api/v1/workspace/research/saved", headers=other_auth).json()["count"] == 0
    assert client.delete(f"/api/v1/workspace/research/saved/{saved_id}", headers=auth).json()["removed"] is True

    res = client.post(
        "/api/v1/workspace/research/canvas",
        json={"title": "Thesis", "blocks": [{"type": "heading", "content": "TCS"}, {"type": "text", "content": "Notes"}]},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    canvas_id = res.json()["item"]["canvas_id"]
    assert client.get(f"/api/v1/workspace/research/canvas/{canvas_id}", headers=auth).json()["item"]["version"] == 1
    assert client.get(f"/api/v1/workspace/research/canvas/{canvas_id}", headers=other_auth).status_code == 404
    bad = client.post("/api/v1/workspace/research/canvas", json={"blocks": [{"type": "script"}]}, headers=auth)
    assert bad.status_code == 422


def test_profile_and_financial_health(client: TestClient, auth: dict[str, str]) -> None:
    empty = client.get("/api/v1/workspace/profile", headers=auth).json()
    assert empty["health"]["status"] == "incomplete" and empty["health"]["score"] is None

    res = client.put(
        "/api/v1/workspace/profile",
        json={
            "age": 34,
            "city": "Pune",
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
        },
        headers=auth,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    health = body["health"]
    assert health["status"] == "complete"
    assert 0 <= health["score"] <= 1000 and health["max"] == 1000
    assert health["category"] in {"Very Poor", "Poor", "Fair", "Good", "Excellent"}
    assert [c["label"] for c in health["components"]] == [
        "Income Strength",
        "Savings & Investments",
        "Debt Management",
        "Emergency Protection",
        "Goal Readiness",
    ]
    assert body["completeness"]["percent"] > 0
    # Locked account fields are populated server-side from the JWT principal.
    assert body["profile"]["email"] == "figmauser@example.com"

    bad = client.put("/api/v1/workspace/profile", json={"primary_goal": "yacht"}, headers=auth)
    assert bad.status_code == 422

    again = client.post("/api/v1/workspace/profile/score", headers=auth).json()
    assert again["health"]["score"] == health["score"]  # deterministic


def test_institutional_directory_signals(client: TestClient, auth: dict[str, str]) -> None:
    _seed_coverage()
    inst = client.get("/api/v1/coverage/institutional?rating=A%2B", headers=auth).json()
    assert inst["stats"]["securities_covered"] == 1 and inst["stats"]["a_plus_rated"] == 1
    assert inst["screener"][0]["symbol"] == "TCS"
    assert inst["screener"][0]["pe"] == 28.1 and inst["screener"][0]["roe"] == 0.46
    assert len(inst["coverage_growth"]) == 6
    assert {d["rating"] for d in inst["rating_distribution"]} == {"A+", "A", "B+", "B", "C", "D", "F"}

    directory = client.get("/api/v1/coverage/directory?sector=Technology&q=tcs", headers=auth).json()
    assert directory["count"] == 1 and directory["items"][0]["rating"] == "A+"
    assert client.get("/api/v1/coverage/directory?sector=Banking", headers=auth).json()["count"] == 0

    signals = client.get("/api/v1/coverage/signals?type=upgrade", headers=auth).json()
    assert signals["count"] == 1 and signals["signals"][0]["label"] == "Quality upgrade"
    assert set(signals["today"]) == {"new_signals", "upgrades", "downgrades", "risk_flags", "as_of"}

    latest = client.get("/api/v1/coverage/latest/TCS", headers=auth).json()
    assert latest["available"] is True and latest["record"]["rating"] == "A+"
    assert client.get("/api/v1/coverage/latest/NOPE", headers=auth).json()["available"] is False

    page = client.get("/api/v1/coverage/directory?limit=1&offset=0", headers=auth).json()
    assert page["count"] == 1 and page["limit"] == 1 and len(page["items"]) == 1

    cmp = client.get("/api/v1/coverage/compare?a=TCS&b=NOPE", headers=auth).json()
    assert cmp["ok"] is True and cmp["available"] is False
    assert client.get("/api/v1/coverage/compare", headers=auth).status_code == 422


def test_analyse_records_coverage_for_owner(client: TestClient, auth: dict[str, str]) -> None:
    """Server-side hook: /analyse → coverage registry (owner from JWT only)."""
    res = client.post(
        "/api/v1/analyse",
        json={"ticker": "TCS", "company": "TCS Ltd", "exchange": "NSE"},
        headers=auth,
    )
    assert res.status_code == 200, res.text
    latest = get_coverage_registry_service().latest("TCS")
    assert latest is not None
    assert latest["owner_user_id"] == "figma-user"
    assert latest["symbol"] == "TCS"
    # Recent research on the Dashboard reflects the analyse call.
    dash = client.get("/api/v1/workspace/dashboard", headers=auth).json()
    assert dash["recent_research"][0]["symbol"] == "TCS"
    assert dash["recent_research"][0]["title"].startswith("TCS")
    assert "href" in dash["recent_research"][0]
    assert any(w["symbol"] == "TCS" for w in dash["watchlist"])


def test_invalid_identifiers_and_cross_user_mutations(
    client: TestClient, auth: dict[str, str], other_auth: dict[str, str]
) -> None:
    assert client.get("/api/v1/workspace/research/canvas/does-not-exist", headers=auth).status_code == 404
    assert client.delete("/api/v1/workspace/research/saved/does-not-exist", headers=auth).json()["removed"] is False
    res = client.post(
        "/api/v1/workspace/research/saved",
        json={"symbol": "TCS", "title": "Mine", "tags": []},
        headers=auth,
    )
    saved_id = res.json()["item"]["saved_id"]
    assert client.delete(f"/api/v1/workspace/research/saved/{saved_id}", headers=other_auth).json()["removed"] is False
    assert client.get("/api/v1/workspace/research/saved", headers=auth).json()["count"] == 1
