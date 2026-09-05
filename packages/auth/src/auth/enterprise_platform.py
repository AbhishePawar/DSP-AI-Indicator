"""Enterprise multi-provider authentication platform — extends A009 AuthService."""

from __future__ import annotations

import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from auth.audit import AuditLogger
from auth.devices import DeviceRegistry
from auth.credential_boundary import AUTH_MAGIC_LINK_ENV
from auth.email_delivery import EmailProviderPort, build_email_provider
from auth.email_templates import (
    render_email_verification_email,
    render_invitation_email,
    render_magic_link_email,
    render_password_reset_email,
)
from auth.enterprise_models import (
    ENTERPRISE_ROLE_ALIASES,
    PRODUCT_ROLES,
    AccessRequest,
    AuthProvider,
    LoginHistoryEntry,
    ProviderUiStatus,
    enterprise_user_public_dict,
)
from auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateUserError,
    OAuthChallengeError,
    ValidationError,
)
from auth.hashing import hash_password, needs_rehash, verify_password
from auth.mfa import MfaGateway, build_mfa_gateway
from auth.models import AuthUser, freeze_mapping, utc_now
from auth.oauth_providers import (
    OAuthProfile,
    OAuthProviderRegistry,
    build_oauth_registry,
    stable_username_from_email,
)
from auth.otp import (
    OtpService,
    normalize_india_mobile,
    try_normalize_india_mobile,
)
from auth.service import AuthService, get_auth_service
from auth.single_use_tokens import SingleUseTokenError, SingleUseTokenService
from auth.sms import build_sms_provider
from auth.validation import assert_email, assert_username

__all__ = [
    "EnterpriseAuthPlatform",
    "get_enterprise_auth_platform",
    "reset_enterprise_auth_platform_for_tests",
    "password_strength",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ACCESS_PREFIX = "auth-access-"
_HISTORY_PREFIX = "auth-login-hist-"
_PHONE_EMAIL_SUFFIX = "@phone.dspai.local"
_USERNAME_EMAIL_SUFFIX = "@username.dspai.local"


def _is_synthetic_mailbox(email: str | None) -> bool:
    mail = (email or "").strip().lower()
    return mail.endswith(_PHONE_EMAIL_SUFFIX) or mail.endswith(_USERNAME_EMAIL_SUFFIX)


def password_strength(password: str) -> dict[str, Any]:
    score = 0
    checks = {
        "min_length": len(password) >= 12,
        "upper": any(c.isupper() for c in password),
        "lower": any(c.islower() for c in password),
        "digit": any(c.isdigit() for c in password),
        "special": any(not c.isalnum() for c in password),
    }
    score = sum(1 for ok in checks.values() if ok)
    label = ("very_weak", "weak", "fair", "good", "strong", "excellent")[score]
    return {"score": score, "max": 5, "label": label, "checks": checks}


def _normalize_role(role: str | None) -> str:
    if not role:
        return "read_only"
    key = role.strip().lower()
    mapped = ENTERPRISE_ROLE_ALIASES.get(key)
    if mapped is None:
        from auth.models import BUILTIN_ROLES

        if key in BUILTIN_ROLES:
            return key
        raise ValidationError(f"unknown role {role!r}")
    return mapped


class EnterpriseAuthPlatform:
    """Production enterprise auth façade over A009 + OAuth/OTP/request-access."""

    def __init__(
        self,
        auth: AuthService,
        *,
        oauth: OAuthProviderRegistry | None = None,
        otp: OtpService | None = None,
        devices: DeviceRegistry | None = None,
        mfa: MfaGateway | None = None,
        email: EmailProviderPort | None = None,
        audit: AuditLogger | None = None,
        tokens: SingleUseTokenService | None = None,
    ) -> None:
        self.auth = auth
        self.oauth = oauth or build_oauth_registry()
        self.email = email or build_email_provider()
        self.otp = otp or OtpService(build_sms_provider())
        self.devices = devices or DeviceRegistry(auth.persistence)
        self.mfa = mfa or build_mfa_gateway(
            persistence=auth.persistence, users=auth.users, jwt=auth.jwt
        )
        self.audit = audit or AuditLogger(auth.persistence)
        # Single shared implementation for every one-time-link auth flow
        # (email verification, password reset, magic link, invitations, and
        # any future one-time flow) — see auth.single_use_tokens.
        self.tokens = tokens or SingleUseTokenService(auth.persistence, audit=self.audit)
        # AuthenticationService (A009) is audit-agnostic by design (lower
        # layer, no dependency on this platform's AuditLogger). Wiring it
        # here means refresh-token rotation/reuse events raised from
        # ``AuthenticationService.refresh`` — including via the pre-existing
        # ``/auth/rbac/refresh`` endpoint, which calls into the very same
        # shared AuthService singleton — land in this platform's audit
        # trail with zero duplicate logic or storage.
        self.auth.authentication.audit = self.audit
        self._rate: dict[str, list[datetime]] = {}
        self._lock = Lock()
        self._lockout_threshold = int(os.environ.get("DSP_AUTH_LOCKOUT_THRESHOLD") or "5")
        self._lockout_seconds = int(os.environ.get("DSP_AUTH_LOCKOUT_SECONDS") or "900")
        self.ensure_product_roles()
        self.ensure_dev_admin_seed()

    # --- schema / status -------------------------------------------------

    def schema(self) -> dict[str, Any]:
        base = self.auth.schema()
        return {
            **base,
            "enterprise_auth": True,
            "providers": [p.value for p in AuthProvider],
            "product_roles": list(PRODUCT_ROLES),
            "oauth": self.oauth.status(),
            "sms": self.otp.sms_status(),
            "features": {
                "email_password": True,
                "username_password": True,
                "mobile_password": True,
                "google_oauth": True,
                "microsoft_oauth": True,
                "facebook_oauth": True,
                "mobile_otp": True,
                "email_otp": False,
                "unified_otp": False,
                "magic_link": True,
                "request_access": True,
                "email_verification": True,
                "username_register": True,
                "mobile_register": True,
                "combined_register": True,
                "password_reset": True,
                "password_reset_otp": True,
                "remember_me": True,
                "login_history": True,
                "device_tracking": True,
                "mfa_totp": self.mfa.enabled() and self.mfa.totp.is_available(),
                "mfa_webauthn": self.mfa.enabled() and self.mfa.webauthn.is_available(),
            },
        }

    def provider_status(self) -> dict[str, Any]:
        """Discovery contract: available | unavailable | coming_soon."""
        otp_flag = (os.environ.get("DSP_AUTH_PROVIDER_OTP") or "auto").strip().lower()
        sms = self.otp.sms_status()
        if otp_flag in {"disabled", "coming_soon", "off", "false", "0"}:
            otp_status = ProviderUiStatus.COMING_SOON.value
            otp_available = False
            otp_message = "Mobile OTP intentionally disabled — Coming Soon."
        elif not sms.get("available"):
            otp_status = ProviderUiStatus.UNAVAILABLE.value
            otp_available = False
            otp_message = "Mobile OTP unavailable — SMS provider credentials are not configured."
        else:
            otp_status = ProviderUiStatus.AVAILABLE.value
            otp_available = True
            otp_message = None
        providers = list(self.oauth.status())
        providers.append(
            {
                "id": "otp",
                "provider": "PHONE",
                "status": otp_status,
                "available": otp_available,
                "message": otp_message,
            }
        )
        providers.append(
            {
                "id": "email",
                "provider": "EMAIL",
                "status": ProviderUiStatus.AVAILABLE.value,
                "available": True,
                "message": None,
            }
        )
        magic_enabled = (os.environ.get(AUTH_MAGIC_LINK_ENV) or "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return {
            "providers": providers,
            "oauth": [p for p in providers if p["provider"] in {"GOOGLE", "MICROSOFT", "FACEBOOK"}],
            "sms": {**sms, "status": otp_status, "available": otp_available, "message": otp_message},
            "magic_link": {
                "available": magic_enabled,
                "status": (
                    ProviderUiStatus.AVAILABLE.value
                    if magic_enabled
                    else ProviderUiStatus.COMING_SOON.value
                ),
                "message": None
                if magic_enabled
                else "Magic link intentionally disabled — Coming Soon.",
            },
            "mfa": self.mfa.status(),
            # Dedicated, additive discovery block for primary/passwordless
            # Passkey sign-in (`/auth/passkey/*`). Computed from the exact
            # same gate as `mfa.webauthn_available` — one shared WebAuthn
            # adapter/credential store backs both entry points — so there is
            # no separate `DSP_AUTH_PASSKEY` flag to keep in sync.
            "passkey": {
                "available": bool(self.mfa.enabled() and self.mfa.webauthn.is_available()),
                "message": None
                if self.mfa.enabled()
                else "Passkey sign-in disabled — enable with DSP_AUTH_MFA=true.",
            },
        }

    def ensure_product_roles(self) -> None:
        from auth.models import PERMISSIONS

        if self.auth.roles.get("super_admin") is None:
            self.auth.roles.upsert(
                "super_admin",
                name="Super Admin",
                permissions=list(PERMISSIONS),
            )
        if self.auth.roles.get("read_only") is None:
            self.auth.roles.upsert(
                "read_only",
                name="Read Only Viewer",
                permissions=["read_research"],
            )
        if self.auth.roles.get("viewer") is None:
            self.auth.roles.upsert(
                "viewer",
                name="Viewer",
                permissions=["read_research"],
            )
        if self.auth.roles.get("enterprise_client") is None:
            self.auth.roles.upsert(
                "enterprise_client",
                name="Enterprise Client",
                permissions=["read_research"],
            )

    def ensure_dev_admin_seed(self) -> None:
        """Seed admin@dspai.local / admin / Admin@123 only when no Super Admin / Administrator exists."""
        users = self.auth.users.list_users()
        if any("super_admin" in u.roles or "administrator" in u.roles for u in users):
            return
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env in {"production", "prod"} and os.environ.get("DSP_FORCE_ADMIN_SEED") != "1":
            return
        password = os.environ.get("DSP_SEED_ADMIN_PASSWORD") or "Admin@123"
        meta = freeze_mapping(
            {
                "auth_entity": "user",
                "provider": AuthProvider.EMAIL.value,
                "email_verified": True,
                "phone_verified": False,
                "seeded": True,
            }
        )
        try:
            user = self.auth.users.create(
                username="admin",
                email="admin@dspai.local",
                password=password,
                display_name="Administrator",
                roles=["administrator"],
                user_id="seed-admin",
            )
        except DuplicateUserError:
            return
        enriched = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=user.status,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            roles=user.roles,
            metadata=meta,
        )
        self.auth.users.save(enriched)

    # --- helpers ---------------------------------------------------------

    def _rate_check(self, key: str, *, limit: int, window_sec: int = 60) -> None:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            bucket = [t for t in self._rate.get(key, []) if (now - t).total_seconds() < window_sec]
            if len(bucket) >= limit:
                self._rate[key] = bucket
                raise AuthenticationError("Rate limit exceeded. Try again later.")
            bucket.append(now)
            self._rate[key] = bucket

    def _frontend_url(self) -> str:
        return (os.environ.get("DSP_FRONTEND_URL") or "http://localhost:3000").rstrip("/")

    # Every one-time-link flow below (email verification, password reset,
    # magic link, invitation acceptance) issues/redeems its token through
    # ``self.tokens`` (a `SingleUseTokenService`, see auth.single_use_tokens)
    # instead of hand-rolling its own storage + expiry + replay logic. That
    # service is the single reusable implementation of: secure random
    # generation, expiry, single-use/atomic consumption, replay protection,
    # revocation, purpose validation, user/organization binding, and audit
    # logging — new one-time flows should use it rather than adding another
    # bespoke token dict.

    def _get_by_email(self, email: str) -> AuthUser | None:
        target = email.strip().lower()
        for user in self.auth.users.list_users():
            if user.email.casefold() == target:
                return user
        return None

    def _get_by_mobile(self, mobile: str) -> AuthUser | None:
        """Return the single user bound to ``mobile``, or None.

        If more than one account shares the same mobile value, fail closed
        (return None) so callers never guess an identity. Password login uses
        :meth:`_find_verified_mobile_users` for an explicit ambiguity check.
        """
        matches = [
            user
            for user in self.auth.users.list_users()
            if str(dict(user.metadata or {}).get("mobile") or "") == mobile
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    def _find_verified_mobile_users(self, mobile: str) -> list[AuthUser]:
        matches: list[AuthUser] = []
        for user in self.auth.users.list_users():
            meta = dict(user.metadata or {})
            if str(meta.get("mobile") or "") != mobile:
                continue
            if not bool(meta.get("phone_verified")):
                continue
            matches.append(user)
        return matches

    def _verified_mobile_of(self, user: AuthUser) -> str | None:
        meta = dict(user.metadata or {})
        if not bool(meta.get("phone_verified")):
            return None
        stored = str(meta.get("mobile") or "").strip()
        return try_normalize_india_mobile(stored)

    def _resolve_verified_otp_user(self, identifier: str) -> AuthUser | None:
        """Resolve username or mobile to a unique account with verified mobile.

        Email identifiers are ignored (email OTP is disabled). Unknown,
        unverified, or ambiguous identifiers return None — callers must not
        distinguish those cases in the public response.
        """
        ident = (identifier or "").strip()
        if not ident or "@" in ident:
            return None
        candidates: dict[str, AuthUser] = {}
        mobile = try_normalize_india_mobile(ident)
        if mobile is not None:
            for user in self._find_verified_mobile_users(mobile):
                candidates[user.user_id] = user
        try:
            by_name = self.auth.users.get_by_username(ident)
        except ValidationError:
            by_name = None
        if by_name is not None and self._verified_mobile_of(by_name):
            candidates[by_name.user_id] = by_name
        if len(candidates) != 1:
            return None
        return next(iter(candidates.values()))

    def _public_login_otp(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Never expose the stored mobile (or any destination) on login/reset OTP."""
        out = dict(payload)
        out.pop("mobile", None)
        out.pop("destination", None)
        out.pop("email_hint", None)
        return out

    def _opaque_login_otp(self, identifier: str, *, ip_hint: str | None) -> dict[str, Any]:
        return self._public_login_otp(
            self.otp.issue_undelivered_challenge(opaque_key=identifier, ip_hint=ip_hint)
        )

    def _get_by_provider_subject(self, provider: str, subject: str) -> AuthUser | None:
        for user in self.auth.users.list_users():
            meta = dict(user.metadata or {})
            for link in meta.get("linked_providers") or []:
                if (
                    str(link.get("provider") or "").upper() == provider.upper()
                    and str(link.get("provider_subject") or "") == subject
                ):
                    return user
        return None

    def _persist_meta(self, user: AuthUser, updates: dict[str, Any]) -> AuthUser:
        meta = dict(user.metadata or {})
        meta.update(updates)
        meta["auth_entity"] = "user"
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=freeze_mapping(meta),
        )
        return self.auth.users.save(updated)

    def _record_login(
        self,
        *,
        user_id: str,
        provider: str,
        success: bool,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        detail: str | None = None,
        device_label: str | None = None,
        reason: str | None = None,
    ) -> None:
        entry = LoginHistoryEntry(
            entry_id=str(uuid.uuid4()),
            user_id=user_id,
            provider=provider,
            success=success,
            created_at=utc_now().isoformat(),
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            detail=detail,
            device_label=device_label,
            reason=reason,
        )
        payload = entry.to_dict()
        payload["auth_entity"] = "login_history"
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_HISTORY_PREFIX}{entry.entry_id}",
            payload=payload,
            refs={"auth_entity": "login_history", "user_id": user_id},
            created_at=entry.created_at,
            allow_update=False,
        )

    def _issue_session(
        self,
        user: AuthUser,
        *,
        remember_me: bool = False,
        provider: str,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        device_label: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if user.status == "locked":
            raise AuthenticationError("Account is locked. Contact an administrator.")
        if user.status != "active":
            raise AuthenticationError("Account is disabled.")
        meta = dict(user.metadata or {})
        locked_until = meta.get("locked_until")
        if locked_until:
            try:
                until = datetime.fromisoformat(str(locked_until))
                if until.tzinfo is None:
                    until = until.replace(tzinfo=timezone.utc)
                if datetime.now(tz=timezone.utc) < until:
                    raise AuthenticationError("Account is locked. Try again later.")
            except AuthenticationError:
                raise
            except Exception:  # noqa: BLE001
                pass
        if meta.get("provider") == AuthProvider.EMAIL.value and not meta.get("email_verified"):
            if meta.get("requires_email_verification"):
                raise AuthenticationError("Email not verified. Check your inbox or contact admin.")
        created = created_at or utc_now().isoformat()
        refresh_ttl = 86400 * 30 if remember_me else 86400 * 7
        access_ttl = 3600 * 8 if remember_me else 3600
        authn = self.auth.authentication
        prev_access, prev_refresh = authn.access_ttl, authn.refresh_ttl
        authn.access_ttl = access_ttl
        authn.refresh_ttl = refresh_ttl
        try:
            session = self.auth.sessions.create(
                user_id=user.user_id,
                expires_in=refresh_ttl,
                refresh_token_id=str(uuid.uuid4()),
                created_at=created,
                metadata={
                    "provider": provider,
                    "remember_me": remember_me,
                    "ip_hint": ip_hint,
                    "user_agent_hint": user_agent_hint,
                    "device_label": device_label or "unknown",
                },
            )
            pair = authn._issue_pair(  # noqa: SLF001 — intentional platform bridge
                user,
                session_id=session.session_id,
                created_at=created,
                access_jti=str(uuid.uuid4()),
                refresh_jti=session.refresh_token_id,
            )
            authn.attach_initial_refresh_token(session, pair)
        finally:
            authn.access_ttl = prev_access
            authn.refresh_ttl = prev_refresh

        device = self.devices.register(
            user_id=user.user_id,
            label=device_label,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            session_id=session.session_id,
        )
        mfa_eval = self.mfa.evaluate(
            user_id=user.user_id,
            device_trusted=self.devices.is_record_trusted(device),
        )
        cleared_meta = dict(user.metadata or {})
        cleared_meta["failed_login_count"] = 0
        cleared_meta.pop("locked_until", None)
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="active",
            created_at=user.created_at,
            updated_at=created,
            last_login=created,
            roles=user.roles,
            metadata=freeze_mapping(cleared_meta),
        )
        self.auth.users.save(updated)
        self._record_login(
            user_id=user.user_id,
            provider=provider,
            success=True,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label=device_label,
        )
        enterprise = enterprise_user_public_dict(updated)
        user_payload = {
            **updated.to_dict(),
            **enterprise,
            "display_name": updated.display_name,
        }
        result = {
            "user": user_payload,
            "tokens": pair.to_dict(),
            "session": session.to_public_dict(),
            "provider": provider,
            "device": device.to_dict(),
        }
        result.update(mfa_eval.additive_fields())
        return result

    # --- registration / email --------------------------------------------

    def register_email(
        self,
        *,
        name: str,
        email: str,
        password: str,
        confirm_password: str,
        username: str | None = None,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        self._rate_check(f"register:{ip_hint or 'na'}", limit=10, window_sec=3600)
        if not name.strip():
            raise ValidationError("name is required")
        mail = email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        if password != confirm_password:
            raise ValidationError("password confirmation does not match")
        strength = password_strength(password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        uname = (username or mail.split("@", 1)[0]).strip().lower()
        uname = re.sub(r"[^a-z0-9._-]", "", uname)[:64] or f"user_{secrets.token_hex(3)}"
        try:
            user = self.auth.users.create(
                username=uname,
                email=mail,
                password=password,
                display_name=name.strip(),
                roles=["read_only"],
            )
        except DuplicateUserError:
            raise DuplicateUserError("An account with this email or username already exists.") from None
        user = self._persist_meta(
            user,
            {
                "provider": AuthProvider.EMAIL.value,
                "email_verified": False,
                "phone_verified": False,
                "requires_email_verification": True,
                "linked_providers": [],
            },
        )
        # Pending until email verified
        pending = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="disabled",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=None,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.auth.users.save(pending)
        token = self.tokens.issue(
            purpose="email_verify",
            ttl=timedelta(hours=24),
            user_id=pending.user_id,
            data={"email": pending.email},
        )
        link_url = f"{self._frontend_url()}/verify-email?token={token}"
        subject, text_body, html_body = render_email_verification_email(
            link_url=link_url, token=token, expires_hours=24
        )
        self.email.send(to=pending.email, subject=subject, body=text_body, html_body=html_body, purpose="email_verify")
        out: dict[str, Any] = {
            "user": enterprise_user_public_dict(pending),
            "verification_required": True,
            "message": "Registration accepted. Verify email before sign-in.",
        }
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["verification_token"] = token
        return out

    def verify_email(self, token: str) -> dict[str, Any]:
        record = self.tokens.consume(
            purpose="email_verify",
            token=token,
            error_cls=ValidationError,
            error_message="Invalid or expired verification token.",
        )
        user = self.auth.users.get(str(record.user_id or ""))
        if user is None:
            raise ValidationError("User not found.")
        activated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="active",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        activated = self._persist_meta(
            activated,
            {"email_verified": True, "requires_email_verification": False},
        )
        self.audit.record("email.verified", user_id=user.user_id)
        return {"ok": True, "user": enterprise_user_public_dict(activated)}

    def register_username(
        self,
        *,
        username: str,
        password: str,
        confirm_password: str,
        name: str | None = None,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        """Create an active account with username + password (no email required).

        Persists a synthetic ``@username.dspai.local`` mailbox to satisfy
        UserStore's email field — never treated as a deliverable address.
        """
        self._rate_check(f"register-username:{ip_hint or 'na'}", limit=10, window_sec=3600)
        uname = assert_username(username)
        if password != confirm_password:
            raise ValidationError("password confirmation does not match")
        strength = password_strength(password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        display = (name or uname).strip() or uname
        synthetic_email = f"{uname.lower()}{_USERNAME_EMAIL_SUFFIX}"
        try:
            user = self.auth.users.create(
                username=uname,
                email=synthetic_email,
                password=password,
                display_name=display,
                roles=["read_only"],
            )
        except DuplicateUserError:
            raise DuplicateUserError("An account with this username already exists.") from None
        user = self._persist_meta(
            user,
            {
                "provider": AuthProvider.USERNAME.value,
                "email_verified": False,
                "phone_verified": False,
                "requires_email_verification": False,
                "synthetic_email": True,
                "linked_providers": [],
            },
        )
        self.audit.record("register.username", user_id=user.user_id, ip_hint=ip_hint)
        return {
            "ok": True,
            "user": enterprise_user_public_dict(user),
            "verification_required": False,
            "message": "Account created. You can sign in with your username and password.",
        }

    def register_mobile_request(
        self, mobile: str, *, ip_hint: str | None = None
    ) -> dict[str, Any]:
        """Start mobile registration via the existing mobile OTP pipeline.

        Registration OTP is sent to the number the requester entered (they are
        proving possession). Login OTP must never do this for a username.
        """
        self._rate_check(f"register-mobile:{ip_hint or mobile}", limit=10, window_sec=3600)
        normalized = normalize_india_mobile(mobile)
        return self.otp.request_otp(normalized, ip_hint=ip_hint)

    def register_mobile_complete(
        self,
        *,
        challenge_id: str,
        code: str,
        password: str,
        confirm_password: str,
        name: str | None = None,
        username: str | None = None,
        email: str | None = None,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        """Finish mobile registration after OTP proof; set a chosen password.

        Combined public registration (username + mobile + email + password) is
        selected by supplying ``email``. That path requires username and name,
        stores the real email, and rejects duplicates. The email-less path
        keeps the previous mobile-only behaviour for existing clients.
        """
        self._rate_check(f"register-mobile-complete:{ip_hint or challenge_id}", limit=10, window_sec=600)
        if password != confirm_password:
            raise ValidationError("password confirmation does not match")
        strength = password_strength(password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")

        verified = self.otp.verify_otp_result(
            challenge_id=challenge_id, code=code, ip_hint=ip_hint
        )
        if verified.channel != "mobile":
            raise AuthenticationError("invalid credentials")
        mobile = verified.destination

        combined_email = (email or "").strip()
        if combined_email:
            return self._register_combined_after_otp(
                mobile=mobile,
                password=password,
                name=name,
                username=username,
                email=combined_email,
                ip_hint=ip_hint,
            )

        chosen_username: str | None = None
        if username and username.strip():
            chosen_username = assert_username(username.strip())

        existing = self._get_by_mobile(mobile)
        if existing is not None:
            updated = AuthUser(
                user_id=existing.user_id,
                username=existing.username,
                email=existing.email,
                display_name=existing.display_name,
                password_hash=hash_password(password),
                status="active" if existing.status != "locked" else existing.status,
                created_at=existing.created_at,
                updated_at=utc_now().isoformat(),
                last_login=existing.last_login,
                roles=existing.roles,
                metadata=existing.metadata,
            )
            updated = self._persist_meta(
                updated,
                {
                    "mobile": mobile,
                    "phone_verified": True,
                    "synthetic_email": _is_synthetic_mailbox(updated.email),
                    "requires_email_verification": False,
                    "provider": AuthProvider.PHONE.value,
                },
            )
            self.audit.record(
                "register.mobile.complete",
                user_id=updated.user_id,
                ip_hint=ip_hint,
                detail="existing",
            )
            return {
                "ok": True,
                "user": enterprise_user_public_dict(updated),
                "verification_required": False,
                "message": "Account ready. You can sign in with your mobile number and password.",
            }

        uname = chosen_username or f"m{mobile[-10:]}"
        synthetic_email = f"m{mobile[-10:]}{_PHONE_EMAIL_SUFFIX}"
        display = (name or f"Mobile {mobile[-4:]}").strip()
        try:
            created = self.auth.users.create(
                username=uname,
                email=synthetic_email,
                password=password,
                display_name=display,
                roles=["read_only"],
            )
        except DuplicateUserError as exc:
            # Username taken (user-chosen) — safe to surface as username conflict.
            if chosen_username:
                raise DuplicateUserError("An account with this username already exists.") from exc
            # Default phone username/email collision — recover by mobile email lookup.
            collided = self._get_by_email(synthetic_email)
            if collided is None:
                raise DuplicateUserError("Unable to complete registration.") from exc
            created = AuthUser(
                user_id=collided.user_id,
                username=collided.username,
                email=collided.email,
                display_name=collided.display_name,
                password_hash=hash_password(password),
                status="active",
                created_at=collided.created_at,
                updated_at=utc_now().isoformat(),
                last_login=collided.last_login,
                roles=collided.roles,
                metadata=collided.metadata,
            )
            created = self.auth.users.save(created)

        user = self._persist_meta(
            created,
            {
                "provider": AuthProvider.PHONE.value,
                "mobile": mobile,
                "phone_verified": True,
                "email_verified": False,
                "requires_email_verification": False,
                "synthetic_email": True,
                "linked_providers": [
                    {
                        "provider": AuthProvider.PHONE.value,
                        "provider_subject": mobile,
                        "email": None,
                        "linked_at": utc_now().isoformat(),
                    }
                ],
            },
        )

        self.audit.record(
            "register.mobile.complete",
            user_id=user.user_id,
            ip_hint=ip_hint,
            detail="created",
        )
        return {
            "ok": True,
            "user": enterprise_user_public_dict(user),
            "verification_required": False,
            "message": "Account created. You can sign in with your mobile number and password.",
        }

    def _register_combined_after_otp(
        self,
        *,
        mobile: str,
        password: str,
        name: str | None,
        username: str | None,
        email: str,
        ip_hint: str | None,
    ) -> dict[str, Any]:
        display = (name or "").strip()
        if not display:
            raise ValidationError("name is required")
        if not (username or "").strip():
            raise ValidationError("username is required")
        uname = assert_username(username.strip())
        mail = assert_email(email)
        if _is_synthetic_mailbox(mail):
            raise ValidationError("invalid email")

        if self._get_by_email(mail) is not None:
            raise DuplicateUserError("An account with this email or username already exists.")
        if self.auth.users.get_by_username(uname) is not None:
            raise DuplicateUserError("An account with this username already exists.")
        if self._find_verified_mobile_users(mobile) or self._get_by_mobile(mobile):
            raise DuplicateUserError("Unable to complete registration.")

        try:
            created = self.auth.users.create(
                username=uname,
                email=mail,
                password=password,
                display_name=display,
                roles=["read_only"],
            )
        except DuplicateUserError as exc:
            raise DuplicateUserError(
                "An account with this email or username already exists."
            ) from exc

        user = self._persist_meta(
            created,
            {
                "provider": AuthProvider.USERNAME.value,
                "mobile": mobile,
                "phone_verified": True,
                "email_verified": False,
                "requires_email_verification": False,
                "synthetic_email": False,
                "linked_providers": [
                    {
                        "provider": AuthProvider.PHONE.value,
                        "provider_subject": mobile,
                        "email": None,
                        "linked_at": utc_now().isoformat(),
                    }
                ],
            },
        )
        self.audit.record(
            "register.combined",
            user_id=user.user_id,
            ip_hint=ip_hint,
            detail="created",
        )
        return {
            "ok": True,
            "user": enterprise_user_public_dict(user),
            "verification_required": False,
            "message": "Account created. You can sign in with your username, mobile OTP, or password.",
        }

    def _register_failed_login(self, user: AuthUser, *, ip_hint: str | None, provider: str) -> None:
        meta = dict(user.metadata or {})
        fails = int(meta.get("failed_login_count") or 0) + 1
        meta["failed_login_count"] = fails
        status = user.status
        if fails >= self._lockout_threshold:
            until = (
                datetime.now(tz=timezone.utc) + timedelta(seconds=self._lockout_seconds)
            ).isoformat()
            meta["locked_until"] = until
            status = "locked"
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=freeze_mapping(meta),
        )
        self.auth.users.save(updated)
        self._record_login(
            user_id=user.user_id,
            provider=provider,
            success=False,
            ip_hint=ip_hint,
            detail="invalid credentials",
            reason="invalid_credentials",
        )

    def login_password(
        self,
        *,
        identifier: str,
        password: str,
        remember_me: bool = False,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        device_label: str | None = None,
    ) -> dict[str, Any]:
        """Resolve ``identifier`` then verify password.

        Resolution order (fail closed on ambiguity / unverified mobile):
        1. email (``@`` present)
        2. username
        3. verified India mobile only (``phone_verified`` + matching ``mobile``)
        """
        self._rate_check(f"login:{ip_hint or identifier}", limit=20, window_sec=300)
        ident = identifier.strip()
        user = None
        provider = AuthProvider.USERNAME.value
        if "@" in ident:
            user = self._get_by_email(ident)
            provider = AuthProvider.EMAIL.value
        if user is None:
            # Username lookup rejects non-username shapes (email/mobile); ignore.
            try:
                user = self.auth.users.get_by_username(ident)
            except ValidationError:
                user = None
            if user is not None:
                provider = AuthProvider.USERNAME.value
        if user is None:
            # Verified-mobile password login (after email/username miss).
            mobile = try_normalize_india_mobile(ident)
            if mobile is not None:
                matches = self._find_verified_mobile_users(mobile)
                if len(matches) > 1:
                    # Ambiguous verified mobile — never guess.
                    raise AuthenticationError("invalid credentials")
                if len(matches) == 1:
                    user = matches[0]
                    provider = AuthProvider.PHONE.value
                # Unverified or unknown mobile: fall through as invalid
                # credentials (same message as unknown identifier).
        if user is None or not user.password_hash or not verify_password(
            password, user.password_hash
        ):
            if user:
                self._register_failed_login(user, ip_hint=ip_hint, provider=provider)
            raise AuthenticationError("invalid credentials")
        if needs_rehash(user.password_hash):
            user = AuthUser(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                display_name=user.display_name,
                password_hash=hash_password(password),
                status=user.status,
                created_at=user.created_at,
                updated_at=utc_now().isoformat(),
                last_login=user.last_login,
                roles=user.roles,
                metadata=user.metadata,
            )
            self.auth.users.save(user)
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=provider,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label=device_label,
        )

    def request_password_reset(self, email: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._rate_check(f"reset:{ip_hint or email}", limit=5, window_sec=3600)
        mail = email.strip().lower()
        user = self._get_by_email(mail)
        # Always opaque success
        out: dict[str, Any] = {
            "ok": True,
            "message": "If an account exists, a reset token was issued.",
        }
        if user is None:
            return out
        # Never promise / send email reset for synthetic phone/username mailboxes.
        if _is_synthetic_mailbox(user.email) or bool(
            dict(user.metadata or {}).get("synthetic_email")
        ):
            return out
        token = self.tokens.issue(
            purpose="password_reset",
            ttl=timedelta(hours=1),
            user_id=user.user_id,
            ip_hint=ip_hint,
        )
        link_url = f"{self._frontend_url()}/reset-password?token={token}"
        subject, text_body, html_body = render_password_reset_email(
            link_url=link_url, token=token, expires_minutes=60
        )
        self.email.send(to=user.email, subject=subject, body=text_body, html_body=html_body, purpose="password_reset")
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["reset_token"] = token
        return out

    def confirm_password_reset(self, token: str, new_password: str) -> dict[str, Any]:
        strength = password_strength(new_password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        record = self.tokens.consume(
            purpose="password_reset",
            token=token,
            error_cls=ValidationError,
            error_message="Invalid or expired reset token.",
        )
        user = self.auth.users.get(str(record.user_id or ""))
        if user is None:
            raise ValidationError("User not found.")
        return self._finalize_password_reset(user, new_password)

    def request_password_reset_otp(
        self, identifier: str, *, ip_hint: str | None = None
    ) -> dict[str, Any]:
        """Primary public recovery: OTP to the account's verified mobile.

        Always returns the same shape. Never echoes the stored mobile. Never
        sends to a mobile supplied by the requester when recovering by username.
        """
        self._rate_check(f"reset-otp:{ip_hint or identifier}", limit=5, window_sec=3600)
        ident = (identifier or "").strip()
        out: dict[str, Any] = {
            "ok": True,
            "message": "If an account exists, a verification code was sent.",
        }
        if "@" in ident:
            # Email is stored but is not a recovery destination in this flow.
            opaque = self._opaque_login_otp(ident, ip_hint=ip_hint)
            out["challenge_id"] = opaque.get("challenge_id")
            out["expires_at"] = opaque.get("expires_at")
            return out
        user = self._resolve_verified_otp_user(ident)
        stored = self._verified_mobile_of(user) if user is not None else None
        if user is None or stored is None:
            opaque = self._opaque_login_otp(ident, ip_hint=ip_hint)
            out["challenge_id"] = opaque.get("challenge_id")
            out["expires_at"] = opaque.get("expires_at")
            return out
        sent = self._public_login_otp(self.otp.request_otp(stored, ip_hint=ip_hint))
        out["challenge_id"] = sent.get("challenge_id")
        out["expires_at"] = sent.get("expires_at")
        if sent.get("sms"):
            out["sms"] = sent["sms"]
        return out

    def confirm_password_reset_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        new_password: str,
        confirm_password: str,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        if new_password != confirm_password:
            raise ValidationError("password confirmation does not match")
        strength = password_strength(new_password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        verified = self.otp.verify_otp_result(
            challenge_id=challenge_id, code=code, ip_hint=ip_hint
        )
        if verified.channel != "mobile":
            raise AuthenticationError("invalid credentials")
        matches = self._find_verified_mobile_users(verified.destination)
        if len(matches) != 1:
            raise AuthenticationError("invalid credentials")
        return self._finalize_password_reset(matches[0], new_password)

    def _finalize_password_reset(self, user: AuthUser, new_password: str) -> dict[str, Any]:
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=hash_password(new_password),
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.auth.users.save(updated)
        self.tokens.revoke_all_for_user(purpose="password_reset", user_id=user.user_id)
        self.audit.record("password.reset", user_id=user.user_id)
        revoked_count = 0
        for session in self.auth.sessions.list_sessions(user_id=user.user_id):
            try:
                self.auth.sessions.revoke(session.session_id)
                revoked_count += 1
            except Exception:  # noqa: BLE001
                pass
        if revoked_count:
            self.audit.record(
                "session.revoked",
                user_id=user.user_id,
                detail=f"password_reset:{revoked_count}",
            )
        return {"ok": True, "user": enterprise_user_public_dict(updated)}

    def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        strength = password_strength(new_password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=hash_password(new_password),
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.auth.users.save(updated)
        return {"ok": True, "user": enterprise_user_public_dict(updated)}

    # --- OAuth -----------------------------------------------------------

    @staticmethod
    def _oauth_event(provider: str, action: str) -> str:
        """Namespaced audit event type, e.g. ``oauth.facebook.login``.

        Single naming convention shared by every OAuth provider (Google,
        Microsoft, Facebook, and any future one) — never hand-rolled
        per-provider so provider-specific audit coverage comes "for free".
        """
        return f"oauth.{provider.strip().lower()}.{action}"

    @staticmethod
    def _oauth_failure_detail(provider: str, exc: BaseException) -> str:
        if isinstance(exc, OAuthChallengeError):
            return f"{provider.strip().upper()}:{exc.reason}"
        return str(exc)[:300]

    def oauth_begin(self, provider: str, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        return self.oauth.begin(provider, redirect_uri=redirect_uri, state=state)

    def oauth_callback(
        self,
        provider: str,
        *,
        code: str,
        state: str | None,
        redirect_uri: str,
        remember_me: bool = False,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        try:
            profile = self.oauth.complete(
                provider, code=code, state=state, redirect_uri=redirect_uri
            )
            self.audit.record(
                self._oauth_event(provider, "callback"),
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=provider,
            )
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                self._oauth_event(provider, "failure"),
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=self._oauth_failure_detail(provider, exc),
            )
            raise
        try:
            return self._login_from_oauth_profile(
                profile,
                remember_me=remember_me,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
            )
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                self._oauth_event(provider, "failure"),
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=self._oauth_failure_detail(provider, exc),
            )
            raise

    def _attach_provider_link(self, user: AuthUser, profile: OAuthProfile) -> AuthUser:
        """Bind ``profile`` to ``user`` as a linked identity (idempotent).

        Shared by both implicit login-time linking (matching by verified
        email in :meth:`_login_from_oauth_profile`) and explicit
        authenticated linking (:meth:`link_oauth_provider`) so there is a
        single place that mutates ``linked_providers`` — never duplicated.
        """
        meta = dict(user.metadata or {})
        links = [
            lnk
            for lnk in (meta.get("linked_providers") or [])
            if not (
                str(lnk.get("provider") or "").upper() == profile.provider.upper()
                and str(lnk.get("provider_subject") or "") == profile.subject
            )
        ]
        links.append(
            {
                "provider": profile.provider,
                "provider_subject": profile.subject,
                "email": profile.email,
                "linked_at": utc_now().isoformat(),
            }
        )
        return self._persist_meta(
            user,
            {
                "linked_providers": links,
                "avatar": profile.avatar or meta.get("avatar"),
                "email_verified": True,
                "requires_email_verification": False,
            },
        )

    def link_oauth_provider(
        self,
        user_id: str,
        provider: str,
        *,
        code: str,
        state: str | None,
        redirect_uri: str,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        """Link a verified OAuth identity to an *already-authenticated* user.

        Unlike :meth:`oauth_callback` (sign-in — matches by verified email
        or auto-provisions a new account), this binds the resulting
        identity to a specific existing user and refuses the link outright
        if that identity, or its email, already belongs to a *different*
        account — preventing account takeover via a mismatched OAuth
        response. Reuses the same PKCE/nonce/JWKS-verified OAuth exchange
        (`self.oauth.complete`) as every other provider; no OAuth logic is
        duplicated here.
        """
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        try:
            profile = self.oauth.complete(provider, code=code, state=state, redirect_uri=redirect_uri)
            if not profile.email:
                raise AuthenticationError("OAuth provider did not return an email address.")
            if not profile.email_verified:
                raise AuthenticationError("OAuth email is not verified by the provider.")
            existing = self._get_by_provider_subject(profile.provider, profile.subject)
            if existing is not None and existing.user_id != user.user_id:
                raise ValidationError(
                    f"This {provider.title()} account is already linked to a different user."
                )
            other = self._get_by_email(profile.email)
            if other is not None and other.user_id != user.user_id:
                raise ValidationError(
                    "This account's email is already associated with a different user."
                )
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                self._oauth_event(provider, "failure"),
                user_id=user.user_id,
                ip_hint=ip_hint,
                detail=self._oauth_failure_detail(provider, exc),
            )
            raise
        updated = self._attach_provider_link(user, profile)
        self.audit.record(
            self._oauth_event(provider, "link"),
            user_id=updated.user_id,
            ip_hint=ip_hint,
            detail=profile.provider,
        )
        return {"ok": True, "user": enterprise_user_public_dict(updated)}

    def _login_from_oauth_profile(
        self,
        profile: OAuthProfile,
        *,
        remember_me: bool = False,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        if not profile.email:
            raise AuthenticationError("OAuth provider did not return an email address.")
        if not profile.email_verified:
            raise AuthenticationError("OAuth email is not verified by the provider.")
        user = self._get_by_provider_subject(profile.provider, profile.subject)
        if user is None:
            user = self._get_by_email(profile.email)
            if user is not None:
                # Link provider to existing email account (prevent duplicates)
                user = self._attach_provider_link(user, profile)
            else:
                # Auto-create
                username = stable_username_from_email(profile.email, profile.provider)
                random_password = secrets.token_urlsafe(32)
                try:
                    created = self.auth.users.create(
                        username=username,
                        email=profile.email,
                        password=random_password,
                        display_name=profile.name or profile.email,
                        roles=["read_only"],
                    )
                except DuplicateUserError:
                    # Race: fetch again
                    created = self._get_by_email(profile.email)
                    if created is None:
                        raise
                user = self._persist_meta(
                    created,
                    {
                        "provider": profile.provider,
                        "avatar": profile.avatar,
                        "email_verified": True,
                        "phone_verified": False,
                        "requires_email_verification": False,
                        "linked_providers": [
                            {
                                "provider": profile.provider,
                                "provider_subject": profile.subject,
                                "email": profile.email,
                                "linked_at": utc_now().isoformat(),
                            }
                        ],
                    },
                )
        if user.status != "active":
            # Activate OAuth users that were pending email verify on same address
            user = AuthUser(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                display_name=profile.name or user.display_name,
                password_hash=user.password_hash,
                status="active",
                created_at=user.created_at,
                updated_at=utc_now().isoformat(),
                last_login=user.last_login,
                roles=user.roles,
                metadata=user.metadata,
            )
            self.auth.users.save(user)
        self.audit.record(
            self._oauth_event(profile.provider, "login"),
            user_id=user.user_id,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            detail=profile.provider,
        )
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=profile.provider,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label=f"oauth:{profile.provider.lower()}",
        )

    # --- OTP -------------------------------------------------------------
    #
    # Mobile/SMS OTP only. Numeric email OTP is removed — email sign-in is
    # Google OAuth (plus password for provisioned accounts). Mobile OTP may
    # still auto-provision ``@phone.dspai.local`` users. Phone↔email linking
    # remains deferred to Phase 2F.

    def request_login_otp(
        self,
        identifier: str,
        *,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        """OTP request for username or verified India mobile.

        Username OTP is always sent to the account's stored verified mobile —
        never to a mobile supplied alongside the username. Unknown, unverified,
        or ambiguous identifiers return an opaque challenge (no SMS).
        """
        self._rate_check(f"otp:{ip_hint or identifier}", limit=10, window_sec=3600)
        otp_flag = (os.environ.get("DSP_AUTH_PROVIDER_OTP") or "auto").strip().lower()
        if otp_flag in {"disabled", "coming_soon", "off", "false", "0"}:
            raise AuthenticationError("OTP intentionally disabled — Coming Soon.")
        ident = (identifier or "").strip()
        if "@" in ident:
            raise ValidationError(
                "Email OTP is no longer supported. Sign in with Google or password, "
                "or use mobile OTP."
            )
        user = self._resolve_verified_otp_user(ident)
        stored = self._verified_mobile_of(user) if user is not None else None
        if user is None or stored is None:
            return self._opaque_login_otp(ident, ip_hint=ip_hint)
        return self._public_login_otp(self.otp.request_otp(stored, ip_hint=ip_hint))

    def request_mobile_otp(self, mobile: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        """Backward-compatible mobile-only entry point."""
        return self.request_login_otp(mobile, ip_hint=ip_hint)

    def resend_mobile_otp(self, mobile: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        """Resend uses the same request path (enforces 30s cooldown)."""
        return self.request_login_otp(mobile, ip_hint=ip_hint)

    def resend_login_otp(self, identifier: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        return self.request_login_otp(identifier, ip_hint=ip_hint)

    def verify_login_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        remember_me: bool = False,
        name: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        """Mobile OTP verify — issues the normal enterprise session."""
        result = self.otp.verify_otp_result(
            challenge_id=challenge_id, code=code, ip_hint=ip_hint
        )
        if result.channel != "mobile":
            raise AuthenticationError(
                "Email OTP is no longer supported. Sign in with Google or password."
            )
        return self._complete_mobile_otp_login(
            mobile=result.destination,
            remember_me=remember_me,
            name=name,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )

    def verify_mobile_otp(
        self,
        *,
        challenge_id: str,
        code: str,
        remember_me: bool = False,
        name: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible mobile verify (delegates to unified path)."""
        return self.verify_login_otp(
            challenge_id=challenge_id,
            code=code,
            remember_me=remember_me,
            name=name,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )

    def _complete_mobile_otp_login(
        self,
        *,
        mobile: str,
        remember_me: bool,
        name: str | None,
        ip_hint: str | None,
        user_agent_hint: str | None,
    ) -> dict[str, Any]:
        _ = name  # retained for call-site compatibility; new accounts are created via /register
        matches = self._find_verified_mobile_users(mobile)
        if len(matches) != 1:
            raise AuthenticationError("invalid credentials")
        user = matches[0]
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=AuthProvider.PHONE.value,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label="mobile-otp",
        )

    # --- MFA: TOTP ---------------------------------------------------------

    def _require_mfa_enabled(self) -> None:
        if not self.mfa.enabled():
            raise ValidationError(
                "MFA is disabled on this deployment. Set DSP_AUTH_MFA=true to enable."
            )

    def mfa_totp_enroll_begin(self, user_id: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._require_mfa_enabled()
        self._rate_check(f"mfa-enroll:{user_id}", limit=5, window_sec=3600)
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        result = self.mfa.totp.begin_enroll(user_id, account_name=user.email or user.username)  # type: ignore[call-arg]
        self.audit.record("mfa.enroll.begin", user_id=user_id, ip_hint=ip_hint, detail="totp")
        return result

    def mfa_totp_enroll_confirm(
        self, user_id: str, code: str, *, ip_hint: str | None = None
    ) -> dict[str, Any]:
        self._require_mfa_enabled()
        self._rate_check(f"mfa-enroll-confirm:{user_id}", limit=10, window_sec=600)
        try:
            result = self.mfa.totp.confirm_enroll(user_id, {"code": code})
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                "mfa.enroll.failure", user_id=user_id, ip_hint=ip_hint, detail=str(exc)[:300]
            )
            raise
        self.audit.record("mfa.enroll.success", user_id=user_id, ip_hint=ip_hint, detail="totp")
        self.audit.record(
            "mfa.enable",
            user_id=user_id,
            ip_hint=ip_hint,
            detail="totp",
            metadata={"recovery_codes_issued": len(result.get("recovery_codes") or [])},
        )
        return result

    def mfa_totp_verify_stepup(
        self,
        *,
        mfa_token: str,
        code: str | None = None,
        recovery_code: str | None = None,
        remember_device: bool = False,
        device_id: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        self._require_mfa_enabled()
        user_id = self.mfa.resolve_mfa_token(mfa_token)
        self._rate_check(f"mfa-verify:{user_id}", limit=8, window_sec=300)
        payload: dict[str, Any] = {}
        if code:
            payload["code"] = code
        if recovery_code:
            payload["recovery_code"] = recovery_code
        ok = self.mfa.totp.verify_challenge(user_id, payload)
        if not ok:
            self.audit.record(
                "mfa.verify.failure",
                user_id=user_id,
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail="recovery_code" if recovery_code else "totp",
            )
            raise AuthenticationError("Invalid or expired authenticator code.")
        self.audit.record(
            "mfa.verify.success",
            user_id=user_id,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            detail="recovery_code" if recovery_code else "totp",
        )
        if recovery_code:
            self.audit.record(
                "mfa.recovery.used", user_id=user_id, ip_hint=ip_hint, user_agent_hint=user_agent_hint
            )
        if remember_device and device_id:
            try:
                self.devices.set_trusted(device_id, user_id=user_id, trusted=True)
            except KeyError:
                pass
        return {"ok": True, "user_id": user_id}

    def mfa_totp_disable(
        self,
        user_id: str,
        *,
        current_password: str | None = None,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        if current_password is not None and not verify_password(current_password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        totp = getattr(self.mfa, "totp", None)
        if totp is not None and hasattr(totp, "disable"):
            totp.disable(user_id)
        self.audit.record("mfa.disable", user_id=user_id, ip_hint=ip_hint, detail="totp")
        return {"ok": True}

    def mfa_recovery_codes_status(self, user_id: str) -> dict[str, Any]:
        self._require_mfa_enabled()
        totp = getattr(self.mfa, "totp", None)
        status = getattr(totp, "recovery_codes_status", None)
        if status is None:
            raise ValidationError("Recovery codes are not supported by this MFA adapter.")
        return status(user_id)

    def mfa_recovery_codes_regenerate(
        self,
        user_id: str,
        *,
        current_password: str | None = None,
        ip_hint: str | None = None,
    ) -> dict[str, Any]:
        self._require_mfa_enabled()
        self._rate_check(f"mfa-recovery-regen:{user_id}", limit=5, window_sec=3600)
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        if current_password is not None and not verify_password(current_password, user.password_hash):
            raise AuthenticationError("invalid credentials")
        totp = getattr(self.mfa, "totp", None)
        regenerate = getattr(totp, "regenerate_recovery_codes", None)
        if regenerate is None:
            raise ValidationError("Recovery codes are not supported by this MFA adapter.")
        codes = regenerate(user_id)
        self.audit.record(
            "mfa.recovery.regenerated",
            user_id=user_id,
            ip_hint=ip_hint,
            detail="totp",
            metadata={"count": len(codes)},
        )
        return {"ok": True, "recovery_codes": codes}

    # --- MFA / Passkey: WebAuthn --------------------------------------------
    #
    # One shared credential store + ceremony implementation
    # (`auth.mfa_webauthn.WebAuthnAdapter`, behind `self.mfa.webauthn`)
    # serves two entry points into the *same* passkeys:
    #   - MFA step-up, via `/auth/mfa/webauthn/*` (registered credentials are
    #     used as a *second* factor after password login).
    #   - Primary, passwordless sign-in, via `/auth/passkey/*` (discoverable/
    #     resident credentials let a user sign in with no prior identifier).
    # Both route groups call these exact same platform methods — nothing is
    # duplicated between them, only the URL surface differs.

    def webauthn_register_begin(self, user_id: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._require_mfa_enabled()
        self.audit.record("passkey.register.begin", user_id=user_id, ip_hint=ip_hint)
        try:
            return self.mfa.webauthn.begin_registration(user_id)
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                "passkey.register.failure", user_id=user_id, ip_hint=ip_hint, detail=str(exc)[:300]
            )
            raise

    def webauthn_register_complete(
        self, user_id: str, credential: dict[str, Any], *, ip_hint: str | None = None
    ) -> dict[str, Any]:
        self._require_mfa_enabled()
        try:
            result = self.mfa.webauthn.complete_registration(user_id, credential)
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                "passkey.register.failure", user_id=user_id, ip_hint=ip_hint, detail=str(exc)[:300]
            )
            raise
        self.audit.record(
            "passkey.register.success",
            user_id=user_id,
            ip_hint=ip_hint,
            detail=str(result.get("credential_id") or ""),
        )
        return result

    def webauthn_authenticate_begin(self, identifier: str | None = None) -> dict[str, Any]:
        self._require_mfa_enabled()
        webauthn = self.mfa.webauthn
        begin = getattr(webauthn, "begin_discoverable_authentication", None)
        if begin is None:
            raise ValidationError("WebAuthn discoverable login not supported by this adapter.")
        return begin(identifier)

    def webauthn_authenticate_complete(
        self,
        assertion: dict[str, Any],
        *,
        remember_me: bool = False,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        self._require_mfa_enabled()
        webauthn = self.mfa.webauthn
        complete = getattr(webauthn, "complete_discoverable_authentication", None)
        if complete is None:
            raise ValidationError("WebAuthn discoverable login not supported by this adapter.")
        try:
            resolved = complete(assertion)
            user = self.auth.users.get(str(resolved.get("user_id") or ""))
            if user is None:
                raise AuthenticationError("Passkey account not found.")
        except Exception as exc:  # noqa: BLE001
            self.audit.record(
                "passkey.login.failure",
                ip_hint=ip_hint,
                user_agent_hint=user_agent_hint,
                detail=str(exc)[:300],
            )
            raise
        session = self._issue_session(
            user,
            remember_me=remember_me,
            provider=AuthProvider.PASSKEY.value,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label="passkey",
        )
        self.audit.record(
            "passkey.login.success",
            user_id=user.user_id,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )
        return session

    def webauthn_list_credentials(self, user_id: str) -> list[dict[str, Any]]:
        webauthn = self.mfa.webauthn
        lister = getattr(webauthn, "list_credentials", None)
        return list(lister(user_id)) if lister else []

    def webauthn_remove_credential(
        self, user_id: str, credential_id: str, *, ip_hint: str | None = None
    ) -> dict[str, Any]:
        webauthn = self.mfa.webauthn
        remover = getattr(webauthn, "remove_credential", None)
        removed = bool(remover(user_id, credential_id)) if remover else False
        if not removed:
            raise ValidationError("credential not found")
        self.audit.record(
            "passkey.deleted", user_id=user_id, ip_hint=ip_hint, detail=credential_id
        )
        return {"ok": True}

    # --- Magic link ------------------------------------------------------

    def request_magic_link(self, email: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._rate_check(f"magic:{ip_hint or email}", limit=5, window_sec=3600)
        mail = email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        token = self.tokens.issue(
            purpose="magic_link",
            ttl=timedelta(minutes=15),
            data={"email": mail},
            ip_hint=ip_hint,
        )
        link_url = f"{self._frontend_url()}/magic-link?token={token}"
        subject, text_body, html_body = render_magic_link_email(
            link_url=link_url, token=token, expires_minutes=15
        )
        self.email.send(to=mail, subject=subject, body=text_body, html_body=html_body, purpose="magic_link")
        out: dict[str, Any] = {
            "ok": True,
            "message": "If the email is eligible, a magic link was issued.",
        }
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["magic_token"] = token
        return out

    def consume_magic_link(
        self,
        token: str,
        *,
        remember_me: bool = False,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        record = self.tokens.consume(
            purpose="magic_link",
            token=token,
            ip_hint=ip_hint,
            error_cls=AuthenticationError,
            error_message="Invalid or expired magic link.",
        )
        email = str(record.data.get("email") or "").lower()
        user = self._get_by_email(email)
        if user is None:
            created = self.auth.users.create(
                username=stable_username_from_email(email, AuthProvider.MAGIC_LINK.value),
                email=email,
                password=secrets.token_urlsafe(24),
                display_name=email.split("@", 1)[0],
                roles=["read_only"],
            )
            user = self._persist_meta(
                created,
                {
                    "provider": AuthProvider.MAGIC_LINK.value,
                    "email_verified": True,
                    "requires_email_verification": False,
                },
            )
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=AuthProvider.MAGIC_LINK.value,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label="magic-link",
        )

    # --- Request access workflow -----------------------------------------

    def submit_access_request(
        self,
        *,
        name: str,
        email: str,
        organization: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValidationError("name is required")
        mail = email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        for existing in self.list_access_requests():
            if existing["email"].casefold() == mail and existing["status"] in {
                "pending",
                "approved",
                "invited",
            }:
                raise DuplicateUserError("An access request for this email is already open.")
        now = utc_now().isoformat()
        req = AccessRequest(
            request_id=str(uuid.uuid4()),
            name=name.strip(),
            email=mail,
            organization=organization.strip(),
            reason=reason.strip(),
            status="pending",
            created_at=now,
            updated_at=now,
        )
        payload = req.to_dict()
        payload["auth_entity"] = "access_request"
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_ACCESS_PREFIX}{req.request_id}",
            payload=payload,
            refs={"auth_entity": "access_request", "email": mail},
            created_at=now,
            allow_update=False,
        )
        return {"ok": True, "request": req.to_dict()}

    def list_access_requests(self, *, status: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entity_id in self.auth.persistence.list_ids("metadata"):
            if not str(entity_id).startswith(_ACCESS_PREFIX):
                continue
            row = self.auth.persistence.get("metadata", entity_id)
            if not row:
                continue
            payload = row.get("payload") or {}
            if status and payload.get("status") != status:
                continue
            out.append(payload)
        out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return out

    def decide_access_request(
        self,
        request_id: str,
        *,
        approve: bool,
        actor_user_id: str,
        notes: str | None = None,
        role: str = "enterprise_client",
    ) -> dict[str, Any]:
        row = self.auth.persistence.get("metadata", f"{_ACCESS_PREFIX}{request_id}")
        if row is None:
            raise ValidationError("access request not found")
        payload = dict(row.get("payload") or {})
        if payload.get("status") not in {"pending", "approved"}:
            raise ValidationError(f"request status is {payload.get('status')}")
        now = utc_now().isoformat()
        if not approve:
            payload.update(
                {
                    "status": "rejected",
                    "updated_at": now,
                    "decided_by": actor_user_id,
                    "notes": notes,
                }
            )
            self.auth.persistence.put(
                kind="metadata",
                entity_id=f"{_ACCESS_PREFIX}{request_id}",
                payload=payload,
                refs={"auth_entity": "access_request"},
                created_at=now,
                allow_update=True,
            )
            return {"ok": True, "request": payload}

        mapped_role = _normalize_role(role)
        organization = str(payload.get("organization") or "").strip() or None
        invite_ttl_hours = 72
        invite_token = self.tokens.issue(
            purpose="invitation",
            ttl=timedelta(hours=invite_ttl_hours),
            organization_id=organization,
            data={
                "request_id": request_id,
                "email": payload["email"],
                "name": payload["name"],
                "role": mapped_role,
            },
        )
        payload.update(
            {
                "status": "invited",
                "updated_at": now,
                "decided_by": actor_user_id,
                "notes": notes,
                "role": mapped_role,
            }
        )
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_ACCESS_PREFIX}{request_id}",
            payload=payload,
            refs={"auth_entity": "access_request"},
            created_at=now,
            allow_update=True,
        )
        link_url = f"{self._frontend_url()}/invite?token={invite_token}"
        subject, text_body, html_body = render_invitation_email(
            link_url=link_url,
            token=invite_token,
            org_name=organization,
            role=mapped_role,
            expires_hours=invite_ttl_hours,
        )
        self.email.send(
            to=str(payload["email"]), subject=subject, body=text_body, html_body=html_body, purpose="invitation"
        )
        self.audit.record(
            "invitation.issued",
            organization_id=organization,
            detail=f"request_id={request_id};role={mapped_role}",
            metadata={"actor_user_id": actor_user_id, "email": payload["email"]},
        )
        out = {"ok": True, "request": payload}
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["invitation_token"] = invite_token
        return out

    def accept_invitation(
        self,
        *,
        token: str,
        password: str,
        confirm_password: str,
        username: str | None = None,
    ) -> dict[str, Any]:
        record = self.tokens.consume(
            purpose="invitation",
            token=token,
            error_cls=ValidationError,
            error_message="Invalid or expired invitation token.",
        )
        invite = record.data
        if password != confirm_password:
            raise ValidationError("password confirmation does not match")
        strength = password_strength(password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        email = str(invite["email"]).lower()
        name = str(invite.get("name") or email)
        role = _normalize_role(str(invite.get("role") or "enterprise_client"))
        uname = (username or email.split("@", 1)[0]).strip().lower()
        uname = re.sub(r"[^a-z0-9._-]", "", uname)[:64] or f"user_{secrets.token_hex(3)}"
        existing = self._get_by_email(email)
        if existing:
            raise DuplicateUserError("Account already exists for this email. Sign in instead.")
        user = self.auth.users.create(
            username=uname,
            email=email,
            password=password,
            display_name=name,
            roles=[role],
        )
        user = self._persist_meta(
            user,
            {
                "provider": AuthProvider.EMAIL.value,
                "email_verified": True,
                "requires_email_verification": False,
                "via_invitation": True,
                "organization": record.organization_id,
            },
        )
        self.audit.record(
            "invitation.accepted",
            user_id=user.user_id,
            organization_id=record.organization_id,
        )
        # Mark request completed
        request_id = invite.get("request_id")
        if request_id:
            req_row = self.auth.persistence.get("metadata", f"{_ACCESS_PREFIX}{request_id}")
            if req_row:
                payload = dict(req_row.get("payload") or {})
                payload["status"] = "completed"
                payload["updated_at"] = utc_now().isoformat()
                self.auth.persistence.put(
                    kind="metadata",
                    entity_id=f"{_ACCESS_PREFIX}{request_id}",
                    payload=payload,
                    refs={"auth_entity": "access_request"},
                    created_at=payload.get("created_at") or utc_now().isoformat(),
                    allow_update=True,
                )
        return {"ok": True, "user": enterprise_user_public_dict(user)}

    # --- Admin -----------------------------------------------------------

    def admin_list_users(self) -> list[dict[str, Any]]:
        return [enterprise_user_public_dict(u) for u in self.auth.users.list_users()]

    def admin_set_status(self, user_id: str, *, active: bool) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="active" if active else "disabled",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.auth.users.save(updated)
        if not active:
            revoked_count = 0
            for session in self.auth.sessions.list_sessions(user_id=user_id):
                try:
                    self.auth.sessions.revoke(session.session_id)
                    revoked_count += 1
                except Exception:  # noqa: BLE001
                    pass
            if revoked_count:
                self.audit.record(
                    "session.revoked",
                    user_id=user_id,
                    detail=f"admin_deactivate:{revoked_count}",
                )
        return enterprise_user_public_dict(updated)

    def admin_reset_password(self, user_id: str, new_password: str) -> dict[str, Any]:
        strength = password_strength(new_password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=hash_password(new_password),
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        self.auth.users.save(updated)
        return {"ok": True, "user": enterprise_user_public_dict(updated)}

    def admin_assign_roles(self, user_id: str, roles: list[str], *, actor_roles: list[str] | None = None) -> dict[str, Any]:
        mapped = [_normalize_role(r) for r in roles]
        if "super_admin" in mapped and "super_admin" not in (actor_roles or []):
            raise AuthorizationError("Only Super Admin can assign super_admin.")
        target = self.auth.users.get(user_id)
        if target and "super_admin" in target.roles and "super_admin" not in mapped:
            if "super_admin" not in (actor_roles or []):
                raise AuthorizationError("Only Super Admin can modify Super Admin roles.")
        return enterprise_user_public_dict(self.auth.users.set_roles(user_id, mapped))

    def login_history(self, user_id: str | None = None, *, limit: int = 100) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entity_id in self.auth.persistence.list_ids("metadata"):
            if not str(entity_id).startswith(_HISTORY_PREFIX):
                continue
            row = self.auth.persistence.get("metadata", entity_id)
            if not row:
                continue
            payload = row.get("payload") or {}
            if user_id and payload.get("user_id") != user_id:
                continue
            out.append(payload)
        out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return out[:limit]

    def list_active_sessions(self, user_id: str | None = None) -> list[dict[str, Any]]:
        sessions = self.auth.sessions.list_sessions(user_id=user_id) if hasattr(
            self.auth.sessions, "list_sessions"
        ) else []
        return [
            s.to_public_dict() if hasattr(s, "to_public_dict") else dict(s)
            for s in sessions
            if not getattr(s, "revoked", False)
        ]

    def get_profile(self, user_id: str) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        return enterprise_user_public_dict(user)

    def update_profile(
        self,
        user_id: str,
        *,
        name: str | None = None,
        avatar: str | None = None,
    ) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        display = name.strip() if name else user.display_name
        if name is not None and not display:
            raise ValidationError("name is required")
        meta = dict(user.metadata or {})
        if avatar is not None:
            meta["avatar"] = avatar
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=display,
            password_hash=user.password_hash,
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=freeze_mapping(meta),
        )
        self.auth.users.save(updated)
        return enterprise_user_public_dict(updated)

    def change_email(self, user_id: str, new_email: str) -> dict[str, Any]:
        mail = new_email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        if self._get_by_email(mail):
            raise DuplicateUserError("Email already in use.")
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        token = self.tokens.issue(
            purpose="email_change",
            ttl=timedelta(hours=24),
            user_id=user_id,
            data={"email": mail},
        )
        self.email.send(
            to=mail,
            subject="Confirm your new DSP email",
            body=f"Confirm email change.\nTOKEN={token}\n",
            purpose="change_email",
        )
        out: dict[str, Any] = {
            "ok": True,
            "message": "Verification sent to the new email address.",
            "verification_required": True,
        }
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["verification_token"] = token
        return out

    def confirm_change_email(self, token: str) -> dict[str, Any]:
        record = self.tokens.consume(
            purpose="email_change",
            token=token,
            error_cls=ValidationError,
            error_message="Invalid or expired email change token.",
        )
        user = self.auth.users.get(str(record.user_id or ""))
        if user is None:
            raise ValidationError("user not found")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=str(record.data.get("email") or user.email),
            display_name=user.display_name,
            password_hash=user.password_hash,
            status=user.status,
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=user.metadata,
        )
        updated = self._persist_meta(updated, {"email_verified": True})
        self.audit.record("email.changed", user_id=user.user_id)
        return {"ok": True, "user": enterprise_user_public_dict(updated)}

    def unlink_provider(self, user_id: str, provider: str) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        meta = dict(user.metadata or {})
        links = list(meta.get("linked_providers") or [])
        target = provider.strip().upper()
        remaining = [lnk for lnk in links if str(lnk.get("provider") or "").upper() != target]
        has_password = bool(user.password_hash)
        has_phone = bool(meta.get("phone_verified") and meta.get("mobile"))
        auth_methods = len(remaining) + (1 if has_password else 0)
        if has_phone and target != "PHONE":
            auth_methods += 1
        if auth_methods < 1:
            raise ValidationError("Cannot unlink the last authentication method.")
        meta["linked_providers"] = remaining
        if target == "PHONE":
            meta["phone_verified"] = False
            meta.pop("mobile", None)
        if str(meta.get("provider") or "").upper() == target:
            meta["provider"] = AuthProvider.EMAIL.value if has_password else (
                remaining[0]["provider"] if remaining else AuthProvider.EMAIL.value
            )
        user = self._persist_meta(user, meta)
        self.audit.record(self._oauth_event(target, "unlink"), user_id=user.user_id, detail=target)
        return enterprise_user_public_dict(user)

    def delete_account(self, user_id: str) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        if "super_admin" in user.roles:
            raise AuthorizationError("Super Admin accounts cannot be self-deleted.")
        updated = self.admin_set_status(user_id, active=False)
        self.devices.revoke_all(user_id)
        return {"ok": True, "user": updated, "message": "Account disabled and sessions revoked."}

    def list_my_devices(self, user_id: str) -> list[dict[str, Any]]:
        return self.devices.list_for_user(user_id)

    def trust_device(self, user_id: str, device_id: str, *, trusted: bool = True) -> dict[str, Any]:
        try:
            return self.devices.set_trusted(device_id, user_id=user_id, trusted=trusted)
        except KeyError as exc:
            raise ValidationError("device not found") from exc

    def revoke_device(self, user_id: str, device_id: str) -> dict[str, Any]:
        try:
            self.devices.revoke(device_id, user_id=user_id)
        except KeyError as exc:
            raise ValidationError("device not found") from exc
        return {"ok": True, "device_id": device_id}

    def my_login_history(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return self.login_history(user_id, limit=limit)

    def admin_provision_user(
        self,
        *,
        name: str,
        email: str,
        username: str | None = None,
        password: str | None = None,
        roles: list[str] | None = None,
        actor_roles: list[str] | None = None,
    ) -> dict[str, Any]:
        mapped = [_normalize_role(r) for r in (roles or ["read_only"])]
        if "super_admin" in mapped and "super_admin" not in (actor_roles or []):
            raise AuthorizationError("Only Super Admin can assign super_admin.")
        mail = email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        uname = (username or mail.split("@", 1)[0]).strip().lower()
        uname = re.sub(r"[^a-z0-9._-]", "", uname)[:64] or f"user_{secrets.token_hex(3)}"
        pwd = password or secrets.token_urlsafe(16) + "Aa1!"
        user = self.auth.users.create(
            username=uname,
            email=mail,
            password=pwd,
            display_name=name.strip() or uname,
            roles=mapped,
        )
        user = self._persist_meta(
            user,
            {
                "provider": AuthProvider.EMAIL.value,
                "email_verified": True,
                "requires_email_verification": False,
                "provisioned": True,
            },
        )
        out: dict[str, Any] = {"ok": True, "user": enterprise_user_public_dict(user)}
        if password is None:
            env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
            if env not in {"production", "prod"}:
                out["temporary_password"] = pwd
        return out

    def admin_unlock_user(self, user_id: str) -> dict[str, Any]:
        user = self.auth.users.get(user_id)
        if user is None:
            raise ValidationError("user not found")
        meta = dict(user.metadata or {})
        meta["failed_login_count"] = 0
        meta.pop("locked_until", None)
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            password_hash=user.password_hash,
            status="active",
            created_at=user.created_at,
            updated_at=utc_now().isoformat(),
            last_login=user.last_login,
            roles=user.roles,
            metadata=freeze_mapping(meta),
        )
        self.auth.users.save(updated)
        return enterprise_user_public_dict(updated)

    def revoke_sessions_for_user(self, user_id: str) -> dict[str, Any]:
        count = 0
        for session in self.auth.sessions.list_sessions(user_id=user_id):
            try:
                self.auth.sessions.revoke(session.session_id)
                count += 1
            except Exception:  # noqa: BLE001
                pass
        devices = self.devices.revoke_all(user_id)
        if count:
            self.audit.record(
                "session.revoked", user_id=user_id, detail=f"admin_revoke_all:{count}"
            )
        return {"ok": True, "sessions_revoked": count, "devices_revoked": devices}

    def admin_revoke_sessions(self, user_id: str) -> dict[str, Any]:
        return self.revoke_sessions_for_user(user_id)

    def refresh_session(
        self,
        *,
        refresh_token: str,
        created_at: str | None = None,
        access_jti: str | None = None,
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
    ) -> dict[str, Any]:
        """Rotate a refresh token with reuse detection — platform-level entry point.

        Thin bridge over :meth:`AuthenticationService.refresh`. Reuses the
        existing A009 session store (no duplicate token storage — the
        rotation state lives on the same ``auth-session-*`` record already
        used for everything else) and this platform's shared
        :class:`~auth.audit.AuditLogger`, which is wired onto
        ``self.auth.authentication`` in ``__init__``. Existing callers of
        the lower-level ``AuthService.refresh`` / ``/auth/rbac/refresh``
        continue to work unchanged and get the same rotation and reuse
        detection guarantees, since both paths share one
        ``AuthenticationService`` instance.
        """
        return self.auth.authentication.refresh(
            refresh_token=refresh_token,
            created_at=created_at,
            access_jti=access_jti,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )

    def require_admin(self, access_token: str) -> dict[str, Any]:
        user = self.auth.current_user(access_token)
        roles = set(user.get("roles") or [])
        if "super_admin" not in roles and "administrator" not in roles:
            try:
                self.auth.require_permission(user, "manage_users")
            except AuthorizationError as exc:
                raise AuthorizationError("administrator access required") from exc
        return user


_PLATFORM: EnterpriseAuthPlatform | None = None


def get_enterprise_auth_platform(auth: AuthService | None = None) -> EnterpriseAuthPlatform:
    global _PLATFORM
    if _PLATFORM is None:
        _PLATFORM = EnterpriseAuthPlatform(auth or get_auth_service())
    return _PLATFORM


def reset_enterprise_auth_platform_for_tests(
    platform: EnterpriseAuthPlatform | None = None,
) -> None:
    global _PLATFORM
    _PLATFORM = platform
