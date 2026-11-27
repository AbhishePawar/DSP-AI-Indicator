"""Native source discovery regression tests."""

from unittest.mock import Mock

import pytest

from llm_adapters.web_research import OpenAIWebResearch


@pytest.fixture
def response_data():

    return {
        "status": "completed",
        "output": [
            {
                "type": "web_search_call",
                "status": "completed",
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://www.infosys.com/report",
                                "title": "Annual report",
                            }
                        ],
                    }
                ],
            },
        ],
    }


def test_completed_search(response_data):

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert result.status == "discovered"
    assert len(result.sources) == 1

    assert result.sources[0].url == (
        "https://www.infosys.com/report"
    )


def test_incomplete_response(response_data):

    response_data["status"] = "incomplete"

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert result.status == "unavailable"


def test_search_required(response_data):

    response_data["output"].pop(0)

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert result.limitation == (
        "web_search_not_completed"
    )


def test_duplicate_citations(response_data):

    annotations = response_data["output"][1][
        "content"
    ][0]["annotations"]

    annotations.append(dict(annotations[0]))

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert len(result.sources) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://www.infosys.com/report",
        "file:///etc/passwd",
        "https://user:password@example.com",
        "https://example.com:8080/report",
        "not-a-url",
    ],
)
def test_invalid_source_urls(response_data, url):

    response_data["output"][1]["content"][0][
        "annotations"
    ][0]["url"] = url

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert result.status == "unavailable"


def test_no_citations(response_data):

    response_data["output"][1]["content"][0][
        "annotations"
    ] = []

    result = OpenAIWebResearch._parse_response(
        response_data
    )

    assert result.limitation == "no_source_citations"


def test_provider_error(monkeypatch):

    monkeypatch.setenv(
        "OPENAI_API_KEY_5", "mock-test-key"
    )

    client = Mock()
    client.post.return_value.status_code = 503

    result = OpenAIWebResearch(
        client=client
    ).discover("Find an official annual report")

    assert result.status == "unavailable"
    assert result.limitation == "provider_http_503"


def test_missing_credentials(monkeypatch):

    monkeypatch.delenv(
        "OPENAI_API_KEY_5", raising=False
    )

    client = Mock()

    result = OpenAIWebResearch(
        client=client
    ).discover("Find an official annual report")

    assert result.status == "unavailable"

    client.post.assert_not_called()


def test_native_search_request(monkeypatch, response_data):

    monkeypatch.setenv(
        "OPENAI_API_KEY_5", "mock-test-key"
    )

    client = Mock()
    client.post.return_value.status_code = 200
    client.post.return_value.json.return_value = response_data

    result = OpenAIWebResearch(
        client=client
    ).discover("Find an official annual report")

    assert result.status == "discovered"

    payload = client.post.call_args.kwargs["json"]

    assert payload["store"] is False
    assert payload["tool_choice"] == "required"
    assert payload["tools"] == [
        {"type": "web_search"}
    ]
