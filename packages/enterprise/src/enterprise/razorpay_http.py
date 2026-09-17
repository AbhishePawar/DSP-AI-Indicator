"""Razorpay HTTPS client and HMAC helpers.

Stdlib only — no official SDK, no Vercel/GCP. Tests inject a fake client so
no live charges are created.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__all__ = [
    "DEFAULT_RAZORPAY_API_BASE",
    "RazorpayHttpClient",
    "RazorpayRequestError",
    "UrllibRazorpayHttpClient",
    "checkout_signature",
    "signatures_match",
    "webhook_signature",
]

DEFAULT_RAZORPAY_API_BASE = "https://api.razorpay.com"


class RazorpayRequestError(Exception):
    """Order/payment HTTP failure — never includes secrets or response bodies."""


class RazorpayHttpClient(Protocol):
    """Injectable JSON HTTP boundary for Razorpay REST calls."""

    def post_json(self, path: str, body: Mapping[str, Any]) -> dict[str, Any]: ...

    def get_json(self, path: str) -> dict[str, Any]: ...


def webhook_signature(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 hex digest of the raw webhook body (Razorpay scheme)."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def checkout_signature(order_id: str, payment_id: str, secret: str) -> str:
    """HMAC-SHA256 hex digest of ``{order_id}|{payment_id}`` with key_secret."""
    message = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def signatures_match(expected: str, provided: str | None) -> bool:
    if not expected or provided is None:
        return False
    candidate = str(provided).strip()
    if not candidate:
        return False
    left = expected.encode("utf-8")
    right = candidate.encode("utf-8")
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


class UrllibRazorpayHttpClient:
    """Default Razorpay REST client — Basic Auth, stdlib urllib only."""

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        base_url: str = DEFAULT_RAZORPAY_API_BASE,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._key_id = key_id
        self._key_secret = key_secret
        self._base_url = (base_url or DEFAULT_RAZORPAY_API_BASE).rstrip("/")
        self._timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(
            f"{self._key_id}:{self._key_secret}".encode("utf-8")
        ).decode("ascii")
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def post_json(self, path: str, body: Mapping[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request = Request(
            url,
            data=json.dumps(dict(body)).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        return self._read(request, path)

    def get_json(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        request = Request(url, headers=self._headers(), method="GET")
        return self._read(request, path)

    def _read(self, request: Request, path: str) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            status = int(getattr(exc, "code", 0) or 0)
            raise RazorpayRequestError(f"HTTP {status} for Razorpay {path}") from None
        except (URLError, OSError, TimeoutError):
            raise RazorpayRequestError(
                f"Razorpay request failed for {path}"
            ) from None
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError:
            raise RazorpayRequestError(
                f"Razorpay response for {path} was not JSON"
            ) from None
        if not isinstance(parsed, dict):
            raise RazorpayRequestError(f"Razorpay response for {path} was not an object")
        return parsed
