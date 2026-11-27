"""Security regression tests for issuer domain authorization."""

import pytest

from dsp_platform.research_retrieval.issuer_registry import (
    resolve_issuer,
    issuer_url_is_approved,
)


def check(url, **overrides):

    args = {
        "ticker": "INFY",
        "exchange": "NSE",
        "isin": "INE009A01021",
        "url": url,
    }

    args.update(overrides)

    return issuer_url_is_approved(**args)


def test_verified_issuer_identity():

    issuer = resolve_issuer("INFY", "NSE")

    assert issuer is not None
    assert issuer.isin == "INE009A01021"


def test_normalized_identity():

    assert resolve_issuer(
        " infy ", " nse "
    ) is not None


def test_unknown_issuer():

    assert resolve_issuer("UNKNOWN", "NSE") is None


@pytest.mark.parametrize("url", [
    "https://www.infosys.com/investors/report.pdf",
    "https://infosys.com/investors/report.pdf",
])
def test_approved_issuer_urls(url):

    assert check(url)


@pytest.mark.parametrize("url", [
    "http://www.infosys.com/investors/report.pdf",
    "https://infosys.com.example.org/investors/report.pdf",
    "https://example.org/investors/report.pdf",
    "https://fakeinfosys.com/investors/report.pdf",
    "https://www.infosys.com@evil.example/investors/report",
    "https://user@www.infosys.com/investors/report",
    "https://www.infosys.com:8080/investors/report",
    "https://unapproved.infosys.com/investors/report",
    "https://www.infosys.com/other/report",
    "https://127.0.0.1/investors/report",
    "file:///etc/passwd",
])
def test_unapproved_urls(url):

    assert not check(url)


@pytest.mark.parametrize("overrides", [
    {"ticker": "TCS"},
    {"exchange": "NYSE"},
    {"isin": "WRONG_ISIN"},
    {"isin": ""},
    {"ticker": ""},
])
def test_identity_mismatch(overrides):

    assert not check(
        "https://www.infosys.com/investors/report.pdf",
        **overrides,
    )
