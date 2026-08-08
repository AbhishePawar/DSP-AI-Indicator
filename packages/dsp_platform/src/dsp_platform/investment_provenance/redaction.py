"""Secret redaction for investment provenance records (P1-06)."""

from __future__ import annotations

from typing import Any

__all__ = ["redact_secrets", "SECRET_KEY_FRAGMENTS"]

SECRET_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "bearer",
    "password",
    "passwd",
    "secret",
    "token",
    "jwt",
    "private_key",
    "access_key",
    "client_secret",
    "credential",
    "cookie",
)


def redact_secrets(value: Any) -> Any:
    """Recursively redact credential-like keys. Never persist secrets."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_l = str(key).lower()
            if any(frag in key_l for frag in SECRET_KEY_FRAGMENTS):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = redact_secrets(item)
        return out
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value
