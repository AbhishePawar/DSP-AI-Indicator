"""Tests for AnalyseRequest mode contract and backward compatibility."""

import pytest
from api_platform.api.composition_schemas import AnalyseRequest, AnalyseResponse


def test_analyse_request_default_mode_is_buffett():
    req = AnalyseRequest(ticker="TCS.NS")
    assert req.mode == "buffett"
    assert req.ticker == "TCS.NS"


def test_analyse_request_accepts_simple_mode():
    req = AnalyseRequest(ticker="INFY.NS", mode="simple")
    assert req.mode == "simple"
    assert req.ticker == "INFY.NS"


def test_analyse_request_accepts_buffett_mode():
    req = AnalyseRequest(ticker="RELIANCE.NS", mode="buffett")
    assert req.mode == "buffett"
    assert req.ticker == "RELIANCE.NS"


def test_analyse_response_includes_mode():
    res = AnalyseResponse(
        ok=True,
        capability="compose_intelligence",
        payload={"test": 1},
        mode="simple",
    )
    assert res.mode == "simple"
