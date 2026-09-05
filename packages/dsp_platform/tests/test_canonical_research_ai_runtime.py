"""Provider-backed CanonicalResearchAiPort — Gemini web research mapping."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass
from data_engine.share_count import ShareCountSnapshot
from data_engine.share_count.acceptance import ShareCountAcceptanceError
from dsp_platform.canonical_research_ai import (
    CanonicalResearchAiBlockedError,
    ProductionBlockedCanonicalResearchAiPort,
)
from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.canonical_research_ai_runtime import (
    ProviderBackedCanonicalResearchAiPort,
)
from dsp_platform.current_outstanding_protocol import (
    CurrentOutstandingDiagnostic,
    production_current_outstanding_protocol,
    untrusted_web_claims_from_ai_draft,
)
from dsp_platform.current_outstanding_protocol.prompt import (
    WEB_RESEARCH_CANARY,
    build_share_count_web_research_prompt,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
)
from dsp_platform.primary_source_retrieval.testing import (
    FIXTURE_IDENTITY,
    FIXTURE_LOCATOR,
)
from dsp_platform.research_prompt.models import PrivateResearchPrompt
from dsp_platform.share_count_evidence import (
    accept_share_count_from_validated_evidence,
)
from llm_adapters import GeminiAdapter
from llm_adapters.activation_evidence import ActivationEvidence
from llm_adapters.activation_guard import ActivationState, evaluate_activation
from llm_adapters.config import LLMPlatformConfig

FIXED = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _config() -> LLMPlatformConfig:
    return LLMPlatformConfig(
        default_provider="gemini",
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key="test-gemini",
        deepseek_api_key=None,
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model="gemini-2.5-flash",
        deepseek_model="deepseek-chat",
        request_timeout_seconds=5.0,
        max_retries=0,
    )


def _prompt() -> PrivateResearchPrompt:
    return build_share_count_web_research_prompt(
        ExternalEvidenceDiscoveryRequest(
            identity=FIXTURE_IDENTITY,
            fact_id="current_outstanding",
            retrieved_at=FIXED,
        )
    )


def _instrument() -> Instrument:
    return Instrument(
        symbol="DSPX",
        asset_class=AssetClass.EQUITY,
        currency="USD",
        exchange="TESTEX",
        isin="DSPX00000001",
        name="DSP Test Synthetic Co",
    )


def _grounded_body() -> dict[str, Any]:
    claim = {
        "company": "DSPX",
        "ticker": "DSPX",
        "exchange": "TESTEX",
        "shares_outstanding": 100,
        "unit": "shares",
        "as_of": "2024-03-31",
        "source_name": "Annual report",
        "source_url": FIXTURE_LOCATOR,
        "source_type": "filing",
        "evidence_excerpt": (
            "As of 31 March 2024, issued and outstanding shares were 100 shares."
        ),
        "explanation": "Note 12 states current issued and outstanding shares.",
        "claim_type": "CURRENT_OUTSTANDING",
    }
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps({"web_claims": [claim]})}]
                },
                "groundingMetadata": {
                    "groundingChunks": [
                        {
                            "web": {
                                "uri": FIXTURE_LOCATOR,
                                "title": "DSPX FY24 annual report",
                            }
                        }
                    ]
                },
            }
        ]
    }


def _mock_response(body: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = body
    return resp


class TestProviderBackedCanonicalResearchAiPort:
    def test_activation_off_raises_and_does_not_call_http(self) -> None:
        verdict = evaluate_activation(ActivationEvidence.missing())
        assert verdict.state is ActivationState.AI_PRODUCTION_BLOCKED
        port = ProviderBackedCanonicalResearchAiPort(
            GeminiAdapter(_config()),
            activation_ready=verdict.is_ready(),
        )
        with (
            patch("llm_adapters.gemini_adapter.httpx.Client") as cls,
            pytest.raises(CanonicalResearchAiBlockedError),
        ):
            port.interpret(_prompt())
        cls.assert_not_called()

    def test_maps_gemini_response_to_untrusted_canonical_draft(self) -> None:
        port = ProviderBackedCanonicalResearchAiPort(
            GeminiAdapter(_config()),
            activation_ready=True,
        )
        captured: dict[str, Any] = {}

        def fake_post(*args: Any, **kwargs: Any) -> MagicMock:
            captured["json"] = kwargs.get("json")
            return _mock_response(_grounded_body())

        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.side_effect = fake_post
            draft = port.interpret(_prompt())
        system = captured["json"]["systemInstruction"]["parts"][0]["text"]
        assert WEB_RESEARCH_CANARY in system
        assert isinstance(draft, CanonicalAIDraft)
        assert draft.output.intrinsic_value is None
        assert draft.output.margin_of_safety is None
        assert draft.output.recommendation_action is None
        payload = draft.untrusted_extraction or {}
        assert payload["trusted"] is False
        assert payload["may_create_snapshot"] is False
        claims = untrusted_web_claims_from_ai_draft(draft)
        assert len(claims) == 1
        assert claims[0].source_url == FIXTURE_LOCATOR
        assert claims[0].to_dict()["trusted"] is False

    def test_malformed_gemini_output_fails_closed(self) -> None:
        port = ProviderBackedCanonicalResearchAiPort(
            GeminiAdapter(_config()),
            activation_ready=True,
        )
        body = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = (
                _mock_response(body)
            )
            with pytest.raises(CanonicalResearchAiBlockedError):
                port.interpret(_prompt())

    def test_gemini_cannot_construct_snapshot_or_enter_valuation(self) -> None:
        port = ProviderBackedCanonicalResearchAiPort(
            GeminiAdapter(_config()),
            activation_ready=True,
        )
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = (
                _mock_response(_grounded_body())
            )
            draft = port.interpret(_prompt())
        assert not isinstance(draft, ShareCountSnapshot)
        with pytest.raises(ShareCountAcceptanceError, match="AI narrative"):
            accept_share_count_from_validated_evidence(draft, symbol="DSPX")

    def test_gemini_cannot_modify_valuation_or_recommendation_state(self) -> None:
        valuation_state = {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        recommendation_state = {"action": "HOLD"}
        port = ProviderBackedCanonicalResearchAiPort(
            GeminiAdapter(_config()),
            activation_ready=True,
        )
        with patch("llm_adapters.gemini_adapter.httpx.Client") as cls:
            cls.return_value.__enter__.return_value.post.return_value = (
                _mock_response(_grounded_body())
            )
            draft = port.interpret(_prompt())
        assert draft.output.intrinsic_value is None
        assert draft.output.recommendation_action is None
        assert valuation_state == {"intrinsic_value": 42.0, "margin_of_safety": 0.3}
        assert recommendation_state == {"action": "HOLD"}

    def test_production_protocol_still_uses_blocked_port(self) -> None:
        blocked = ProductionBlockedCanonicalResearchAiPort()
        with pytest.raises(CanonicalResearchAiBlockedError):
            blocked.interpret(_prompt())
        result = production_current_outstanding_protocol().resolve(
            _instrument(),
            identity=FIXTURE_IDENTITY,
            retrieved_at=FIXED,
        )
        assert result.current_shares_outstanding is None
        assert (
            result.diagnostic
            is CurrentOutstandingDiagnostic.EVIDENCE_DISCOVERY_BLOCKED
        )
