import pytest

from dsp_platform.research_retrieval.html_extraction import (
    HtmlExtractionError,
    extract_html_text,
)

from dsp_platform.research_retrieval.url_safety import (
    UrlSafetyPolicy,
)


def test_default_limits_preserved():

    policy = UrlSafetyPolicy()

    assert policy.max_html_input_bytes == 5 * 1024 * 1024
    assert policy.max_html_text_chars == 2_000_000


def test_small_document():

    assert extract_html_text(
        b"<p>Financial statement</p>"
    ) == "Financial statement"


def test_default_input_limit():

    raw = b"<p>" + b" " * 6_000_000 + b"Revenue</p>"

    with pytest.raises(
        HtmlExtractionError,
        match="input size limit",
    ):

        extract_html_text(raw)


def test_approved_large_input():

    raw = b"<p>" + b" " * 6_000_000 + b"Revenue</p>"

    assert extract_html_text(
        raw,
        max_input_bytes=10_000_000,
    ) == "Revenue"


def test_default_output_limit():

    raw = b"<p>" + b"A" * 2_100_000 + b"</p>"

    with pytest.raises(
        HtmlExtractionError,
        match="text limit",
    ):

        extract_html_text(raw)


def test_approved_large_output():

    raw = b"<p>" + b"A" * 2_100_000 + b"</p>"

    result = extract_html_text(
        raw,
        max_text_chars=3_000_000,
    )

    assert len(result) == 2_100_000


@pytest.mark.parametrize(
    "limits",
    [
        {"max_input_bytes": 0},
        {"max_input_bytes": 30_000_001},
        {"max_text_chars": 0},
        {"max_text_chars": 8_000_001},
        {"max_input_bytes": True},
        {"max_text_chars": -1},
    ],
)
def test_unsafe_limits_rejected(limits):

    with pytest.raises(HtmlExtractionError):

        extract_html_text(
            b"<p>Revenue</p>",
            **limits,
        )


def test_hidden_content_still_excluded():

    raw = (
        b"<p>Revenue</p>"
        b"<script>Fake revenue</script>"
        b"<div hidden>Hidden data</div>"
    )

    assert extract_html_text(
        raw,
        max_input_bytes=10_000_000,
    ) == "Revenue"
