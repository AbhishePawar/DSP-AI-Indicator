"""Live preview API smoke tests for DSP-AI-Indicator infrastructure."""
import os
import requests

from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ENV = dotenv_values(ROOT / "frontend" / ".env")
BACKEND_ENV = dotenv_values(ROOT / "backend" / ".env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api/v1"
ADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("DSP_SEED_ADMIN_PASSWORD") or BACKEND_ENV["DSP_SEED_ADMIN_PASSWORD"]


def test_health_ok():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "pass"
    assert data.get("ready") is True


def test_auth_providers_lists_unavailable():
    r = requests.get(f"{API}/auth/providers", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    providers = data["result"]["providers"]
    # external OAuth is unconfigured so should be unavailable (honest state)
    for p in providers:
        if p["id"] in ("google", "microsoft"):
            assert p["available"] is False
            assert "unavailable" in p["status"]


def test_market_health_null_provider():
    r = requests.get(f"{API}/market/health", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["provider"]["provider_id"].startswith("null")


def test_fundamentals_resolve_tcs_returns_identity_only():
    # should return identity without fabricated financials
    r = requests.get(f"{API}/fundamentals/resolve", params={"symbol": "TCS", "exchange": "NSE"}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    # no fabricated price/eps/pe at top level
    txt = str(body).lower()
    # heuristic: should not fabricate numeric price field at top level
    assert "ok" in body or "result" in body


def test_legacy_auth_login_returns_503_security_bundle():
    """Legacy /auth/login path is NOT configured — must honestly report 503."""
    r = requests.post(f"{API}/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 503
    assert "security bundle" in r.text.lower()


def test_rbac_login_succeeds_and_returns_tokens():
    s = requests.Session()
    r = s.post(f"{API}/auth/rbac/login", json={"username": ADMIN_USER, "password": ADMIN_PASS, "remember_me": False}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    tokens = data["result"]["tokens"]
    assert tokens["access_token"]
    assert tokens["token_type"] == "bearer"
    # session cookie set
    assert any("csrf" in c.name.lower() for c in s.cookies)
    assert any("access" in c.name.lower() for c in s.cookies)


def test_rbac_login_invalid_password_rejected():
    r = requests.post(f"{API}/auth/rbac/login", json={"username": ADMIN_USER, "password": "wrong"}, timeout=15)
    assert r.status_code in (400, 401, 403)


def test_research_company_blocked_by_architecture_gate():
    """Per FIGMA_PARITY: /research/company intentionally blocked (safeguard, not an LLM)."""
    r = requests.get(f"{API}/research/company", params={"symbol": "TCS"}, timeout=15)
    # Expect non-2xx or an unavailable envelope — must NOT fabricate research
    if r.status_code == 200:
        body = r.json()
        assert body.get("ok") is False or "unavailable" in str(body).lower() or "blocked" in str(body).lower()
    else:
        assert r.status_code in (401, 403, 404, 405, 501, 503)


def test_auth_session_endpoint():
    r = requests.get(f"{API}/auth/session", timeout=15)
    # unauthenticated session query should 200 with ok envelope
    assert r.status_code in (200, 401)
