"""Enterprise multi-provider auth models (production identity platform)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from auth.models import utc_now

__all__ = [
    "AuthProvider",
    "ENTERPRISE_ROLE_ALIASES",
    "PRODUCT_ROLES",
    "ProviderUiStatus",
    "AccessRequest",
    "LoginHistoryEntry",
    "OtpChallenge",
    "ProviderAccountLink",
    "MfaCredential",
    "enterprise_user_public_dict",
]


class AuthProvider(str, Enum):
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"
    FACEBOOK = "FACEBOOK"
    PHONE = "PHONE"
    USERNAME = "USERNAME"
    MAGIC_LINK = "MAGIC_LINK"
    PASSKEY = "PASSKEY"


class ProviderUiStatus(str, Enum):
    """Discovery contract for login UI."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"  # hide button — credentials missing
    COMING_SOON = "coming_soon"  # intentionally disabled — show Coming Soon


# Product-facing role names → A009 permission roles (never hardcode checks in UI).
PRODUCT_ROLES = (
    "super_admin",
    "administrator",
    "research_analyst",
    "portfolio_manager",
    "enterprise_client",
    "read_only",
)

ENTERPRISE_ROLE_ALIASES: dict[str, str] = {
    "super_admin": "super_admin",
    "super admin": "super_admin",
    "administrator": "administrator",
    "admin": "administrator",
    "research_analyst": "research_analyst",
    "research analyst": "research_analyst",
    "portfolio_manager": "portfolio_manager",
    "portfolio manager": "portfolio_manager",
    "viewer": "read_only",
    "read_only": "read_only",
    "read only": "read_only",
    "read only viewer": "read_only",
    "enterprise_client": "enterprise_client",
    "enterprise client": "enterprise_client",
}


@dataclass(frozen=True, slots=True)
class AccessRequest:
    request_id: str
    name: str
    email: str
    organization: str
    reason: str
    status: str  # pending | approved | rejected | invited | completed
    created_at: str
    updated_at: str
    invitation_token: str | None = None
    decided_by: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "name": self.name,
            "email": self.email,
            "organization": self.organization,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "invitation_token": self.invitation_token,
            "decided_by": self.decided_by,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class LoginHistoryEntry:
    entry_id: str
    user_id: str
    provider: str
    success: bool
    created_at: str
    ip_hint: str | None = None
    user_agent_hint: str | None = None
    detail: str | None = None
    device_label: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "provider": self.provider,
            "success": self.success,
            "created_at": self.created_at,
            "ip_hint": self.ip_hint,
            "user_agent_hint": self.user_agent_hint,
            "detail": self.detail,
            "device_label": self.device_label,
            "reason": self.reason or self.detail,
        }


@dataclass(frozen=True, slots=True)
class OtpChallenge:
    """One-time login challenge for mobile SMS or email delivery.

    ``mobile`` remains the historical field name for the destination when
    ``channel == "mobile"``. Email challenges store the address in
    ``destination`` and leave ``mobile`` empty. Public responses never
    include the plaintext OTP.
    """

    challenge_id: str
    mobile: str
    code_hash: str
    expires_at: str
    created_at: str
    attempts: int = 0
    consumed: bool = False
    resend_available_at: str | None = None
    channel: str = "mobile"  # mobile | email
    destination: str = ""

    def resolved_destination(self) -> str:
        return self.destination or self.mobile

    def to_public_dict(self) -> dict[str, Any]:
        dest = self.resolved_destination()
        out: dict[str, Any] = {
            "challenge_id": self.challenge_id,
            "channel": self.channel,
            "expires_at": self.expires_at,
            "resend_available_at": self.resend_available_at,
            "consumed": self.consumed,
        }
        if self.channel == "mobile":
            out["mobile"] = dest
        elif dest and "@" in dest:
            local, _, domain = dest.partition("@")
            masked_local = (local[:1] + "***") if local else "***"
            out["email_hint"] = f"{masked_local}@{domain}"
        return out


@dataclass(frozen=True, slots=True)
class ProviderAccountLink:
    provider: str
    provider_subject: str
    email: str | None
    linked_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_subject": self.provider_subject,
            "email": self.email,
            "linked_at": self.linked_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class MfaCredential:
    """Future-ready MFA credential row (schema now; runtime optional)."""

    user_id: str
    method: str  # totp | webauthn
    credential_ref: str
    created_at: str
    enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "method": self.method,
            "credential_ref": self.credential_ref,
            "created_at": self.created_at,
            "enabled": self.enabled,
        }


def _thaw(value: Any) -> Any:
    """Recursively convert immutable ``MappingProxyType``/tuple wrappers
    (used internally for `AuthUser.metadata`, see `auth.models.freeze_mapping`)
    back into plain ``dict``/``list`` so the result is safely
    JSON-serializable by a bare `JSONResponse` (which — unlike FastAPI's
    default response handling — does not run values through
    `jsonable_encoder`).
    """
    if isinstance(value, Mapping):
        return {str(k): _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value


def enterprise_user_public_dict(user: Any) -> dict[str, Any]:
    """Normalize AuthUser (+ metadata) into the enterprise user shape."""
    meta = _thaw(dict(getattr(user, "metadata", None) or {}))
    if isinstance(user, Mapping):
        base = dict(user)
        meta = _thaw(dict(base.get("metadata") or {}))
        roles = list(base.get("roles") or meta.get("roles") or [])
        raw_email = str(base.get("email") or "")
        public_email = "" if _public_email_is_synthetic(raw_email, meta) else raw_email
        return {
            "id": base.get("user_id") or base.get("id"),
            "user_id": base.get("user_id") or base.get("id"),
            "name": base.get("display_name") or base.get("name") or "",
            "username": base.get("username") or "",
            "email": public_email,
            "mobile": meta.get("mobile") or base.get("mobile"),
            "provider": meta.get("provider") or AuthProvider.USERNAME.value,
            "avatar": meta.get("avatar"),
            "role": (roles or [None])[0],
            "roles": roles,
            "status": base.get("status") or "active",
            "emailVerified": bool(meta.get("email_verified") or base.get("email_verified")),
            "phoneVerified": bool(meta.get("phone_verified") or base.get("phone_verified")),
            "failedLoginCount": int(meta.get("failed_login_count") or 0),
            "lockedUntil": meta.get("locked_until"),
            "createdAt": base.get("created_at"),
            "updatedAt": base.get("updated_at"),
            "lastLogin": base.get("last_login"),
            "linkedProviders": list(meta.get("linked_providers") or []),
            "metadata": meta,
        }
    roles = list(getattr(user, "roles", ()) or ())
    raw_email = str(getattr(user, "email", "") or "")
    public_email = "" if _public_email_is_synthetic(raw_email, meta) else raw_email
    return {
        "id": user.user_id,
        "user_id": user.user_id,
        "name": user.display_name,
        "username": user.username,
        "email": public_email,
        "mobile": meta.get("mobile"),
        "provider": meta.get("provider") or AuthProvider.USERNAME.value,
        "avatar": meta.get("avatar"),
        "role": roles[0] if roles else None,
        "roles": roles,
        "status": user.status,
        "emailVerified": bool(meta.get("email_verified")),
        "phoneVerified": bool(meta.get("phone_verified")),
        "failedLoginCount": int(meta.get("failed_login_count") or 0),
        "lockedUntil": meta.get("locked_until"),
        "createdAt": user.created_at,
        "updatedAt": user.updated_at,
        "lastLogin": user.last_login,
        "linkedProviders": list(meta.get("linked_providers") or []),
        "metadata": dict(meta),
        "asOf": utc_now().isoformat(),
    }


def _public_email_is_synthetic(email: str, meta: Mapping[str, Any]) -> bool:
    if bool(meta.get("synthetic_email")):
        return True
    lowered = (email or "").strip().lower()
    return lowered.endswith("@phone.dspai.local") or lowered.endswith(
        "@username.dspai.local"
    )
