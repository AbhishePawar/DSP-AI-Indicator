"""Request / correlation ID context (PEP-003)."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

from production_platform.production.logging import new_correlation_id

__all__ = [
    "bind_correlation_id",
    "clear_correlation_id",
    "correlation_context",
    "get_correlation_id",
    "new_request_id",
]

_CORRELATION_ID: ContextVar[str | None] = ContextVar("dsp_correlation_id", default=None)


def new_request_id() -> str:
    """Alias for opaque request / correlation id."""
    return new_correlation_id()


def get_correlation_id() -> str | None:
    return _CORRELATION_ID.get()


def bind_correlation_id(correlation_id: str | None) -> Token[str | None]:
    return _CORRELATION_ID.set(correlation_id)


def clear_correlation_id(token: Token[str | None]) -> None:
    _CORRELATION_ID.reset(token)


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[str]:
    """Bind a correlation id for the current context; yield the active id."""
    cid = correlation_id or new_correlation_id()
    token = bind_correlation_id(cid)
    try:
        yield cid
    finally:
        clear_correlation_id(token)
