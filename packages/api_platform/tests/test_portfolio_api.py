"""Portfolio Store API tests (RC1 Milestone 3) — CRUD, ownership, migration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from api_platform.api.app import create_app
from auth import (
    AuthService,
    RoleRegistry,
    reset_auth_service_for_tests,
    reset_role_registry_for_tests,
)
from dsp_platform.portfolio_store_facade import reset_portfolio_store_for_tests
from persistence import (
    InMemoryStorageProvider,
    PersistenceService,
    RepositoryRegistry,
    reset_persistence_service_for_tests,
    reset_repository_registry_for_tests,
)
from portfolio_store import InMemoryPortfolioStore, PortfolioService

FIXED = datetime.now(UTC).replace(microsecond=0).isoformat()


@pytest.fixture()
def client() -> TestClient:
    store = InMemoryStorageProvider()
    registry = RepositoryRegistry(storage=store)
    reset_repository_registry_for_tests(registry)
    ps = PersistenceService(registry)
    reset_persistence_service_for_tests(ps)
    reset_role_registry_for_tests(RoleRegistry())
    auth = AuthService(ps, jwt_secret="test-secret")
    reset_auth_service_for_tests(auth)
    reset_portfolio_store_for_tests(PortfolioService(store=InMemoryPortfolioStore()))
    app = create_app(enable_security=False)
    with TestClient(app) as c:
        yield c
    reset_auth_service_for_tests(None)
    reset_role_registry_for_tests(None)
    reset_persistence_service_for_tests(None)
    reset_repository_registry_for_tests(None)
    reset_portfolio_store_for_tests(None)


def _register_and_login(client: TestClient, *, username: str, user_id: str) -> str:
    # Each registration is an independent flow — clear any leftover session
    # cookie from a previous user's login in this same TestClient so the
    # CSRF double-submit check (cookie-session-only) never applies here;
    # these tests authenticate via explicit Bearer tokens.
    client.cookies.clear()
    created = client.post(
        "/api/v1/auth/rbac/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "StrongPass12!",
            "user_id": user_id,
            "created_at": FIXED,
            "password_salt": "aabbccddeeff0011",
        },
    )
    assert created.status_code == 200, created.text
    login = client.post(
        "/api/v1/auth/rbac/login",
        json={
            "username": username,
            "password": "StrongPass12!",
            "created_at": FIXED,
            "session_id": f"s-{user_id}",
            "access_jti": f"a-{user_id}",
            "refresh_jti": f"r-{user_id}",
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["result"]["tokens"]["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestAuthenticationRequired:
    def test_list_portfolios_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio")
        assert response.status_code == 401

    def test_create_portfolio_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/portfolio", json={"name": "Mine"})
        assert response.status_code == 401


class TestSchema:
    def test_schema_endpoint_public(self, client: TestClient) -> None:
        response = client.get("/api/v1/portfolio/schema")
        assert response.status_code == 200
        body = response.json()
        assert "buy" in body["schema"]["transaction_types"]


class TestPortfolioCrud:
    def test_create_list_get_update_delete(self, client: TestClient) -> None:
        token = _register_and_login(client, username="analyst1", user_id="u-analyst1")
        headers = _auth_headers(token)

        created = client.post(
            "/api/v1/portfolio", json={"name": "My Portfolio"}, headers=headers
        )
        assert created.status_code == 200
        portfolio = created.json()["result"]
        assert portfolio["is_default"] is True
        pid = portfolio["portfolio_id"]

        listed = client.get("/api/v1/portfolio", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()["result"]) == 1

        fetched = client.get(f"/api/v1/portfolio/{pid}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["result"]["name"] == "My Portfolio"

        updated = client.put(
            f"/api/v1/portfolio/{pid}", json={"name": "Renamed"}, headers=headers
        )
        assert updated.status_code == 200
        assert updated.json()["result"]["name"] == "Renamed"

        deleted = client.delete(f"/api/v1/portfolio/{pid}", headers=headers)
        assert deleted.status_code == 200
        assert deleted.json()["result"]["deleted"] is True

        missing = client.get(f"/api/v1/portfolio/{pid}", headers=headers)
        assert missing.status_code == 404

    def test_multiple_portfolios_per_user(self, client: TestClient) -> None:
        token = _register_and_login(client, username="pm1", user_id="u-pm1")
        headers = _auth_headers(token)
        client.post("/api/v1/portfolio", json={"name": "First"}, headers=headers)
        client.post("/api/v1/portfolio", json={"name": "Second"}, headers=headers)
        client.post("/api/v1/portfolio", json={"name": "Third"}, headers=headers)
        listed = client.get("/api/v1/portfolio", headers=headers)
        assert len(listed.json()["result"]) == 3

    def test_default_portfolio_invariant(self, client: TestClient) -> None:
        token = _register_and_login(client, username="pm2", user_id="u-pm2")
        headers = _auth_headers(token)
        first = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]
        second = client.post(
            "/api/v1/portfolio",
            json={"name": "Second", "is_default": True},
            headers=headers,
        ).json()["result"]
        assert second["is_default"] is True
        refreshed_first = client.get(
            f"/api/v1/portfolio/{first['portfolio_id']}", headers=headers
        ).json()["result"]
        assert refreshed_first["is_default"] is False


class TestOwnership:
    def test_cannot_access_another_users_portfolio(self, client: TestClient) -> None:
        token1 = _register_and_login(client, username="owner1", user_id="u-owner1")
        token2 = _register_and_login(client, username="intruder1", user_id="u-intruder1")

        created = client.post(
            "/api/v1/portfolio",
            json={"name": "Private"},
            headers=_auth_headers(token1),
        ).json()["result"]
        pid = created["portfolio_id"]

        response = client.get(f"/api/v1/portfolio/{pid}", headers=_auth_headers(token2))
        assert response.status_code == 403

    def test_cannot_delete_another_users_portfolio(self, client: TestClient) -> None:
        token1 = _register_and_login(client, username="owner2", user_id="u-owner2")
        token2 = _register_and_login(client, username="intruder2", user_id="u-intruder2")
        created = client.post(
            "/api/v1/portfolio", json={"name": "Private"}, headers=_auth_headers(token1)
        ).json()["result"]
        response = client.delete(
            f"/api/v1/portfolio/{created['portfolio_id']}", headers=_auth_headers(token2)
        )
        assert response.status_code == 403


class TestBenchmark:
    def test_set_and_clear_benchmark(self, client: TestClient) -> None:
        token = _register_and_login(client, username="bench1", user_id="u-bench1")
        headers = _auth_headers(token)
        created = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]
        pid = created["portfolio_id"]

        set_resp = client.put(
            f"/api/v1/portfolio/{pid}/benchmark",
            json={"benchmark_symbol": "spy"},
            headers=headers,
        )
        assert set_resp.status_code == 200
        assert set_resp.json()["result"]["benchmark_symbol"] == "SPY"

        clear_resp = client.put(
            f"/api/v1/portfolio/{pid}/benchmark",
            json={"benchmark_symbol": None},
            headers=headers,
        )
        assert clear_resp.json()["result"]["benchmark_symbol"] is None


class TestHoldings:
    def test_upsert_list_remove_holding(self, client: TestClient) -> None:
        token = _register_and_login(client, username="hold1", user_id="u-hold1")
        headers = _auth_headers(token)
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]["portfolio_id"]

        upserted = client.post(
            f"/api/v1/portfolio/{pid}/holdings",
            json={"symbol": "aapl", "weight": 0.5, "sector": "Technology"},
            headers=headers,
        )
        assert upserted.status_code == 200
        assert upserted.json()["result"]["symbol"] == "AAPL"

        listed = client.get(f"/api/v1/portfolio/{pid}/holdings", headers=headers)
        assert len(listed.json()["result"]) == 1

        removed = client.delete(
            f"/api/v1/portfolio/{pid}/holdings/AAPL", headers=headers
        )
        assert removed.status_code == 200
        assert removed.json()["result"]["removed"] is True

    def test_holdings_require_ownership(self, client: TestClient) -> None:
        token1 = _register_and_login(client, username="hold2", user_id="u-hold2")
        token2 = _register_and_login(client, username="hold3", user_id="u-hold3")
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=_auth_headers(token1)
        ).json()["result"]["portfolio_id"]
        response = client.post(
            f"/api/v1/portfolio/{pid}/holdings",
            json={"symbol": "AAPL", "weight": 0.5},
            headers=_auth_headers(token2),
        )
        assert response.status_code == 403


class TestTransactions:
    def test_record_and_list_transaction(self, client: TestClient) -> None:
        token = _register_and_login(client, username="txn1", user_id="u-txn1")
        headers = _auth_headers(token)
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]["portfolio_id"]

        recorded = client.post(
            f"/api/v1/portfolio/{pid}/transactions",
            json={
                "transaction_type": "buy",
                "transaction_date": "2024-01-01",
                "symbol": "AAPL",
                "quantity": 10,
                "price": 150,
            },
            headers=headers,
        )
        assert recorded.status_code == 200
        assert recorded.json()["result"]["transaction_type"] == "buy"

        listed = client.get(f"/api/v1/portfolio/{pid}/transactions", headers=headers)
        assert len(listed.json()["result"]) == 1

    def test_rejects_unsupported_transaction_type(self, client: TestClient) -> None:
        token = _register_and_login(client, username="txn2", user_id="u-txn2")
        headers = _auth_headers(token)
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]["portfolio_id"]
        response = client.post(
            f"/api/v1/portfolio/{pid}/transactions",
            json={"transaction_type": "short_sell", "transaction_date": "2024-01-01"},
            headers=headers,
        )
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "transaction_type",
        [
            "buy",
            "sell",
            "dividend",
            "bonus",
            "split",
            "rights",
            "fee",
            "tax",
            "cash_deposit",
            "cash_withdrawal",
        ],
    )
    def test_every_transaction_type_accepted(
        self, client: TestClient, transaction_type: str
    ) -> None:
        token = _register_and_login(
            client, username=f"txn_{transaction_type}", user_id=f"u-txn-{transaction_type}"
        )
        headers = _auth_headers(token)
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]["portfolio_id"]
        response = client.post(
            f"/api/v1/portfolio/{pid}/transactions",
            json={
                "transaction_type": transaction_type,
                "transaction_date": "2024-01-01",
                "amount": 100.0,
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text


class TestWatchlist:
    def test_add_list_remove_watchlist_symbol(self, client: TestClient) -> None:
        token = _register_and_login(client, username="wl1", user_id="u-wl1")
        headers = _auth_headers(token)
        pid = client.post(
            "/api/v1/portfolio", json={"name": "First"}, headers=headers
        ).json()["result"]["portfolio_id"]

        added = client.post(
            f"/api/v1/portfolio/{pid}/watchlist",
            json={"symbol": "nvda", "label": "AI"},
            headers=headers,
        )
        assert added.status_code == 200
        assert added.json()["result"]["symbol"] == "NVDA"

        listed = client.get(f"/api/v1/portfolio/{pid}/watchlist", headers=headers)
        assert len(listed.json()["result"]) == 1

        removed = client.delete(
            f"/api/v1/portfolio/{pid}/watchlist/NVDA", headers=headers
        )
        assert removed.json()["result"]["removed"] is True


class TestMigration:
    def test_migrates_local_snapshot_on_first_call(self, client: TestClient) -> None:
        token = _register_and_login(client, username="mig1", user_id="u-mig1")
        headers = _auth_headers(token)

        response = client.post(
            "/api/v1/portfolio/migrate",
            json={
                "name": "My Portfolio",
                "holdings": [
                    {"symbol": "AAPL", "allocationPercent": 60},
                    {"symbol": "MSFT", "weight": 0.4},
                ],
                "watchlist": [{"symbol": "NVDA"}],
                "benchmark_symbol": "SPY",
            },
            headers=headers,
        )
        assert response.status_code == 200
        body = response.json()["result"]
        assert body["migrated"] is True
        assert body["portfolio"]["benchmark_symbol"] == "SPY"

        holdings = client.get(
            f"/api/v1/portfolio/{body['portfolio']['portfolio_id']}/holdings",
            headers=headers,
        ).json()["result"]
        assert {h["symbol"] for h in holdings} == {"AAPL", "MSFT"}

    def test_migration_idempotent_on_retry(self, client: TestClient) -> None:
        token = _register_and_login(client, username="mig2", user_id="u-mig2")
        headers = _auth_headers(token)

        first = client.post(
            "/api/v1/portfolio/migrate",
            json={"name": "Original", "holdings": [{"symbol": "AAPL", "weight": 1.0}]},
            headers=headers,
        ).json()["result"]
        assert first["migrated"] is True

        second = client.post(
            "/api/v1/portfolio/migrate",
            json={"name": "Different", "holdings": [{"symbol": "TSLA", "weight": 1.0}]},
            headers=headers,
        ).json()["result"]
        assert second["migrated"] is False
        assert second["portfolio"]["portfolio_id"] == first["portfolio"]["portfolio_id"]

    def test_migration_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/portfolio/migrate", json={"name": "X"})
        assert response.status_code == 401
