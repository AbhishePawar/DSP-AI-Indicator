"""OIDC ID-token verification — JWKS (RS256) signature + issuer/audience/nonce.

This is additive, defense-in-depth hardening on top of the OAuth flow that
already exists in :mod:`auth.oauth_providers` (authorization-code + PKCE +
a live ``userinfo``/Graph ``/me`` call using the freshly-exchanged access
token). That live profile call is itself a strong validity signal — an
attacker without a genuine access token cannot obtain it — so ID-token
verification here is treated as an *additional* cross-check rather than the
sole trust anchor:

* When the token endpoint returns an ``id_token`` **and** the optional
  ``cryptography`` package is installed, the signature is verified against
  the provider's live JWKS, plus issuer / audience / expiry / nonce claims.
  A verified token's ``sub``/``email`` must match the ``userinfo`` profile
  or the login is rejected (catches token-substitution / mix-up attacks).
* When ``id_token`` is absent or ``cryptography`` is unavailable, the
  existing (already-working) userinfo-based flow proceeds unchanged — no
  regression, no new hard dependency, full backward compatibility.

Only RS256/RSA keys are handled (what Google and Microsoft Entra ID issue
today for ID tokens). An unsupported ``kty``/``alg`` is treated the same as
"verification unavailable", not as a failure, to fail open on the additive
check while the primary (userinfo-based) trust path still applies.
"""

from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.request
from threading import Lock
from typing import Any

__all__ = [
    "OidcVerificationUnavailable",
    "cryptography_available",
    "verify_id_token",
]

_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_CACHE_TTL = 3600
_JWKS_LOCK = Lock()


class OidcVerificationUnavailable(Exception):
    """Raised internally when signature verification cannot be attempted
    (missing dependency, unsupported key type, or JWKS fetch failure).
    Callers should treat this as "skip the additive check", not "reject".
    """


def cryptography_available() -> bool:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return False
    return True


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _b64url_decode_uint(value: str) -> int:
    return int.from_bytes(_b64url_decode(value), "big")


def _fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    now = time.time()
    with _JWKS_LOCK:
        cached = _JWKS_CACHE.get(jwks_uri)
        if cached and now - cached[0] < _JWKS_CACHE_TTL:
            return cached[1]
    try:
        req = urllib.request.Request(jwks_uri, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise OidcVerificationUnavailable(f"JWKS fetch failed: {exc}") from exc
    with _JWKS_LOCK:
        _JWKS_CACHE[jwks_uri] = (now, data)
    return data


def _issuer_matches(token_iss: str, pattern: str) -> bool:
    """Match an issuer against an expected value, allowing ``*`` to stand
    in for exactly one path segment (used for multi-tenant Microsoft Entra
    ID issuers, e.g. ``https://login.microsoftonline.com/*/v2.0``).
    """
    if "*" not in pattern:
        return token_iss == pattern
    regex = "^" + "".join(
        re.escape(part) if part != "*" else "[^/]+" for part in re.split(r"(\*)", pattern)
    ) + "$"
    return re.match(regex, token_iss) is not None


def _rsa_public_key(jwk: dict[str, Any]) -> Any:
    from cryptography.hazmat.primitives.asymmetric import rsa

    if jwk.get("kty") != "RSA":
        raise OidcVerificationUnavailable(f"unsupported key type {jwk.get('kty')!r}")
    n = _b64url_decode_uint(jwk["n"])
    e = _b64url_decode_uint(jwk["e"])
    return rsa.RSAPublicNumbers(e, n).public_key()


def verify_id_token(
    id_token: str,
    *,
    jwks_uri: str,
    issuer: str | tuple[str, ...],
    audience: str,
    nonce: str | None = None,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    """Verify an RS256 OIDC ID token's signature and standard claims.

    Returns the decoded claims dict on success. Raises
    :class:`OidcVerificationUnavailable` when verification cannot be
    attempted (caller should treat as "skip"), or ``ValueError`` when the
    token is cryptographically present but fails a real check (caller
    should treat as a hard rejection).
    """
    if not cryptography_available():
        raise OidcVerificationUnavailable("cryptography package not installed")
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15

    try:
        header_b64, payload_b64, sig_b64 = id_token.split(".")
    except ValueError as exc:
        raise ValueError("malformed id_token") from exc
    header = json.loads(_b64url_decode(header_b64))
    payload = json.loads(_b64url_decode(payload_b64))
    if header.get("alg") != "RS256":
        raise OidcVerificationUnavailable(f"unsupported alg {header.get('alg')!r}")

    jwks = _fetch_jwks(jwks_uri)
    kid = header.get("kid")
    jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if jwk is None:
        raise OidcVerificationUnavailable("signing key not found in JWKS")
    public_key = _rsa_public_key(jwk)

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = _b64url_decode(sig_b64)
    try:
        public_key.verify(signature, signing_input, PKCS1v15(), hashes.SHA256())
    except InvalidSignature as exc:
        raise ValueError("id_token signature verification failed") from exc

    now = time.time()
    exp = payload.get("exp")
    if exp is None or now > float(exp) + leeway_seconds:
        raise ValueError("id_token expired")
    iat = payload.get("iat")
    if iat is not None and float(iat) > now + leeway_seconds:
        raise ValueError("id_token issued in the future")

    issuers = (issuer,) if isinstance(issuer, str) else tuple(issuer)
    token_iss = str(payload.get("iss") or "")
    if not any(_issuer_matches(token_iss, i) for i in issuers):
        raise ValueError(f"unexpected issuer {token_iss!r}")

    aud = payload.get("aud")
    aud_values = aud if isinstance(aud, list) else [aud]
    if audience not in aud_values:
        raise ValueError("audience mismatch")

    if nonce is not None and payload.get("nonce") != nonce:
        raise ValueError("nonce mismatch")

    return dict(payload)
