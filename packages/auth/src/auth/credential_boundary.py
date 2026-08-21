"""Auth vs investment credential namespaces (configuration boundary).

AUTH DOMAIN — user login / sessions / email / Google OAuth.
These may be read by ``auth`` and auth API routers. They must never be
satisfied by investment credentials.

    DSP_AUTH_JWT_SECRET
    DSP_AUTH_MAGIC_LINK
    DSP_RESEND_API_KEY
    DSP_RESEND_FROM_ADDRESS   (Resend From; not SMTP)
    DSP_GOOGLE_CLIENT_ID
    DSP_GOOGLE_CLIENT_SECRET

INVESTMENT DOMAIN — market data / Upstox. Owned by ``data_engine`` /
composition. Auth boot, login, OTP, magic-link, Google OAuth, JWT/session,
and ``/health/ready`` must not require these.

    DSP_INVESTMENT_DATA_PROVIDER
    DSP_UPSTOX_ANALYTICS_TOKEN
    DSP_UPSTOX_CLIENT_SECRET

Auth code must not call investment factories
(``build_default_quote_adapter_from_env``, ``require_upstox_analytics_token``,
``assert_production_investment_connectors_configured``).
"""

from __future__ import annotations

import os

__all__ = [
    "AUTH_JWT_SECRET_ENV",
    "AUTH_MAGIC_LINK_ENV",
    "GOOGLE_CLIENT_ID_ENV",
    "GOOGLE_CLIENT_SECRET_ENV",
    "LEGACY_JWT_SECRET_ENV",
    "RESEND_API_KEY_ENV",
    "RESEND_FROM_ADDRESS_ENV",
    "resolve_auth_jwt_secret",
]

AUTH_JWT_SECRET_ENV = "DSP_AUTH_JWT_SECRET"
AUTH_MAGIC_LINK_ENV = "DSP_AUTH_MAGIC_LINK"
RESEND_API_KEY_ENV = "DSP_RESEND_API_KEY"
RESEND_FROM_ADDRESS_ENV = "DSP_RESEND_FROM_ADDRESS"
GOOGLE_CLIENT_ID_ENV = "DSP_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET_ENV = "DSP_GOOGLE_CLIENT_SECRET"

# Legacy API/security seam — prefer AUTH_JWT_SECRET_ENV; never investment vars.
LEGACY_JWT_SECRET_ENV = "DSP_JWT_SECRET"

_DEFAULT_DEV_SECRETS = frozenset(
    {"", "dsp-auth-dev-secret", "dev-only-change-me"}
)


def resolve_auth_jwt_secret(
    environ: dict[str, str] | None = None,
) -> str:
    """Return the auth-domain JWT secret (never investment credentials)."""
    env = environ if environ is not None else os.environ
    primary = str(env.get(AUTH_JWT_SECRET_ENV) or "").strip()
    if primary:
        return primary
    legacy = str(env.get(LEGACY_JWT_SECRET_ENV) or "").strip()
    if legacy:
        return legacy
    return "dsp-auth-dev-secret"


def auth_jwt_secret_is_default(secret: str) -> bool:
    return secret.strip() in _DEFAULT_DEV_SECRETS
