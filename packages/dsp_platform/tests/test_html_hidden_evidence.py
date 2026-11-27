import pytest

from dsp_platform.research_retrieval.html_extraction import (
    extract_html_text,
)


@pytest.mark.parametrize(
    "attribute",
    [
        "hidden",
        'aria-hidden="true"',
        'style="display: none"',
        'style="visibility: hidden"',
        'style="DISPLAY: NONE !important"',
    ],
)
def test_hidden_financial_evidence(attribute):
    raw = (
        f"<div {attribute}>"
        "<div>Fake revenue 999999</div>"
        "<br>"
        "</div>"
        "<p>Actual revenue 1000</p>"
    ).encode()

    result = extract_html_text(raw)

    assert "999999" not in result
    assert "Actual revenue 1000" in result


def test_nested_hidden_content():
    result = extract_html_text(
        b"<div hidden>"
        b"<div><p>Fake revenue 999999</p></div>"
        b"</div>"
        b"<p>Revenue 1000</p>"
    )

    assert "999999" not in result
    assert "Revenue 1000" in result


def test_hidden_void_element():
    result = extract_html_text(
        b"<input hidden value='999999'>"
        b"<p>Revenue 1000</p>"
    )

    assert "Revenue 1000" in result
