import io

import pytest

from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    UrlSafetyError,
    UrlSafetyPolicy,
)


class FakeSocket:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        pass

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.payload)

    def close(self):
        self.closed = True


class FakeTLS:
    def wrap_socket(self, sock, server_hostname):
        return sock


def execute(payload, limit=100):
    sock = FakeSocket(payload)

    fetcher = DefaultSafeHttpFetcher(
        policy=UrlSafetyPolicy(max_body_bytes=limit),
        socket_connector=lambda *args: sock,
    )

    try:
        return fetcher._execute_request(
            target_ip="8.8.8.8",
            hostname="example.com",
            port=443,
            path="/",
            ssl_ctx=FakeTLS(),
        )
    finally:
        assert sock.closed


def test_content_length():
    status, headers, body = execute(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 5\r\n\r\nhello"
    )
    assert status == 200
    assert body == b"hello"


def test_chunked_response():
    status, headers, body = execute(
        b"HTTP/1.1 200 OK\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n"
        b"5\r\nhello\r\n"
        b"6\r\n world\r\n"
        b"0\r\n\r\n"
    )
    assert status == 200
    assert body == b"hello world"


def test_truncated_response():
    with pytest.raises(UrlSafetyError):
        execute(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 100\r\n\r\nhello"
        )


def test_oversized_response():
    with pytest.raises(UrlSafetyError):
        execute(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Length: 6\r\n\r\nabcdef",
            limit=5,
        )


def test_invalid_status_line():
    with pytest.raises(UrlSafetyError):
        execute(b"INVALID RESPONSE\r\n\r\n")


def test_unsupported_encoding():
    with pytest.raises(UrlSafetyError):
        execute(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Encoding: gzip\r\n"
            b"Content-Length: 5\r\n\r\nhello"
        )


def test_truncated_chunk():
    with pytest.raises(UrlSafetyError):
        execute(
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
            b"10\r\nhello"
        )


@pytest.mark.parametrize("status", [204, 206, 400, 403, 404, 429, 500, 503])
def test_non_success_document_rejected(monkeypatch, status):
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
            status,
            {"content-type": "text/plain"},
            b"RELIANCE outstanding shares 1000000",
        ),
    )

    with pytest.raises(UrlSafetyError):
        fetcher.fetch("https://example.com/report")


def test_success_document_accepted(monkeypatch):
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
            {"content-type": "text/plain"},
            b"Financial report",
        ),
    )

    result = fetcher.fetch("https://example.com/report")

    assert result.status_code == 200
    assert result.text_content == "Financial report"
