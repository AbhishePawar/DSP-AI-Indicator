"""Password hashing (EPIC-A009) — stdlib PBKDF2 only."""

from __future__ import annotations

import hashlib
import hmac
import secrets

__all__ = ["hash_password", "verify_password"]

_ITERATIONS = 120_000
_ALGO = "sha256"


def hash_password(password: str, *, salt: str | None = None) -> str:
    """Return ``pbkdf2$iterations$salt$digest`` — never store plaintext."""
    if not password:
        raise ValueError("password is required")
    salt_hex = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        _ALGO,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        _ITERATIONS,
    ).hex()
    return f"pbkdf2${_ITERATIONS}${salt_hex}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iters_s, salt_hex, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    try:
        iterations = int(iters_s)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        _ALGO,
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        iterations,
    ).hex()
    return hmac.compare_digest(candidate, digest)
