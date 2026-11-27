import pytest

from dsp_platform.research_retrieval.html_extraction import (
    HtmlExtractionError,
    extract_html_text,
)


def test_financial_text():
    text = extract_html_text(
        b"<h1>RELIANCE</h1>"
        b"<p>Outstanding shares: 1000000</p>"
    )

    assert "RELIANCE" in text
    assert "Outstanding shares: 1000000" in text


def test_scripts_excluded():
    text = extract_html_text(
        b"<script>Fake revenue 999999</script>"
        b"<p>Revenue 1000</p>"
    )

    assert "999999" not in text
    assert "Revenue 1000" in text


def test_styles_excluded():
    text = extract_html_text(
        b"<style>fake financial content</style>"
        b"<p>Net profit 100</p>"
    )

    assert "fake financial content" not in text
    assert "Net profit 100" in text


def test_table_columns_preserved():
    text = extract_html_text(
        b"<table><tr>"
        b"<th>Metric</th><th>2026</th>"
        b"</tr><tr>"
        b"<td>Revenue</td><td>1000</td>"
        b"</tr></table>"
    )

    assert "| Metric | 2026" in text
    assert "| Revenue | 1000" in text


def test_entities_decoded():
    assert "Profit & Loss" in extract_html_text(
        b"<p>Profit &amp; Loss</p>"
    )


def test_empty_document_rejected():
    with pytest.raises(HtmlExtractionError):
        extract_html_text(b"<html></html>")


def test_oversized_document_rejected():
    with pytest.raises(HtmlExtractionError):
        extract_html_text(
            b"x" * (5 * 1024 * 1024 + 1)
        )


def test_navigation_excluded():
    text = extract_html_text(
        b"<nav>Unrelated company</nav>"
        b"<article>Financial report</article>"
    )

    assert "Unrelated company" not in text
    assert "Financial report" in text
