"""Minimal HMAC JWT (EPIC-A009) — stdlib only, deterministic with fixed iat."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from auth.exceptions import InvalidTokenError

__all__ = ["JwtService", "b64url_decode", "b64url_encode"]


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


class JwtService:
    """HS256 JWT issuer/validator — no external JWT dependency."""

    def __init__(self, secret: str = "dsp-auth-dev-secret", *, issuer: str = "dsp-auth") -> None:
        if not secret:
            raise ValueError("jwt secret is required")
        self._secret = secret.encode("utf-8")
        self.issuer = issuer

    def issue(
        self,
        *,
        subject: str,
        claims: Mapping[str, Any] | None = None,
        expires_in: int = 3600,
        issued_at: str | None = None,
        token_id: str | None = None,
        token_use: str = "access",
    ) -> str:
        if issued_at:
            iat_dt = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
        else:
            iat_dt = datetime.now(tz=timezone.utc)
        exp_dt = iat_dt + timedelta(seconds=int(expires_in))
        header = {"alg": "HS256", "typ": "JWT"}
        payload: dict[str, Any] = {
            "iss": self.issuer,
            "sub": subject,
            "iat": int(iat_dt.timestamp()),
            "exp": int(exp_dt.timestamp()),
            "token_use": token_use,
        }
        if token_id:
            payload["jti"] = token_id
        if claims:
            for k in sorted(claims.keys()):
                payload[str(k)] = claims[k]
        return self._encode(header, payload)

    def decode(self, token: str, *, now: datetime | None = None) -> dict[str, Any]:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError as exc:
            raise InvalidTokenError("malformed token") from exc
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(b64url_encode(expected), sig_b64):
            raise InvalidTokenError("invalid signature")
        try:
            payload = json.loads(b64url_decode(payload_b64))
        except (ValueError, json.JSONDecodeError) as exc:
            raise InvalidTokenError("invalid payload") from exc
        if not isinstance(payload, dict):
            raise InvalidTokenError("invalid payload")
        current = now or datetime.now(tz=timezone.utc)
        exp = payload.get("exp")
        if exp is None or int(exp) < int(current.timestamp()):
            raise InvalidTokenError("token expired")
        if payload.get("iss") != self.issuer:
            raise InvalidTokenError("invalid issuer")
        return payload

    def _encode(self, header: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
        header_b64 = b64url_encode(
            json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        payload_b64 = b64url_encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        sig = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return f"{header_b64}.{payload_b64}.{b64url_encode(sig)}"
