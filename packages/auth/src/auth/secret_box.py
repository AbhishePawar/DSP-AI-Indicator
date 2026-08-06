"""Encryption-at-rest for sensitive MFA secret material (RFC 6238 seeds).

Uses ``cryptography.fernet.Fernet`` (AES-128-CBC + HMAC-SHA256, authenticated
encryption) — the same *optional* dependency already used for OIDC JWKS
signature verification (see :mod:`auth.oidc`). No new mandatory dependency is
introduced: when ``cryptography`` is not installed, secrets are written with
an explicit ``plain:`` tag rather than silently masquerading as encrypted, so
operators can always tell exactly what protection is active via
:func:`is_encrypted`.

Key management
--------------
- ``DSP_MFA_SECRET_KEY`` — a urlsafe-base64, 32-byte Fernet key
  (generate with ``Fernet.generate_key()``). Recommended for production —
  supports independent rotation from the JWT signing secret.
- When unset, a key is deterministically derived (SHA-256) from
  ``DSP_AUTH_JWT_SECRET`` so encryption works out of the box in development
  without any extra configuration.
- ``DSP_MFA_SECRET_KEY_PREVIOUS`` — optional comma-separated list of retired
  keys, tried for *decrypt-only* fallback. This lets an operator rotate
  ``DSP_MFA_SECRET_KEY`` without invalidating existing TOTP enrollments; new
  writes always use the current active key.

Ciphertext format is self-describing and forward-compatible:
``"enc:v1:<fernet-token>"`` for encrypted values, ``"plain:<value>"`` for the
graceful-degradation fallback. Legacy unprefixed values (written before this
module existed) are still readable by :func:`decrypt_secret`.
"""

from __future__ import annotations

import base64
import hashlib
import os

from auth.exceptions import AuthenticationError

__all__ = [
    "decrypt_secret",
    "encrypt_secret",
    "is_encrypted",
    "secret_encryption_available",
]

_ENC_PREFIX = "enc:v1:"
_PLAIN_PREFIX = "plain:"


def secret_encryption_available() -> bool:
    """Return ``True`` when the optional ``cryptography`` package is installed."""
    try:
        import cryptography.fernet  # noqa: F401
    except ImportError:
        return False
    return True


def _derive_key(passphrase: str) -> bytes:
    """Deterministically derive a valid 32-byte urlsafe-base64 Fernet key."""
    digest = hashlib.sha256(passphrase.strip().encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _active_key() -> bytes:
    configured = (os.environ.get("DSP_MFA_SECRET_KEY") or "").strip()
    if configured:
        return configured.encode("ascii")
    jwt_secret = os.environ.get("DSP_AUTH_JWT_SECRET") or "dsp-auth-dev-secret"
    return _derive_key(jwt_secret)


def _previous_keys() -> list[bytes]:
    raw = (os.environ.get("DSP_MFA_SECRET_KEY_PREVIOUS") or "").strip()
    if not raw:
        return []
    return [part.strip().encode("ascii") for part in raw.split(",") if part.strip()]


def encrypt_secret(plaintext: str) -> str:
    """Encrypt ``plaintext`` for at-rest storage.

    Falls back to an explicitly-tagged plaintext form when the optional
    ``cryptography`` dependency is unavailable — never raises.
    """
    if not secret_encryption_available():
        return f"{_PLAIN_PREFIX}{plaintext}"
    from cryptography.fernet import Fernet

    token = Fernet(_active_key()).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{_ENC_PREFIX}{token}"


def decrypt_secret(stored: str) -> str:
    """Reverse :func:`encrypt_secret`.

    Raises :class:`~auth.exceptions.AuthenticationError` when an encrypted
    value cannot be decrypted with any known key (tampering, corruption, or a
    rotated-away key with no ``DSP_MFA_SECRET_KEY_PREVIOUS`` entry).
    """
    if stored.startswith(_PLAIN_PREFIX):
        return stored[len(_PLAIN_PREFIX) :]
    if stored.startswith(_ENC_PREFIX):
        if not secret_encryption_available():
            raise AuthenticationError(
                "Cannot decrypt MFA secret: the 'cryptography' package is not installed."
            )
        from cryptography.fernet import Fernet, InvalidToken

        token = stored[len(_ENC_PREFIX) :].encode("ascii")
        for key in (_active_key(), *_previous_keys()):
            try:
                return Fernet(key).decrypt(token).decode("utf-8")
            except InvalidToken:
                continue
        raise AuthenticationError("MFA secret could not be decrypted (key mismatch or tampering).")
    # Legacy records persisted before this module existed: raw, unprefixed secret.
    return stored


def is_encrypted(stored: str) -> bool:
    """Return ``True`` when ``stored`` uses the authenticated-encryption format."""
    return stored.startswith(_ENC_PREFIX)
