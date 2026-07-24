"""Minimal HMAC-SHA256 JWT manager (stdlib only)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from security_platform.security.exceptions import TokenError
from security_platform.security.roles import Role, assert_role

__all__ = ["JWTManager", "TokenClaims"]


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Validated JWT claims used by the security platform."""

    subject: str
    role: Role
    issued_at: int
    expires_at: int
    token_id: str | None = None
    username: str | None = None
    extra: dict[str, Any] | None = None

    @property
    def expired(self) -> bool:
        return int(time.time()) >= self.expires_at


class JWTManager:
    """Issue / verify HS256 JWTs — OAuth2-ready claim shape.

    Does not call external IdPs. Adapters may validate opaque tokens via
    :class:`~security_platform.security.auth.OAuth2TokenValidator`.
    """

    def __init__(
        self,
        *,
        secret: str,
        issuer: str = "dsp-security",
        audience: str = "dsp-api",
        default_ttl_seconds: int = 3600,
    ) -> None:
        if not secret.strip():
            msg = "JWT secret must not be empty"
            raise TokenError(msg)
        if default_ttl_seconds <= 0:
            msg = "default_ttl_seconds must be positive"
            raise TokenError(msg)
        self._secret = secret.encode("utf-8")
        self._issuer = issuer
        self._audience = audience
        self._ttl = default_ttl_seconds

    @property
    def issuer(self) -> str:
        return self._issuer

    @property
    def audience(self) -> str:
        return self._audience

    def issue(
        self,
        *,
        subject: str,
        role: Role | str,
        username: str | None = None,
        ttl_seconds: int | None = None,
        token_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Return a signed JWT string."""
        if not subject.strip():
            msg = "subject must not be empty"
            raise TokenError(msg)
        now = int(time.time())
        ttl = self._ttl if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            msg = "ttl_seconds must be positive"
            raise TokenError(msg)
        resolved = assert_role(role)
        payload: dict[str, Any] = {
            "sub": subject.strip(),
            "role": resolved.value,
            "iat": now,
            "exp": now + ttl,
            "iss": self._issuer,
            "aud": self._audience,
        }
        if username:
            payload["username"] = username
        if token_id:
            payload["jti"] = token_id
        if extra:
            payload["extra"] = extra
        return self._encode(payload)

    def verify(self, token: str) -> TokenClaims:
        """Verify signature + exp/iss/aud and return claims."""
        try:
            header_b64, payload_b64, signature_b64 = token.strip().split(".")
        except ValueError as exc:
            msg = "malformed JWT"
            raise TokenError(msg) from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected, actual):
            msg = "invalid JWT signature"
            raise TokenError(msg)

        try:
            header = json.loads(_b64url_decode(header_b64))
            payload = json.loads(_b64url_decode(payload_b64))
        except (json.JSONDecodeError, ValueError) as exc:
            msg = "invalid JWT encoding"
            raise TokenError(msg) from exc

        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            msg = "unsupported JWT header"
            raise TokenError(msg)

        if payload.get("iss") != self._issuer:
            msg = "invalid JWT issuer"
            raise TokenError(msg)
        aud = payload.get("aud")
        if aud != self._audience:
            msg = "invalid JWT audience"
            raise TokenError(msg)

        exp = int(payload.get("exp", 0))
        iat = int(payload.get("iat", 0))
        if int(time.time()) >= exp:
            msg = "JWT expired"
            raise TokenError(msg)

        subject = str(payload.get("sub", "")).strip()
        if not subject:
            msg = "JWT missing subject"
            raise TokenError(msg)

        return TokenClaims(
            subject=subject,
            role=assert_role(str(payload.get("role", ""))),
            issued_at=iat,
            expires_at=exp,
            token_id=str(payload["jti"]) if payload.get("jti") else None,
            username=str(payload["username"]) if payload.get("username") else None,
            extra=payload.get("extra") if isinstance(payload.get("extra"), dict) else None,
        )

    def _encode(self, payload: dict[str, Any]) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = _b64url_encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
        )
        payload_b64 = _b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(self._secret, signing_input, hashlib.sha256).digest()
        return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"
