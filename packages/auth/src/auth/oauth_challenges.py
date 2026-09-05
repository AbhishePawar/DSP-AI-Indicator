"""Durable OAuth PKCE challenge store (A008 metadata).

OAuth begin/callback on Cloud Run cannot rely on process-local RAM. Challenges
are persisted through the existing A008 ``StorageProviderPort`` (Postgres in
production, in-memory in development/tests).

Key derivation (domain-separated HKDF-SHA256 from ``DSP_AUTH_JWT_SECRET``)
------------------------------------------------------------------------
IKM  = UTF-8 bytes of :func:`auth.credential_boundary.resolve_auth_jwt_secret`
salt = ``b"dsp.a008.oauth.v1"``
PKCE AES-GCM key (32 bytes) = HKDF(IKM, salt, info=``b"dsp.oauth.pkce.v1"``)
State HMAC key (32 bytes)   = HKDF(IKM, salt, info=``b"dsp.oauth.state-id.v1"``)

The JWT secret is never used directly as an AES key. Rotating
``DSP_AUTH_JWT_SECRET`` also rotates these derived keys: in-flight challenges
(TTL 10 minutes) become undecryptable and must be restarted. Existing JWTs are
likewise invalidated by that rotation. No additional secret is introduced.

The browser/provider ``state`` value is never used as a database identifier.
``challenge_id`` is HMAC-SHA256(state, state-id key), hex-encoded.
The PKCE verifier is encrypted with AES-256-GCM (random 12-byte nonce) and
never hashed (Google requires the original verifier at token exchange).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from persistence.exceptions import DuplicateIdError
from auth.credential_boundary import resolve_auth_jwt_secret
from auth.exceptions import AuthenticationError, OAuthChallengeError

__all__ = [
    "OAUTH_CHALLENGE_TTL",
    "OAuthChallenge",
    "OAuthChallengeStore",
    "challenge_id_for_state",
]

logger = logging.getLogger(__name__)

OAUTH_CHALLENGE_TTL = timedelta(minutes=10)
_HKDF_SALT = b"dsp.a008.oauth.v1"
_HKDF_INFO_PKCE = b"dsp.oauth.pkce.v1"
_HKDF_INFO_STATE = b"dsp.oauth.state-id.v1"
_ENTITY_KIND = "metadata"
_PREFIX = "auth-oauth-"
_AAD = b"dsp.oauth.pkce.v1"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    padded = text + "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _hkdf_key(ikm: bytes, info: bytes, *, length: int = 32) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=_HKDF_SALT,
        info=info,
    ).derive(ikm)


def _ikm() -> bytes:
    return resolve_auth_jwt_secret().encode("utf-8")


def _pkce_key() -> bytes:
    return _hkdf_key(_ikm(), _HKDF_INFO_PKCE)


def _state_key() -> bytes:
    return _hkdf_key(_ikm(), _HKDF_INFO_STATE)


def challenge_id_for_state(state: str) -> str:
    """Return the HMAC-SHA256 identifier for a raw OAuth ``state`` value."""
    return hmac.new(_state_key(), state.encode("utf-8"), hashlib.sha256).hexdigest()


def _encrypt_verifier(verifier: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    ciphertext = AESGCM(_pkce_key()).encrypt(nonce, verifier.encode("ascii"), _AAD)
    return _b64url(nonce + ciphertext)


def _decrypt_verifier(packed_b64: str) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    try:
        packed = _b64url_decode(packed_b64)
        nonce, ciphertext = packed[:12], packed[12:]
        if len(nonce) != 12 or not ciphertext:
            raise ValueError("invalid ciphertext")
        plain = AESGCM(_pkce_key()).decrypt(nonce, ciphertext, _AAD)
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError(
            "Unable to complete sign-in. Start again from the login page."
        ) from exc
    return plain.decode("ascii")


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _entity_id(provider: str, challenge_id: str) -> str:
    return f"{_PREFIX}{provider.strip().lower()}-{challenge_id}"


@dataclass(frozen=True, slots=True)
class OAuthChallenge:
    challenge_id: str
    provider: str
    redirect_uri: str
    verifier: str
    nonce: str | None
    created_at: str
    expires_at: str


class OAuthChallengeStore:
    """Put/consume OAuth PKCE challenges on the shared A008 persistence service."""

    def __init__(self, persistence_service: Any | None = None) -> None:
        if persistence_service is None:
            from persistence import get_persistence_service

            persistence_service = get_persistence_service()
        self._persistence = persistence_service

    def put(
        self,
        *,
        provider: str,
        state: str,
        redirect_uri: str,
        verifier: str,
        nonce: str | None,
    ) -> str:
        created = _now()
        expires = created + OAUTH_CHALLENGE_TTL
        challenge_id = challenge_id_for_state(state)
        ciphertext_b64 = _encrypt_verifier(verifier)
        entity_id = _entity_id(provider, challenge_id)
        created_iso = created.isoformat()
        try:
            self._persistence.put(
                kind=_ENTITY_KIND,
                entity_id=entity_id,
                payload={
                    "auth_entity": "oauth_challenge",
                    "challenge_id": challenge_id,
                    "provider": provider.strip().upper(),
                    "redirect_uri": redirect_uri,
                    "verifier_ciphertext": ciphertext_b64,
                    "nonce": nonce,
                    "created_at": created_iso,
                    "expires_at": expires.isoformat(),
                    "consumed_at": None,
                },
                refs={"auth_entity": "oauth_challenge", "provider": provider.strip().upper()},
                created_at=created_iso,
                allow_update=False,
            )
        except DuplicateIdError as exc:
            raise AuthenticationError(
                "Unable to start sign-in. Start again from the login page."
            ) from exc
        logger.info("oauth challenge stored provider=%s", provider.strip().upper())
        return challenge_id

    def consume(self, *, provider: str, state: str, redirect_uri: str) -> OAuthChallenge:
        _ = redirect_uri
        if not state:
            raise OAuthChallengeError("unknown")
        challenge_id = challenge_id_for_state(state)
        entity_id = _entity_id(provider, challenge_id)
        now = _now()
        now_iso = now.isoformat()
        consumed = self._persistence.atomic_consume_unexpired(
            _ENTITY_KIND,
            entity_id,
            now_iso=now_iso,
            consumed_at=now_iso,
        )
        if consumed is None:
            self._reject_unconsumed(entity_id, now)
        assert consumed is not None
        payload = dict(consumed.get("payload") or {})
        verifier = _decrypt_verifier(str(payload.get("verifier_ciphertext") or ""))
        return OAuthChallenge(
            challenge_id=str(payload.get("challenge_id") or challenge_id),
            provider=str(payload.get("provider") or provider),
            redirect_uri=str(payload.get("redirect_uri") or ""),
            verifier=verifier,
            nonce=payload.get("nonce"),
            created_at=str(payload.get("created_at") or ""),
            expires_at=str(payload.get("expires_at") or ""),
        )

    def _reject_unconsumed(self, entity_id: str, now: datetime) -> None:
        row = self._persistence.get(_ENTITY_KIND, entity_id)
        if row is None:
            raise OAuthChallengeError("unknown")
        payload = dict(row.get("payload") or {})
        if payload.get("consumed_at"):
            raise OAuthChallengeError("replayed")
        expires = _parse_dt(payload.get("expires_at"))
        if expires is None or now >= expires:
            raise OAuthChallengeError("expired")
        raise OAuthChallengeError("replayed")
