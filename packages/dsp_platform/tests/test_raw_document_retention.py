from hashlib import sha256

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyPolicy,
)


def make_fetcher(monkeypatch, raw):

    fetcher = DefaultSafeHttpFetcher(
        policy=UrlSafetyPolicy(
            max_redirects=0
        )
    )

    monkeypatch.setattr(
        fetcher,
        "_validate_and_resolve_destination",
        lambda url: (
            "www.sec.gov",
            "8.8.8.8",
        ),
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


def test_original_document_bytes_preserved(monkeypatch):

    raw = b"<html><p>Revenue: 100</p></html>"

    fetcher = make_fetcher(monkeypatch, raw)

    document, returned = fetcher.fetch_with_raw(
        "https://www.sec.gov/example.htm"
    )

    assert returned == raw

    assert document.content_hash == (
        sha256(raw).hexdigest()
    )

    assert document.text_content == "Revenue: 100"


def test_existing_fetch_contract_preserved(monkeypatch):

    raw = b"<p>Financial statement</p>"

    fetcher = make_fetcher(monkeypatch, raw)

    document = fetcher.fetch(
        "https://www.sec.gov/example.htm"
    )

    assert document.text_content == "Financial statement"

    assert document.content_hash == (
        sha256(raw).hexdigest()
    )


def test_raw_html_not_replaced_by_extracted_text(monkeypatch):

    raw = b"<p><b>Assets</b></p>"

    fetcher = make_fetcher(monkeypatch, raw)

    document, returned = fetcher.fetch_with_raw(
        "https://www.sec.gov/example.htm"
    )

    assert returned == raw
    assert document.text_content == "Assets"
    assert returned != document.text_content.encode()
