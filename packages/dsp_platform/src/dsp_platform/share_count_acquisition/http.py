"""Injectable JSON HTTP for acquisition. Tests use recorded pages."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

__all__ = ["JsonHttpPort", "RecordedJsonHttp"]


class JsonHttpPort(Protocol):
    def get_json(
        self, url: str, *, referer: str | None = None
    ) -> Mapping[str, Any] | list[Any] | None:
        """Return parsed JSON or None when the page cannot be retrieved."""
        ...


class RecordedJsonHttp:
    """Deterministic fixture transport. Does not open sockets."""

    def __init__(self, pages: Mapping[str, Mapping[str, Any] | list[Any] | None]) -> None:
        self._pages = dict(pages)
        self.calls: list[str] = []

    def get_json(
        self, url: str, *, referer: str | None = None
    ) -> Mapping[str, Any] | list[Any] | None:
        del referer
        self.calls.append(url)
        if url in self._pages:
            return self._pages[url]
        for key, payload in self._pages.items():
            if key and key in url:
                return payload
        return None
