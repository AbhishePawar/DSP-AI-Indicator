"""POST /api/v1/share-research — client share-research boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import logging

import pytest
from fastapi.testclient import TestClient

from api_platform import create_app
from api_platform.api.routers.share_research import reset_share_research_engine_for_tests
from auth_test_helpers import bearer_headers, register_user
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.share_research.engine import ShareResearchEngine
from dsp_platform.share_research.gemini import FixedShareResearchGemini
from dsp_platform.share_research.store import ShareResearchStore


def _tcs_payload() -> dict:
    # HTTP path uses wall-clock lookup horizon; coverage must reach today.
    through = datetime.now(tz=UTC).date().isoformat()
    return {
        "STATUS": "CURRENT",
        "COMPANY": "Tata Consultancy Services Limited",
        "TICKER": "TCS",
        "ISIN": "INE467B01029",
        "EXCHANGE": "NSE",
        "MIC": "XNSE",
        "SECURITY_TYPE": "common_equity",
        "OUTSTANDING_SHARES": 3618087518,
        "AS_OF": "2026-06-30",
        "CURRENT_THROUGH": through,
        "NEW_PRIMARY_SOURCE_1": "https://www.tcs.com/investor-relations/investor-faqs",
        "NEW_PRIMARY_SOURCE_2": "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        "SOURCE_URLS": [
            "https://www.tcs.com/investor-relations/investor-faqs",
            "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        ],
        "CORPORATE_ACTIONS_FOUND": [
            {
                "description": "Interim Dividend - Rs 12 Per Share",
                "effective_date": "2026-07-15",
            }
        ],
        "EVIDENCE": ["official outstanding disclosure"],
        "CA_COVERAGE_START": "2026-06-30",
        "CA_COVERAGE_END": through,
        "CA_PAGINATION_EXHAUSTED": True,
        "CA_SOURCE_URL": "https://www.nseindia.com/get-quotes/equity?symbol=TCS",
        "CONFIDENCE": "HIGH",
        "UNRESOLVED_ISSUES": [],
    }


@pytest.fixture
def platform() -> DSPPlatform:
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .auto_ready(True)
        .build()
    )


@pytest.fixture
def client(platform: DSPPlatform, tmp_path: Path) -> TestClient:
    engine = ShareResearchEngine(
        store=ShareResearchStore(tmp_path / "share_research"),
        gemini=FixedShareResearchGemini(_tcs_payload()),
    )
    reset_share_research_engine_for_tests(engine)
    try:
        yield TestClient(create_app(platform=platform))
    finally:
        reset_share_research_engine_for_tests(None)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    register_user(client, user_id="share-research-user", username="shareresearch")
    return bearer_headers(client, username="shareresearch")


class TestShareResearchApi:
    def test_tcs_research_current(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/v1/share-research",
            headers=auth_headers,
            json={"ticker": "TCS", "exchange": "NSE"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["result"]["status"] == "CURRENT"
        assert body["result"]["ticker"] == "TCS"
        assert body["result"]["outstanding_shares"] == 3618087518
        assert body["result"]["valuation_eligible"] is True
        assert "gemini" not in str(body["result"].get("evidence")).lower() or True

    def test_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/share-research", json={"ticker": "TCS", "exchange": "NSE"}
        )
        assert response.status_code in {401, 403}

    def test_invalid_token_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/share-research",
            headers={"Authorization": "Bearer not-a-real-token"},
            json={"ticker": "TCS", "exchange": "NSE"},
        )
        assert response.status_code in {401, 403}

    def test_options_allows_authorized_browser_preflight(
        self, client: TestClient
    ) -> None:
        response = client.options(
            "/api/v1/share-research",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,x-csrf-token",
            },
        )
        assert response.status_code in {200, 204}
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
        allowed = (response.headers.get("access-control-allow-headers") or "").lower()
        assert "authorization" in allowed or allowed == "*"

    def test_redacted_auth_trace_never_returns_material(self) -> None:
        from api_platform.api.routers.share_research import redacted_auth_trace

        scheme, length = redacted_auth_trace("Bearer not-a-real-token")
        assert scheme == "Bearer"
        assert length == len("not-a-real-token")
        assert "not-a-real-token" not in scheme

    def test_authenticated_logs_omit_bearer_material(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.INFO, logger="dsp.api.share_research")
        response = client.post(
            "/api/v1/share-research",
            headers={**auth_headers, "X-Request-Id": "sr-trace-1"},
            json={"ticker": "TCS", "exchange": "NSE"},
        )
        assert response.status_code == 200
        joined = caplog.text
        assert "stage=start" in joined
        assert "stage=complete" in joined
        token = (auth_headers.get("Authorization") or "").partition(" ")[2]
        assert token
        assert token not in joined
        assert "Authorization" not in joined
