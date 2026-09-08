"""SIMPLE-14I live research agent qualification tests.

Live HTTP is mocked unless GEMINI_API_KEY is present. Tests never print
credentials and never treat AI consensus as proof.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from data_engine.multi_agent_research.agents import (
    AgentCapabilityState,
    AgentFailureClass,
    AgentRole,
    ScriptedResearchAgent,
    UnavailableResearchAgent,
)
from data_engine.multi_agent_research.contracts import ResearchRequest
from data_engine.multi_agent_research.orchestrator import (
    ResearchOrchestrator,
    ResearchOutcomeStatus,
)
from data_engine.security_identity import IdentityStatus, set_security_master_for_tests
from llm_adapters.anthropic import ClaudeLiveResearchAgent
from llm_adapters.deep_search import DeepSearchLiveResearchAgent
from llm_adapters.gemini import (
    SIMPLE11_BLOCKED_GEMINI_MODELS,
    GeminiLiveResearchAgent,
)
from llm_adapters.openai import ChatGptLiveResearchAgent
from llm_adapters.research import (
    LiveQualificationStatus,
    build_research_agents,
    claims_from_model_output,
    qualification_security_master,
    qualify_agents,
)

_REPO = Path(__file__).resolve().parents[3]


_RealClient = httpx.Client


def _client_factory(handler):
    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealClient(transport=httpx.MockTransport(handler), **kwargs)

    return factory


@pytest.fixture
def catalog_master():
    master = qualification_security_master()
    set_security_master_for_tests(master)
    yield master
    set_security_master_for_tests(None)


def _request() -> ResearchRequest:
    return ResearchRequest(
        research_request_id="rr_nse",
        company="Infosys Limited",
        ticker="INFY",
        isin="INE009A01021",
        exchange="NSE",
        mic="XNSE",
        requested_fields=("listing_status",),
        requested_as_of="2026-03-31",
        research_purpose="qualification",
        created_at=datetime.now(tz=UTC),
        security_type="EQUITY",
        listing_status="LISTED",
        identity_status="RESOLVED",
    )


def test_agents_are_independent_ports() -> None:
    agents = build_research_agents()
    assert type(agents[AgentRole.GEMINI]) is GeminiLiveResearchAgent
    assert type(agents[AgentRole.CHATGPT]) is ChatGptLiveResearchAgent
    assert type(agents[AgentRole.DEEP_SEARCH]) is DeepSearchLiveResearchAgent
    assert type(agents[AgentRole.CLAUDE]) is ClaudeLiveResearchAgent


def test_chatgpt_claude_deep_search_unavailable_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "OPENAI_API_KEY",
        "DSP_AI_OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DSP_AI_ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "DSP_AI_GEMINI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    report = qualify_agents()
    assert report[AgentRole.CHATGPT].status is LiveQualificationStatus.NOT_CONFIGURED
    assert report[AgentRole.CLAUDE].status is LiveQualificationStatus.NOT_CONFIGURED
    assert (
        report[AgentRole.DEEP_SEARCH].status
        is LiveQualificationStatus.CAPABILITY_UNAVAILABLE
    )
    assert report[AgentRole.GEMINI].status is LiveQualificationStatus.NOT_CONFIGURED


def test_deep_search_is_not_a_gemini_alias() -> None:
    probe = DeepSearchLiveResearchAgent().probe()
    assert probe.status is LiveQualificationStatus.CAPABILITY_UNAVAILABLE
    assert "Gemini" in probe.detail


def test_gemini_does_not_retry_simple11_models() -> None:
    agent = GeminiLiveResearchAgent(api_key="x" * 20, model="gemini-2.5-flash")
    result = agent.research(_request())
    assert result.failure is AgentFailureClass.MODEL_NOT_FOUND
    assert result.claims == ()
    assert "gemini-2.5-flash" in SIMPLE11_BLOCKED_GEMINI_MODELS


def test_gemini_list_models_success_is_not_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/models") or "/models" in str(request.url)
        return httpx.Response(
            200,
            json={"models": [{"name": "models/gemini-flash-latest"}]},
        )

    monkeypatch.setattr(
        "llm_adapters.research.http.httpx.Client",
        _client_factory(handler),
    )
    probe = GeminiLiveResearchAgent(
        api_key="x" * 20, model="gemini-flash-latest"
    ).probe_list_models()
    assert probe.status is LiveQualificationStatus.LIVE_AVAILABLE_BUT_UNQUALIFIED
    assert probe.http_status == 200


def test_security_master_nse_bse_dual(catalog_master) -> None:
    orch = ResearchOrchestrator(security_master=catalog_master)
    nse = orch.run(ticker="INFY", exchange="NSE")
    assert nse.identity.status is IdentityStatus.RESOLVED
    assert nse.identity.isin == "INE009A01021"
    assert nse.identity.mic == "XNSE"
    bse = orch.run(ticker="INFY", exchange="BSE")
    assert bse.identity.mic == "XBOM"
    dual = orch.run(ticker="INFY")
    assert dual.status is ResearchOutcomeStatus.IDENTITY_BLOCKED
    assert dual.identity.status is IdentityStatus.AMBIGUOUS
    hdfc = orch.run(ticker="HDFCBANK", exchange="NSE")
    assert hdfc.identity.company == "HDFC Bank Limited"


def test_primary_nse_evidence_can_verify_through_14h_gate(catalog_master) -> None:
    text = json.dumps(
        {
            "field": "listing_status",
            "candidate_value": "LISTED",
            "source": "nse",
            "source_url": "https://www.nseindia.com/get-quote/equity?symbol=INFY",
            "document_date": "2026-03-31",
            "evidence_locator": "equity quote header listing status",
        }
    )
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "groundingMetadata": {
                    "groundingChunks": [
                        {
                            "web": {
                                "uri": (
                                    "https://www.nseindia.com/get-quote/equity"
                                    "?symbol=INFY"
                                )
                            }
                        }
                    ]
                },
            }
        ]
    }
    claims = claims_from_model_output(
        request=_request(),
        agent="gemini",
        text=text,
        payload=payload,
    )
    assert claims[0].source == "nse"
    orch = ResearchOrchestrator(
        security_master=catalog_master,
        agents={
            AgentRole.GEMINI: ScriptedResearchAgent(
                AgentRole.GEMINI,
                claims=claims,
                capability_state=AgentCapabilityState.MOCK,
            ),
            AgentRole.CHATGPT: UnavailableResearchAgent(AgentRole.CHATGPT),
            AgentRole.DEEP_SEARCH: UnavailableResearchAgent(AgentRole.DEEP_SEARCH),
            AgentRole.CLAUDE: UnavailableResearchAgent(AgentRole.CLAUDE),
        },
    )
    result = orch.run(
        ticker="INFY",
        exchange="NSE",
        requested_fields=("listing_status",),
        requested_as_of="2026-03-31",
    )
    assert result.identity.isin == "INE009A01021"
    assert "listing_status" in result.verified_fields


def test_agent_named_as_source_cannot_verify(catalog_master) -> None:
    claims = claims_from_model_output(
        request=_request(),
        agent="gemini",
        text=json.dumps(
            {
                "field": "listing_status",
                "candidate_value": "LISTED",
                "source": "gemini",
                "source_url": "",
            }
        ),
        payload=None,
    )
    orch = ResearchOrchestrator(
        security_master=catalog_master,
        agents={
            AgentRole.GEMINI: ScriptedResearchAgent(AgentRole.GEMINI, claims=claims),
            AgentRole.CHATGPT: UnavailableResearchAgent(AgentRole.CHATGPT),
            AgentRole.DEEP_SEARCH: UnavailableResearchAgent(AgentRole.DEEP_SEARCH),
            AgentRole.CLAUDE: UnavailableResearchAgent(AgentRole.CLAUDE),
        },
    )
    result = orch.run(
        ticker="INFY",
        exchange="NSE",
        requested_fields=("listing_status",),
        requested_as_of="2026-03-31",
    )
    assert result.verified_fields == ()


def test_dsp_package_has_no_live_agent_imports() -> None:
    dsp = _REPO / "packages" / "dsp" / "src" / "dsp"
    for path in dsp.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "llm_adapters.simple14i" not in text
        assert "GeminiLiveResearchAgent" not in text


def test_no_silent_chatgpt_fallback_in_gemini_agent() -> None:
    src = (
        _REPO
        / "packages"
        / "llm_adapters"
        / "src"
        / "llm_adapters"
        / "gemini"
        / "research_agent.py"
    ).read_text(encoding="utf-8")
    assert "openai.com" not in src
    assert "ChatGptLiveResearchAgent" not in src


@pytest.mark.skipif(
    not (os.environ.get("GEMINI_API_KEY") or os.environ.get("DSP_AI_GEMINI_API_KEY")),
    reason="GEMINI_API_KEY not configured on this runtime",
)
def test_live_gemini_list_models_when_key_present() -> None:
    probe = GeminiLiveResearchAgent().probe_list_models()
    assert probe.configured is True
    assert probe.http_status == 200
    assert probe.status is LiveQualificationStatus.LIVE_AVAILABLE_BUT_UNQUALIFIED
