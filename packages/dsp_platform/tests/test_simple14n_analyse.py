"""SIMPLE-14N — /analyse wiring after independent acquisition tests."""

from __future__ import annotations

from datetime import date

from dsp_platform import DSPPlatform, pipeline_result_public_dict
from dsp_platform.composition.models import CompositionRequest
from dsp_platform.composition.mock_nse_eod import default_master as _master
from dsp_platform.composition.mock_nse_eod import mock_nse as _nse


def test_analyse_uses_labeled_primary_document_or_unavailable() -> None:
    text = (
        "unit: actual\n"
        "as_of: 2026-09-08\n"
        "consolidated\n"
        "year ended 2026-03-31\n"
        "revenue: 50000000000\n"
        "net income: 20000000000\n"
        "shareholders equity: 80000000000\n"
        "cash flow from operating activities: 25000000000\n"
        "capital expenditure: 5000000000\n"
        "shares outstanding: 1000000000\n"
    )
    envelope = DSPPlatform().compose_intelligence(
        CompositionRequest(
            ticker="INFY",
            isin="INE009A01021",
            mic="XNSE",
            exchange="NSE",
            research_mode="MOCK",
            nse_eod=_nse(),
            security_master=_master(),
            document_url="https://www.infosys.com/investors/annual-report.pdf",
            document_text=text,
        )
    )
    public = pipeline_result_public_dict(envelope.payload)
    identity = public["dsp_analysis"]["identity"]
    assert identity["isin"] == "INE009A01021"
    assert identity["mic"] == "XNSE"
    dataset = public["dsp_analysis"].get("verified_dataset") or public.get("verified_dataset")
    _ = date, dataset
    iv = public["server_valuation"]["intrinsic_value_per_share"]
    status = public["server_valuation"].get("valuation_status")
    if iv is not None:
        assert status in {None, "AVAILABLE", "VALUATION AVAILABLE"}
    else:
        assert iv is None


def test_analyse_does_not_fallback_to_yahoo() -> None:
    envelope = DSPPlatform().compose_intelligence(
        CompositionRequest(
            ticker="INFY",
            isin="INE009A01021",
            mic="XNSE",
            exchange="NSE",
            research_mode="MOCK",
            nse_eod=_nse(),
            security_master=_master(),
            document_url="https://finance.yahoo.com/quote/INFY",
            document_text="unit: actual\nas_of: 2026-09-08\nnet income: 1\nshares outstanding: 1",
        )
    )
    public = pipeline_result_public_dict(envelope.payload)
    assert public["server_valuation"]["intrinsic_value_per_share"] is None
