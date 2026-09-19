"""Unit tests for the canonical DSP → OpenAI → validation bridge."""

from __future__ import annotations

from types import SimpleNamespace

from copilot.enums import LanguageModelStatus
from copilot.models import LanguageModelResult
from dsp_platform.research_validation import (
    CanonicalValidationResult,
    CanonicalValidationStatus,
)

from api_platform.api import research_company_service as service


class _FakeAdapter:
    provider_id = "openai"
    model_label = "test-model"

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    def invoke(self, _request: object) -> LanguageModelResult:
        self.calls += 1
        return LanguageModelResult(
            result_id="result-1",
            status=LanguageModelStatus.COMPLETE,
            provenance=("test",),
            narrative_text=self.text,
            structured_sections=(),
            model_label=self.model_label,
        )


class _FakeRegistry:
    def __init__(self, adapter: _FakeAdapter, provider: str = "openai") -> None:
        self.adapter = adapter
        self.config = SimpleNamespace(default_provider=provider, max_retries=0)

    def get(self, provider_id: str):
        return self.adapter if provider_id == "openai" else None


class _FakeReport:
    def to_public_dict(self) -> dict[str, object]:
        return {"schema_version": "public-test"}


def test_openai_is_required_for_research() -> None:
    adapter = _FakeAdapter("{}")
    result = service.execute_research_company(
        platform=object(),
        ticker="TCS",
        exchange="NSE",
        company=None,
        registry=_FakeRegistry(adapter, provider="deterministic"),
    )
    assert result.ok is False
    assert result.state == "ai_unavailable"
    assert adapter.calls == 0


def test_openai_draft_is_sent_to_dsp_validator(monkeypatch) -> None:
    adapter = _FakeAdapter('{"executive_summary":"validated"}')
    registry = _FakeRegistry(adapter)

    monkeypatch.setattr(
        service,
        "build_composition_request",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        service,
        "build_research_package",
        lambda _pipeline, request=None: object(),
    )
    monkeypatch.setattr(
        service,
        "build_private_research_prompt",
        lambda _package: SimpleNamespace(
            instructions="private DSP methodology",
            data_block="{\"research_package\":{}}",
        ),
    )

    seen: dict[str, object] = {}

    def _validate(package, ai_payload):
        seen["package"] = package
        seen["payload"] = ai_payload
        return CanonicalValidationResult(
            status=CanonicalValidationStatus.VALID,
            report=_FakeReport(),  # type: ignore[arg-type]
            issues=(),
        )

    monkeypatch.setattr(service, "validate_canonical_research", _validate)

    platform = SimpleNamespace(
        compose_intelligence=lambda _request: SimpleNamespace(
            payload=SimpleNamespace(ok=True),
        )
    )

    result = service.execute_research_company(
        platform=platform,
        ticker="TCS",
        exchange="NSE",
        company="Tata Consultancy Services",
        registry=registry,
    )

    assert result.ok is True
    assert result.state == "ai_executed"
    assert result.outcome == "success"
    assert result.report == {"schema_version": "public-test"}
    assert seen["payload"] == {"executive_summary": "validated"}
    assert adapter.calls == 1


def test_invalid_json_fails_closed(monkeypatch) -> None:
    adapter = _FakeAdapter("not-json")
    registry = _FakeRegistry(adapter)
    monkeypatch.setattr(
        service,
        "build_composition_request",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        service,
        "build_research_package",
        lambda _pipeline, request=None: object(),
    )
    monkeypatch.setattr(
        service,
        "build_private_research_prompt",
        lambda _package: SimpleNamespace(instructions="private", data_block="{}"),
    )

    platform = SimpleNamespace(
        compose_intelligence=lambda _request: SimpleNamespace(
            payload=SimpleNamespace(ok=True),
        )
    )

    result = service.execute_research_company(
        platform=platform,
        ticker="TCS",
        exchange="NSE",
        company=None,
        registry=registry,
    )

    assert result.ok is False
    assert result.state == "ai_validation_failed"
    assert result.report is None
