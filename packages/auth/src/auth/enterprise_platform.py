"""Enterprise multi-provider authentication platform — extends A009 AuthService."""

from __future__ import annotations

import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from auth.devices import DeviceRegistry
from auth.email_delivery import EmailProviderPort, build_email_provider
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
from auth.otp import OtpService
from auth.service import AuthService, get_auth_service
from auth.sms import build_sms_provider

__all__ = [
    "EnterpriseAuthPlatform",
    "get_enterprise_auth_platform",
    "reset_enterprise_auth_platform_for_tests",
    "password_strength",
]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ACCESS_PREFIX = "auth-access-"
_HISTORY_PREFIX = "auth-login-hist-"
_VERIFY_PREFIX = "auth-email-verify-"
_RESET_PREFIX = "auth-pwd-reset-"
_MAGIC_PREFIX = "auth-magic-"
_INVITE_PREFIX = "auth-invite-"


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
    ) -> None:
        self.auth = auth
        self.oauth = oauth or build_oauth_registry()
        self.otp = otp or OtpService(build_sms_provider())
        self.devices = devices or DeviceRegistry(auth.persistence)
        self.mfa = mfa or build_mfa_gateway()
        self.email = email or build_email_provider()
        self._verify_tokens: dict[str, dict[str, Any]] = {}
        self._reset_tokens: dict[str, dict[str, Any]] = {}
        self._magic_tokens: dict[str, dict[str, Any]] = {}
        self._email_change_tokens: dict[str, dict[str, Any]] = {}
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
                "google_oauth": True,
                "microsoft_oauth": True,
                "facebook_oauth": True,
                "mobile_otp": True,
                "magic_link": True,
                "request_access": True,
                "email_verification": True,
                "password_reset": True,
                "remember_me": True,
                "login_history": True,
                "device_tracking": True,
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
        magic_enabled = (os.environ.get("DSP_AUTH_MAGIC_LINK") or "false").strip().lower() in {
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

    def _get_by_email(self, email: str) -> AuthUser | None:
        target = email.strip().lower()
        for user in self.auth.users.list_users():
            if user.email.casefold() == target:
                return user
        return None

    def _get_by_mobile(self, mobile: str) -> AuthUser | None:
        for user in self.auth.users.list_users():
            meta = dict(user.metadata or {})
            if str(meta.get("mobile") or "") == mobile:
                return user
        return None

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
            device_trusted=bool(device.trusted),
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
            "session": session.to_dict(),
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
        token = secrets.token_urlsafe(32)
        self._verify_tokens[token] = {
            "user_id": pending.user_id,
            "expires_at": (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat(),
        }
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_VERIFY_PREFIX}{token}",
            payload={"token": token, "user_id": pending.user_id, "auth_entity": "email_verify"},
            refs={"auth_entity": "email_verify"},
            created_at=utc_now().isoformat(),
            allow_update=True,
        )
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
        meta = self._verify_tokens.get(token)
        if meta is None:
            row = self.auth.persistence.get("metadata", f"{_VERIFY_PREFIX}{token}")
            if row:
                meta = row.get("payload") or {}
        if not meta:
            raise ValidationError("Invalid or expired verification token.")
        user = self.auth.users.get(str(meta["user_id"]))
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
        self._verify_tokens.pop(token, None)
        return {"ok": True, "user": enterprise_user_public_dict(activated)}

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
        self._rate_check(f"login:{ip_hint or identifier}", limit=20, window_sec=300)
        ident = identifier.strip()
        user = None
        if "@" in ident:
            user = self._get_by_email(ident)
        if user is None:
            user = self.auth.users.get_by_username(ident)
        provider = AuthProvider.EMAIL.value if "@" in ident else AuthProvider.USERNAME.value
        if user is None or not verify_password(password, user.password_hash):
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
        token = secrets.token_urlsafe(32)
        self._reset_tokens[token] = {
            "user_id": user.user_id,
            "expires_at": (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_RESET_PREFIX}{token}",
            payload={"token": token, "user_id": user.user_id, "auth_entity": "password_reset"},
            refs={"auth_entity": "password_reset"},
            created_at=utc_now().isoformat(),
            allow_update=True,
        )
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env not in {"production", "prod"}:
            out["reset_token"] = token
        return out

    def confirm_password_reset(self, token: str, new_password: str) -> dict[str, Any]:
        strength = password_strength(new_password)
        if strength["score"] < 4:
            raise ValidationError("password is too weak")
        meta = self._reset_tokens.get(token)
        if meta is None:
            row = self.auth.persistence.get("metadata", f"{_RESET_PREFIX}{token}")
            if row:
                meta = row.get("payload") or {}
        if not meta:
            raise ValidationError("Invalid or expired reset token.")
        user = self.auth.users.get(str(meta["user_id"]))
        if user is None:
            raise ValidationError("User not found.")
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
        self._reset_tokens.pop(token, None)
        # Revoke sessions
        for session in self.auth.sessions.list_sessions(user_id=user.user_id):
            try:
                self.auth.sessions.revoke(session.session_id)
            except Exception:  # noqa: BLE001
                pass
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
        profile = self.oauth.complete(
            provider, code=code, state=state, redirect_uri=redirect_uri
        )
        return self._login_from_oauth_profile(
            profile,
            remember_me=remember_me,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )

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
                meta = dict(user.metadata or {})
                links = list(meta.get("linked_providers") or [])
                links.append(
                    {
                        "provider": profile.provider,
                        "provider_subject": profile.subject,
                        "email": profile.email,
                        "linked_at": utc_now().isoformat(),
                    }
                )
                user = self._persist_meta(
                    user,
                    {
                        "linked_providers": links,
                        "avatar": profile.avatar or meta.get("avatar"),
                        "email_verified": True,
                        "requires_email_verification": False,
                    },
                )
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
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=profile.provider,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label=f"oauth:{profile.provider.lower()}",
        )

    # --- OTP -------------------------------------------------------------

    def request_mobile_otp(self, mobile: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._rate_check(f"otp:{ip_hint or mobile}", limit=10, window_sec=3600)
        otp_flag = (os.environ.get("DSP_AUTH_PROVIDER_OTP") or "auto").strip().lower()
        if otp_flag in {"disabled", "coming_soon", "off", "false", "0"}:
            raise AuthenticationError("Mobile OTP intentionally disabled — Coming Soon.")
        return self.otp.request_otp(mobile, ip_hint=ip_hint)

    def resend_mobile_otp(self, mobile: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        """Resend uses the same request path (enforces 30s cooldown)."""
        return self.request_mobile_otp(mobile, ip_hint=ip_hint)

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
        mobile = self.otp.verify_otp(challenge_id=challenge_id, code=code, ip_hint=ip_hint)
        user = self._get_by_mobile(mobile)
        if user is None:
            # Auto-create phone user
            uname = f"m{mobile[-10:]}"
            email = f"{uname}@phone.dspai.local"
            try:
                created = self.auth.users.create(
                    username=uname,
                    email=email,
                    password=secrets.token_urlsafe(24),
                    display_name=name or f"Mobile {mobile[-4:]}",
                    roles=["read_only"],
                )
            except DuplicateUserError:
                created = self.auth.users.get_by_username(uname)
                if created is None:
                    raise
            user = self._persist_meta(
                created,
                {
                    "provider": AuthProvider.PHONE.value,
                    "mobile": mobile,
                    "phone_verified": True,
                    "email_verified": False,
                    "requires_email_verification": False,
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
        else:
            user = self._persist_meta(user, {"phone_verified": True, "mobile": mobile})
        return self._issue_session(
            user,
            remember_me=remember_me,
            provider=AuthProvider.PHONE.value,
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
            device_label="mobile-otp",
        )

    # --- Magic link ------------------------------------------------------

    def request_magic_link(self, email: str, *, ip_hint: str | None = None) -> dict[str, Any]:
        self._rate_check(f"magic:{ip_hint or email}", limit=5, window_sec=3600)
        mail = email.strip().lower()
        if not _EMAIL_RE.match(mail):
            raise ValidationError("invalid email")
        token = secrets.token_urlsafe(32)
        self._magic_tokens[token] = {
            "email": mail,
            "expires_at": (datetime.now(tz=timezone.utc) + timedelta(minutes=15)).isoformat(),
        }
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_MAGIC_PREFIX}{token}",
            payload={"token": token, "email": mail, "auth_entity": "magic_link"},
            refs={"auth_entity": "magic_link"},
            created_at=utc_now().isoformat(),
            allow_update=True,
        )
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
        meta = self._magic_tokens.pop(token, None)
        if meta is None:
            row = self.auth.persistence.get("metadata", f"{_MAGIC_PREFIX}{token}")
            if row:
                meta = row.get("payload") or {}
        if not meta:
            raise AuthenticationError("Invalid or expired magic link.")
        expires = meta.get("expires_at")
        if expires:
            exp = datetime.fromisoformat(str(expires))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(tz=timezone.utc) > exp:
                raise AuthenticationError("Magic link expired.")
        email = str(meta["email"]).lower()
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

        invite_token = secrets.token_urlsafe(24)
        mapped_role = _normalize_role(role)
        payload.update(
            {
                "status": "invited",
                "updated_at": now,
                "decided_by": actor_user_id,
                "notes": notes,
                "invitation_token": invite_token,
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
        self.auth.persistence.put(
            kind="metadata",
            entity_id=f"{_INVITE_PREFIX}{invite_token}",
            payload={
                "token": invite_token,
                "request_id": request_id,
                "email": payload["email"],
                "name": payload["name"],
                "role": mapped_role,
                "auth_entity": "invitation",
            },
            refs={"auth_entity": "invitation"},
            created_at=now,
            allow_update=True,
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
        row = self.auth.persistence.get("metadata", f"{_INVITE_PREFIX}{token}")
        if row is None:
            raise ValidationError("Invalid invitation token.")
        invite = row.get("payload") or {}
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
            },
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
            for session in self.auth.sessions.list_sessions(user_id=user_id):
                try:
                    self.auth.sessions.revoke(session.session_id)
                except Exception:  # noqa: BLE001
                    pass
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
        return [s.to_dict() if hasattr(s, "to_dict") else dict(s) for s in sessions if not getattr(s, "revoked", False)]

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
        token = secrets.token_urlsafe(32)
        self._email_change_tokens[token] = {
            "user_id": user_id,
            "email": mail,
            "expires_at": (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat(),
        }
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
        meta = self._email_change_tokens.pop(token, None)
        if not meta:
            raise ValidationError("Invalid or expired email change token.")
        user = self.auth.users.get(str(meta["user_id"]))
        if user is None:
            raise ValidationError("user not found")
        updated = AuthUser(
            user_id=user.user_id,
            username=user.username,
            email=str(meta["email"]),
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
        return {"ok": True, "sessions_revoked": count, "devices_revoked": devices}

    def admin_revoke_sessions(self, user_id: str) -> dict[str, Any]:
        return self.revoke_sessions_for_user(user_id)

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
