"""MFA gateway — TOTP / WebAuthn ports reserved; login contracts stay additive-stable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "MfaChallenge",
    "MfaEvaluateResult",
    "MfaGateway",
    "MfaMethodPort",
    "NullTotpAdapter",
    "NullWebAuthnAdapter",
    "WebAuthnPort",
    "build_mfa_gateway",
]


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
    """Passkeys / FIDO2 — architecture only until DSP_AUTH_MFA=true."""

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
    def begin_registration(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled (DSP_AUTH_MFA=false)")

    def complete_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled")

    def begin_authentication(self, user_id: str) -> dict[str, Any]:
        raise NotImplementedError("WebAuthn not enabled")

    def complete_authentication(self, user_id: str, assertion: dict[str, Any]) -> bool:
        _ = (user_id, assertion)
        return False


class MfaGateway:
    """
    Evaluate MFA after primary authentication.

    Today (DSP_AUTH_MFA=false): always proceed — login response shape unchanged.
    Later: return additive ``mfa_required`` / ``mfa_token`` without breaking clients.
    Trusted devices may skip step-up when MFA is enabled.
    """

    def __init__(
        self,
        *,
        totp: MfaMethodPort | None = None,
        webauthn: WebAuthnPort | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._totp = totp or NullTotpAdapter()
        self._webauthn = webauthn or NullWebAuthnAdapter()
        if enabled is None:
            enabled = (os.environ.get("DSP_AUTH_MFA") or "false").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self._enabled = enabled

    def enabled(self) -> bool:
        return self._enabled

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "totp_available": self._totp.is_available(),
            "webauthn_available": False,
            "reserved_routes": [
                "/auth/mfa/totp/enroll",
                "/auth/mfa/totp/verify",
                "/auth/mfa/webauthn/register",
                "/auth/mfa/webauthn/authenticate",
            ],
            "message": None
            if self._enabled
            else "MFA ports reserved — enable with DSP_AUTH_MFA=true when adapters are configured.",
        }

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
        if not enrolled:
            return MfaEvaluateResult(proceed=True)
        # Future: issue short-lived mfa_token; clients ignore unknown fields today.
        return MfaEvaluateResult(
            proceed=False,
            challenge=MfaChallenge(
                mfa_required=True,
                mfa_token=f"mfa-pending:{user_id}",
                methods=tuple(enrolled),
            ),
        )


def build_mfa_gateway() -> MfaGateway:
    return MfaGateway()
