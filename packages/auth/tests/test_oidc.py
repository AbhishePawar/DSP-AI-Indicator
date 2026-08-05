"""OIDC ID-token JWKS/issuer/audience/nonce verification tests."""

from __future__ import annotations

import base64
import json
import time

import pytest

cryptography = pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15  # noqa: E402

from auth import oidc  # noqa: E402


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _int_to_b64url(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return _b64url(value.to_bytes(length, "big"))


class _KeyPair:
    def __init__(self, kid: str = "test-kid") -> None:
        self.kid = kid
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def jwks(self) -> dict:
        numbers = self.public_key.public_numbers()
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "kid": self.kid,
                    "use": "sig",
                    "alg": "RS256",
                    "n": _int_to_b64url(numbers.n),
                    "e": _int_to_b64url(numbers.e),
                }
            ]
        }

    def sign_token(self, claims: dict) -> str:
        header = {"alg": "RS256", "typ": "JWT", "kid": self.kid}
        header_b64 = _b64url(json.dumps(header).encode("utf-8"))
        payload_b64 = _b64url(json.dumps(claims).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = self.private_key.sign(signing_input, PKCS1v15(), hashes.SHA256())
        return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


@pytest.fixture(autouse=True)
def _clear_jwks_cache():
    oidc._JWKS_CACHE.clear()
    yield
    oidc._JWKS_CACHE.clear()


def _base_claims(**overrides) -> dict:
    now = time.time()
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "client-123",
        "sub": "user-abc",
        "email": "user@example.com",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return claims


def _patch_jwks(monkeypatch, jwks_uri: str, jwks: dict) -> None:
    monkeypatch.setattr(oidc, "_fetch_jwks", lambda uri: jwks)


def test_verify_id_token_success(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(_base_claims(nonce="abc123"))

    claims = oidc.verify_id_token(
        token,
        jwks_uri="https://example.test/jwks",
        issuer="https://accounts.google.com",
        audience="client-123",
        nonce="abc123",
    )
    assert claims["sub"] == "user-abc"
    assert claims["email"] == "user@example.com"


def test_verify_id_token_rejects_bad_signature(monkeypatch):
    kp = _KeyPair()
    other_kp = _KeyPair(kid="test-kid")
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    # Sign with a *different* key than the one published in JWKS.
    token = other_kp.sign_token(_base_claims())

    with pytest.raises(ValueError, match="signature"):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )


def test_verify_id_token_rejects_wrong_audience(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(_base_claims(aud="someone-else"))

    with pytest.raises(ValueError, match="audience"):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )


def test_verify_id_token_rejects_wrong_issuer(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(_base_claims(iss="https://evil.example"))

    with pytest.raises(ValueError, match="issuer"):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )


def test_verify_id_token_rejects_nonce_mismatch(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(_base_claims(nonce="expected-nonce"))

    with pytest.raises(ValueError, match="nonce"):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
            nonce="different-nonce",
        )


def test_verify_id_token_rejects_expired(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(_base_claims(exp=time.time() - 600))

    with pytest.raises(ValueError, match="expired"):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )


def test_verify_id_token_supports_multi_tenant_issuer_wildcard(monkeypatch):
    kp = _KeyPair()
    _patch_jwks(monkeypatch, "https://example.test/jwks", kp.jwks())
    token = kp.sign_token(
        _base_claims(iss="https://login.microsoftonline.com/72f9-tenant/v2.0")
    )

    claims = oidc.verify_id_token(
        token,
        jwks_uri="https://example.test/jwks",
        issuer="https://login.microsoftonline.com/*/v2.0",
        audience="client-123",
    )
    assert claims["sub"] == "user-abc"


def test_verify_id_token_unavailable_when_cryptography_missing(monkeypatch):
    monkeypatch.setattr(oidc, "cryptography_available", lambda: False)
    with pytest.raises(oidc.OidcVerificationUnavailable):
        oidc.verify_id_token(
            "a.b.c",
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )


def test_verify_id_token_unavailable_on_unsupported_key_type(monkeypatch):
    jwks = {"keys": [{"kty": "EC", "kid": "test-kid", "crv": "P-256"}]}
    _patch_jwks(monkeypatch, "https://example.test/jwks", jwks)
    kp = _KeyPair()
    token = kp.sign_token(_base_claims())

    with pytest.raises(oidc.OidcVerificationUnavailable):
        oidc.verify_id_token(
            token,
            jwks_uri="https://example.test/jwks",
            issuer="https://accounts.google.com",
            audience="client-123",
        )
