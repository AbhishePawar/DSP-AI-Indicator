"""The default pinned-IP connector must call socket.create_connection correctly."""

from __future__ import annotations

import socket

import pytest

from dsp_platform.research_retrieval import url_safety


def test_default_connector_passes_address_tuple(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_create_connection(address: object, timeout: object = None) -> str:
        seen["address"] = address
        seen["timeout"] = timeout
        return "sock"

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    fetcher = url_safety.DefaultSafeHttpFetcher()
    assert fetcher._socket_connector("93.184.216.34", 443, 7.5) == "sock"
    assert seen == {"address": ("93.184.216.34", 443), "timeout": 7.5}
