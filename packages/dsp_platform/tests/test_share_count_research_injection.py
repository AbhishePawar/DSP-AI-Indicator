"""Verify the server-only research callback reaches authenticated valuation."""
from __future__ import annotations

from typing import Any

from dsp_platform import CompositionRequest
from dsp_platform.composition.context import ExecutionContext
from dsp_platform.composition import pipeline


def test_pipeline_passes_researcher_to_authenticated_loader(monkeypatch) -> None:
    callback = lambda ticker, company_name, exchange: None
    bundle = object()
    seen: dict[str, Any] = {}

    def fake_load(ticker, *, exchange, research_missing_shares):
        seen["ticker"] = ticker
        seen["exchange"] = exchange
        seen["research_missing_shares"] = research_missing_shares
        return bundle

    monkeypatch.setattr(pipeline, "load_authenticated_valuation_bundle", fake_load)
    monkeypatch.setattr(pipeline, "to_financial_statements", lambda _: object())
    context = ExecutionContext(
        request=CompositionRequest(
            ticker="ABC",
            exchange="NSE",
            research_missing_shares=callback,
        )
    )

    pipeline._preload_authenticated_valuation_bundle(context)

    assert seen["ticker"] == "ABC"
    assert seen["exchange"] == "NSE"
    assert seen["research_missing_shares"] is callback
    assert context.results["authenticated_valuation_bundle"] is bundle
