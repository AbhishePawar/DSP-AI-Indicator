"""Gemini web-research adapter — mocked HTTP, no live Gemini calls."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from llm_adapters.activation_evidence import ActivationEvidence
from llm_adapters.activation_guard import ActivationState, evaluate_activation
from llm_adapters.config import LLMPlatformConfig
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.gemini_grounding import (
    GOOGLE_SEARCH_TOOL,
    google_search_tool_for_model,
    parse_grounded_web_research,
    untrusted_extraction_from_grounded_web_research,
)
from llm_adapters.gemini_web_research import ActivationGatedGeminiWebResearch


def _config(*, model: str = "gemini-1.5-flash", key: str | None = "test-gemini") -> (
    LLMPlatformConfig
):
    return LLMPlatformConfig(
        default_provider="gemini",
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=key,
        deepseek_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model=model,
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def _request(prompt: str = "Find current outstanding shares.") -> LanguageModelRequest:
    return LanguageModelRequest(
        request_id="req-web-1",
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=("DSP CALCULATES. AI RESEARCHES. DSP VALIDATES.", prompt),
        context_digest_ids=("recommendation",),
        provenance=("test", "dsp.llm.gemini.web_research.v1"),
        constraints=("Return JSON web_claims only.",),
    )


def _mock_response(json_body: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_body
    return resp


def _claim() -> dict[str, Any]:
    return {
        "company": "TCS",
        "ticker": "TCS",
        "exchange": "NSE",
        "shares_outstanding": 3618087514,
        "unit": "shares",
        "as_of": "2024-03-31",
        "source_name": "Screener",
        "source_url": "https://www.screener.in/company/TCS/",
        "source_type": "company_website",
        "evidence_excerpt": (
            "Shares outstanding as of 31 March 2024 were 3,618,087,514."
        ),
        "evidence_reference": "Screener company page",
        "explanation": "The page labels the figure as current shares outstanding.",
        "claim_type": "CURRENT_OUTSTANDING",
        "retrieved_at": "2024-06-15T12:00:00+00:00",
    }


def _grounded_body(
    *, text: str | None = None, citations: bool = True
) -> dict[str, Any]:
    payload = {"web_claims": [_claim()]}
    body_text = text if text is not None else json.dumps(payload)
    candidate: dict[str, Any] = {
        "content": {"parts": [{"text": body_text}]}
    }
    if citations:
        candidate["groundingMetadata"] = {
            "webSearchQueries": ["TCS shares outstanding"],
            "groundingChunks": [
                {
                    "web": {
                        "uri": "https://www.screener.in/company/TCS/",
                        "title": "Tata Consultancy Services Ltd",
                    }
                }
            ],
        }
    return {"candidates": [candidate]}


class TestGoogleSearchToolSelection:
    def test_current_models_use_google_search(self) -> None:
        assert google_search_tool_for_model("gemini-2.5-flash") == GOOGLE_SEARCH_TOOL

    def test_gemini_1_5_uses_documented_retrieval_tool(self) -> None:
        tool = google_search_tool_for_model("gemini-1.5-flash")
        assert "googleSearchRetrieval" in tool


class TestGeminiWebResearchAdapter:
    def test_sends_canonical_prompt_and_google_search_tool(self) -> None:
        adapter = GeminiAdapter(_config(model="gemini-2.5-flash"))
        captured: dict[str, Any] = {}

        def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
            captured["json"] = kwargs.get("json")
            return _mock_response(_grounded_body())

        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.side_effect = fake_post
            result, grounded = adapter.invoke_web_research(_request())
        payload = captured["json"]
        system = payload["systemInstruction"]["parts"][0]["text"]
        user = payload["contents"][0]["parts"][0]["text"]
        assert system.startswith("DSP CALCULATES")
        assert "Find current outstanding shares." in user
        assert payload["tools"] == [GOOGLE_SEARCH_TOOL]
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert result.status is LanguageModelStatus.COMPLETE
        assert grounded.citations[0].uri == "https://www.screener.in/company/TCS/"

    def test_invoke_still_does_not_send_search_or_functions(self) -> None:
        adapter = GeminiAdapter(_config())
        captured: dict[str, Any] = {}

        def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
            captured["json"] = kwargs.get("json")
            return _mock_response(
                {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
            )

        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.side_effect = fake_post
            adapter.invoke(_request())
        assert "tools" not in captured["json"]
        assert "googleSearch" not in json.dumps(captured["json"])

    def test_maps_structured_json_and_preserves_citation(self) -> None:
        adapter = GeminiAdapter(_config())
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = _mock_response(
                _grounded_body()
            )
            result, grounded = adapter.invoke_web_research(_request())
        extraction = untrusted_extraction_from_grounded_web_research(grounded)
        assert result.narrative_text is not None
        assert extraction["trusted"] is False
        assert extraction["may_create_snapshot"] is False
        assert extraction["web_claims"][0]["source_url"] == (
            "https://www.screener.in/company/TCS/"
        )
        assert extraction["grounding_citations"][0]["source_url"] == (
            "https://www.screener.in/company/TCS/"
        )
        assert "intrinsic_value" not in extraction
        assert "recommendation" not in extraction

    def test_missing_citation_is_safe_and_keeps_json_url(self) -> None:
        grounded = parse_grounded_web_research(
            _grounded_body(citations=False),
            narrative_text=json.dumps({"web_claims": [_claim()]}),
            status="complete",
        )
        assert grounded.missing_citations is True
        extraction = untrusted_extraction_from_grounded_web_research(grounded)
        assert extraction["missing_citations"] is True
        assert extraction["web_claims"][0]["source_url"]

    def test_malformed_output_fails_closed(self) -> None:
        adapter = GeminiAdapter(_config())
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = _mock_response(
                _grounded_body(text="not json")
            )
            result, grounded = adapter.invoke_web_research(_request())
        assert result.status is LanguageModelStatus.FAILED
        assert grounded.malformed is True
        extraction = untrusted_extraction_from_grounded_web_research(grounded)
        assert extraction["web_claims"] == []
        assert extraction["may_create_snapshot"] is False

    def test_naked_text_without_json_is_not_evidence(self) -> None:
        extraction = untrusted_extraction_from_grounded_web_research(
            parse_grounded_web_research(
                {},
                narrative_text="TCS has about 362 crore shares outstanding.",
                status="complete",
            )
        )
        assert extraction["malformed"] is True
        assert extraction["web_claims"] == []

    def test_activation_off_does_not_call_http(self) -> None:
        verdict = evaluate_activation(ActivationEvidence.missing())
        assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
        gated = ActivationGatedGeminiWebResearch(
            GeminiAdapter(_config()),
            activation_ready=verdict.is_ready(),
        )
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            result, grounded = gated.invoke_web_research(_request())
        cls.assert_not_called()
        assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE
        assert grounded.status == "unavailable"
        assert "AI_PRODUCTION_BLOCKED" in result.limitations

    def test_missing_credentials_do_not_call_http(self) -> None:
        adapter = GeminiAdapter(_config(key=None))
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            result, grounded = adapter.invoke_web_research(_request())
        cls.assert_not_called()
        assert result.status is LanguageModelStatus.PROVIDER_UNAVAILABLE
        assert grounded.citations == ()

    def test_http_status_is_copied_without_response_body(self) -> None:
        adapter = GeminiAdapter(_config())
        response = MagicMock()
        response.status_code = 404
        response.json.return_value = {
            "error": {"status": "NOT_FOUND", "message": "secret-should-not-leak"}
        }
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "not found",
            request=MagicMock(),
            response=response,
        )
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = response
            result, grounded = adapter.invoke_web_research(_request())
        assert result.status is LanguageModelStatus.FAILED
        assert result.limitations == ("http_error: HTTPStatusError:404:NOT_FOUND",)
        assert "secret-should-not-leak" not in str(result.limitations)
        assert grounded.citations == ()
