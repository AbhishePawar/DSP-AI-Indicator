"""MFA gateway — TOTP / WebAuthn ports; login contracts stay additive-stable.

``DSP_AUTH_MFA=true`` swaps the default :class:`NullTotpAdapter` /
:class:`NullWebAuthnAdapter` for the real :class:`auth.mfa_totp.TotpAdapter`
and :class:`auth.mfa_webauthn.WebAuthnAdapter` implementations. When the
flag is unset (default ``false``) behaviour is byte-for-byte identical to
the original reserved-ports design: ``evaluate()`` always proceeds and the
``/auth/mfa/*`` routes report ``501``. This preserves backward compatibility
for existing deployments while making the feature complete once opted in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from auth.jwt import JwtService

__all__ = [
    "MfaChallenge",
    "MfaEvaluateResult",
    "MfaGateway",
    "MfaMethodPort",
    "NullTotpAdapter",
    "NullWebAuthnAdapter",
    "WebAuthnPort",
    "build_mfa_gateway",
    "mfa_flag_enabled",
]

_MFA_TOKEN_TTL_SECONDS = 300
_MFA_TOKEN_USE = "mfa_stepup"


def mfa_flag_enabled() -> bool:
    return (os.environ.get("DSP_AUTH_MFA") or "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@runtime_checkable
class MfaMethodPort(Protocol):
    def method_name(self) -> str: ...

    def is_available(self) -> bool: ...

    def is_enrolled(self, user_id: str) -> bool: ...

    def begin_enroll(self, user_id: str) -> dict[str, Any]: ...

    def confirm_enroll(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def begin_challenge(self, user_id: str) -> dict[str, Any]: ...

    def verify_challenge(self, user_id: str, payload: dict[str, Any]) -> bool: ...


@runtime_checkable
class WebAuthnPort(Protocol):
    """Passkeys / FIDO2 — real adapter when ``DSP_AUTH_MFA=true`` and the
    optional ``webauthn`` package is installed; :class:`NullWebAuthnAdapter`
    otherwise."""

    def begin_registration(self, user_id: str) -> dict[str, Any]: ...

    def complete_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]: ...

    def begin_authentication(self, user_id: str) -> dict[str, Any]: ...

    def complete_authentication(self, user_id: str, assertion: dict[str, Any]) -> bool: ...


@dataclass(frozen=True, slots=True)
class MfaChallenge:
    mfa_required: bool
    mfa_token: str | None = None
    methods: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mfa_required": self.mfa_required,
            "mfa_token": self.mfa_token,
            "methods": list(self.methods),
        }


@dataclass(frozen=True, slots=True)
class MfaEvaluateResult:
    """Result of post-primary MFA evaluation — additive fields only when required."""

    proceed: bool
    challenge: MfaChallenge | None = None

    def additive_fields(self) -> dict[str, Any]:
        if self.challenge is None or not self.challenge.mfa_required:
            return {}
        return self.challenge.to_dict()


class NullTotpAdapter:
    def method_name(self) -> str:
        return "totp"

    def is_available(self) -> bool:
        return False

    def is_enrolled(self, user_id: str) -> bool:
        _ = user_id
        return False

    def begin_enroll(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("TOTP enrollment not enabled (DSP_AUTH_MFA=false)")

    def confirm_enroll(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("TOTP enrollment not enabled")

    def begin_challenge(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("TOTP challenge not enabled")

    def verify_challenge(self, user_id: str, payload: dict[str, Any]) -> bool:
        _ = (user_id, payload)
        return False


class NullWebAuthnAdapter:
    def is_available(self) -> bool:
        return False

    def begin_registration(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled (DSP_AUTH_MFA=false)")

    def complete_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled")

    def begin_authentication(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled")

    def begin_discoverable_authentication(self, identifier: str | None = None) -> dict[str, Any]:
        _ = identifier
        raise NotImplementedError("WebAuthn not enabled")

    def complete_discoverable_authentication(self, assertion: dict[str, Any]) -> dict[str, Any]:
        _ = assertion
        raise NotImplementedError("WebAuthn not enabled")

    def complete_authentication(self, user_id: str, assertion: dict[str, Any]) -> bool:
        _ = (user_id, assertion)
        return False

    def list_credentials(self, user_id: str) -> list[dict[str, Any]]:
        _ = user_id
        return []


class MfaGateway:
    """
    Evaluate MFA after primary authentication.

    When disabled (default): always proceed — login response shape unchanged.
    When ``DSP_AUTH_MFA=true`` and a user is enrolled in TOTP and/or a
    passkey, the login response gains additive ``mfa_required`` /
    ``mfa_token`` / ``methods`` fields without breaking existing clients.
    Trusted devices (:class:`auth.devices.DeviceRegistry`) skip step-up.
    """

    def __init__(
        self,
        *,
        totp: MfaMethodPort | None = None,
        webauthn: WebAuthnPort | None = None,
        jwt: JwtService | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._totp = totp or NullTotpAdapter()
        self._webauthn = webauthn or NullWebAuthnAdapter()
        from auth.credential_boundary import resolve_auth_jwt_secret

        self._jwt = jwt or JwtService(
            resolve_auth_jwt_secret(),
            issuer="dsp-auth-mfa",
        )
        self._enabled = mfa_flag_enabled() if enabled is None else enabled

    def enabled(self) -> bool:
        return self._enabled

    @property
    def totp(self) -> MfaMethodPort:
        return self._totp

    @property
    def webauthn(self) -> WebAuthnPort:
        return self._webauthn

    def status(self) -> dict[str, Any]:
        webauthn_available = bool(self._enabled and self._webauthn.is_available())
        return {
            "enabled": self._enabled,
            "totp_available": bool(self._enabled and self._totp.is_available()),
            "webauthn_available": webauthn_available,
            "reserved_routes": [
                "/auth/mfa/enroll",
                "/auth/mfa/enable",
                "/auth/mfa/verify",
                "/auth/mfa/disable",
                "/auth/mfa/recovery-codes",
                "/auth/mfa/recovery-codes/regenerate",
                "/auth/mfa/totp/enroll",
                "/auth/mfa/totp/verify",
                "/auth/mfa/webauthn/register",
                "/auth/mfa/webauthn/authenticate",
            ],
            "message": None
            if self._enabled
            else "MFA disabled — enable with DSP_AUTH_MFA=true.",
        }

    def issue_mfa_token(self, user_id: str) -> str:
        """Short-lived, signed token identifying the pending step-up subject.

        Replaces a predictable ``f"mfa-pending:{user_id}"`` placeholder with
        a verifiable, time-boxed HMAC token via the existing
        :class:`auth.jwt.JwtService` (no new signing primitive introduced).
        """
        return self._jwt.issue(
            subject=user_id,
            expires_in=_MFA_TOKEN_TTL_SECONDS,
            token_use=_MFA_TOKEN_USE,
        )

    def resolve_mfa_token(self, mfa_token: str) -> str:
        """Return the ``user_id`` bound to a valid, unexpired ``mfa_token``."""
        from auth.exceptions import AuthenticationError, InvalidTokenError

        try:
            payload = self._jwt.decode(mfa_token)
        except InvalidTokenError as exc:
            raise AuthenticationError("Invalid or expired MFA challenge.") from exc
        if payload.get("token_use") != _MFA_TOKEN_USE:
            raise AuthenticationError("Invalid MFA challenge token.")
        subject = str(payload.get("sub") or "")
        if not subject:
            raise AuthenticationError("Invalid MFA challenge token.")
        return subject

    def evaluate(
        self,
        *,
        user_id: str,
        device_trusted: bool = False,
    ) -> MfaEvaluateResult:
        if not self._enabled:
            return MfaEvaluateResult(proceed=True)
        if device_trusted:
            return MfaEvaluateResult(proceed=True)
        enrolled: list[str] = []
        if self._totp.is_enrolled(user_id):
            enrolled.append("totp")
        if self._webauthn.list_credentials(user_id):
            enrolled.append("webauthn")
        if not enrolled:
            return MfaEvaluateResult(proceed=True)
        return MfaEvaluateResult(
            proceed=False,
            challenge=MfaChallenge(
                mfa_required=True,
                mfa_token=self.issue_mfa_token(user_id),
                methods=tuple(enrolled),
            ),
        )


def build_mfa_gateway(
    *,
    persistence: Any | None = None,
    users: Any | None = None,
    jwt: JwtService | None = None,
) -> MfaGateway:
    if not mfa_flag_enabled() or persistence is None:
        return MfaGateway(jwt=jwt)
    from auth.mfa_totp import TotpAdapter
    from auth.mfa_webauthn import WebAuthnAdapter

    totp = TotpAdapter(persistence)
    webauthn = WebAuthnAdapter(persistence, users) if users is not None else NullWebAuthnAdapter()
    return MfaGateway(totp=totp, webauthn=webauthn, jwt=jwt)
