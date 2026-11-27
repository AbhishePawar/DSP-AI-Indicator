import hashlib

import pytest

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyError,
)


def make_fetcher(monkeypatch, raw):
    fetcher = DefaultSafeHttpFetcher()

    monkeypatch.setattr(
        fetcher,
        "_validate_and_resolve_destination",
        lambda url: ("example.com", "8.8.8.8"),
    )

    monkeypatch.setattr(
        fetcher,
        "_execute_request",
        lambda **kwargs: (
            200,
            {"content-type": "text/html"},
            raw,
        ),
    )

    return fetcher


def test_html_fetcher_integration(monkeypatch):
    raw = (
        b"<h1>RELIANCE</h1>"
        b"<script>Fake shares 999999</script>"
        b"<p>Outstanding shares 1000000</p>"
    )

    document = make_fetcher(monkeypatch, raw).fetch(
        "https://example.com/report"
    )

    assert "RELIANCE" in document.text_content
    assert "Outstanding shares 1000000" in document.text_content
    assert "999999" not in document.text_content
    assert document.content_hash == hashlib.sha256(raw).hexdigest()
    assert document.content_type == "text/html"


def test_empty_html_rejected(monkeypatch):
    fetcher = make_fetcher(
        monkeypatch,
        b"<html><script>Fake evidence</script></html>",
    )

    with pytest.raises(UrlSafetyError):
        fetcher.fetch("https://example.com/report")


def test_financial_table_preserved(monkeypatch):
    raw = (
        b"<table>"
        b"<tr><th>Metric</th><th>2026</th><th>2025</th></tr>"
        b"<tr><td>Revenue</td><td>1000</td><td>800</td></tr>"
        b"</table>"
    )

    document = make_fetcher(monkeypatch, raw).fetch(
        "https://example.com/report"
    )

    assert "| Metric | 2026 | 2025" in document.text_content
    assert "| Revenue | 1000 | 800" in document.text_content
