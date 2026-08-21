"""Env-gated OAuth providers (Google / Microsoft / Facebook) with PKCE."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Any

from auth.credential_boundary import GOOGLE_CLIENT_ID_ENV, GOOGLE_CLIENT_SECRET_ENV
from auth.enterprise_models import AuthProvider, ProviderUiStatus
from auth.exceptions import AuthenticationError, ValidationError
from auth.oidc import OidcVerificationUnavailable, verify_id_token

logger = logging.getLogger(__name__)

__all__ = [
    "OAuthProfile",
    "OAuthProviderAdapter",
    "OAuthProviderRegistry",
    "build_oauth_registry",
    "stable_username_from_email",
]


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


@dataclass(frozen=True, slots=True)
class OAuthProfile:
    provider: str
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    avatar: str | None
    raw_claims: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "subject": self.subject,
            "email": self.email,
            "email_verified": self.email_verified,
            "name": self.name,
            "avatar": self.avatar,
        }


class OAuthProviderAdapter:
    def __init__(
        self,
        *,
        provider: AuthProvider,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
        userinfo_url: str,
        scopes: tuple[str, ...],
        flag_env: str,
        oidc_jwks_uri: str | None = None,
        oidc_issuers: tuple[str, ...] = (),
    ) -> None:
        self.provider = provider
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.scopes = scopes
        self.flag_env = flag_env
        self.oidc_jwks_uri = oidc_jwks_uri
        self.oidc_issuers = oidc_issuers
        self._states: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def provider_name(self) -> str:
        return self.provider.value

    def _flag(self) -> str:
        return (os.environ.get(self.flag_env) or "auto").strip().lower()

    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def is_available(self) -> bool:
        return self.ui_status() == ProviderUiStatus.AVAILABLE.value

    def ui_status(self) -> str:
        flag = self._flag()
        if flag in {"disabled", "coming_soon", "off", "false", "0"}:
            return ProviderUiStatus.COMING_SOON.value
        if not self.has_credentials():
            return ProviderUiStatus.UNAVAILABLE.value
        return ProviderUiStatus.AVAILABLE.value

    def status(self) -> dict[str, Any]:
        status = self.ui_status()
        messages = {
            ProviderUiStatus.AVAILABLE.value: None,
            ProviderUiStatus.UNAVAILABLE.value: (
                f"{self.provider_name()} OAuth unavailable — credentials not configured."
            ),
            ProviderUiStatus.COMING_SOON.value: (
                f"{self.provider_name()} intentionally disabled — Coming Soon."
            ),
        }
        return {
            "id": self.provider_name().lower(),
            "provider": self.provider_name(),
            "status": status,
            "available": status == ProviderUiStatus.AVAILABLE.value,
            "message": messages[status],
        }

    def begin_login(self, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        status = self.ui_status()
        if status != ProviderUiStatus.AVAILABLE.value:
            return {
                "available": False,
                "status": status,
                "provider": self.provider_name(),
                "authorization_url": None,
                "message": self.status()["message"],
                "state": None,
            }
        st = state or secrets.token_urlsafe(24)
        verifier, challenge = _pkce_pair()
        nonce = secrets.token_urlsafe(24) if self.oidc_jwks_uri else None
        with self._lock:
            self._states[st] = {
                "redirect_uri": redirect_uri,
                "code_verifier": verifier,
                "nonce": nonce,
            }
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": st,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "access_type": "online",
            "prompt": "select_account",
        }
        if nonce:
            params["nonce"] = nonce
        if self.provider == AuthProvider.MICROSOFT:
            params.pop("access_type", None)
            params["response_mode"] = "query"
        if self.provider == AuthProvider.FACEBOOK:
            # Facebook supports PKCE on some app configs; still send challenge.
            params.pop("access_type", None)
            params.pop("prompt", None)
        url = f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
        return {
            "available": True,
            "status": status,
            "provider": self.provider_name(),
            "authorization_url": url,
            "state": st,
            "message": None,
        }

    def complete_login(self, *, code: str, state: str | None, redirect_uri: str) -> OAuthProfile:
        if self.ui_status() != ProviderUiStatus.AVAILABLE.value:
            raise AuthenticationError(
                f"{self.provider_name()} OAuth unavailable — credentials not configured."
            )
        with self._lock:
            meta = self._states.pop(state or "", None)
        if meta is None:
            raise AuthenticationError("Invalid or expired OAuth state.")
        expected_redirect = str(meta.get("redirect_uri") or redirect_uri)
        verifier = str(meta.get("code_verifier") or "")
        nonce = meta.get("nonce")
        token_payload = self._exchange_code(code, expected_redirect, verifier)
        access = str(token_payload.get("access_token") or "")
        if not access:
            raise AuthenticationError("OAuth token exchange failed.")
        id_claims = self._verify_id_token(token_payload, nonce)
        return self._fetch_profile(access, token_payload, id_claims)

    def _verify_id_token(
        self, token_payload: dict[str, Any], nonce: str | None
    ) -> dict[str, Any] | None:
        """Best-effort additive verification of the token endpoint's ``id_token``.

        Returns decoded+verified claims, or ``None`` when verification could
        not be attempted (missing token, missing ``cryptography`` dependency,
        unsupported key type, or JWKS fetch failure) — callers must continue
        to trust the existing userinfo-based flow in that case. Raises
        :class:`AuthenticationError` when a token IS present and IS
        cryptographically checkable but fails validation (bad signature,
        issuer, audience, or nonce) — that is a genuine attack signal.
        """
        id_token = token_payload.get("id_token")
        if not id_token or not self.oidc_jwks_uri or not self.oidc_issuers:
            return None
        try:
            return verify_id_token(
                str(id_token),
                jwks_uri=self.oidc_jwks_uri,
                issuer=self.oidc_issuers,
                audience=self.client_id,
                nonce=nonce,
            )
        except OidcVerificationUnavailable as exc:
            logger.debug("%s id_token verification skipped: %s", self.provider_name(), exc)
            return None
        except ValueError as exc:
            raise AuthenticationError(f"{self.provider_name()} id_token rejected: {exc}") from exc

    def _exchange_code(self, code: str, redirect_uri: str, code_verifier: str) -> dict[str, Any]:
        form = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        if code_verifier:
            form["code_verifier"] = code_verifier
        data = urllib.parse.urlencode(form).encode("utf-8")
        req = urllib.request.Request(
            self.token_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise AuthenticationError(f"OAuth token exchange failed: {body}") from exc
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationError(f"OAuth token exchange failed: {exc}") from exc

    def _fetch_profile(
        self,
        access_token: str,
        token_payload: dict[str, Any],
        id_claims: dict[str, Any] | None = None,
    ) -> OAuthProfile:
        _ = token_payload
        if self.provider == AuthProvider.FACEBOOK:
            fields = "id,name,first_name,last_name,email,picture.type(large),locale"
            url = f"{self.userinfo_url}?{urllib.parse.urlencode({'fields': fields})}"
        else:
            url = self.userinfo_url
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                claims = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AuthenticationError(f"OAuth userinfo failed: {exc}") from exc

        if self.provider == AuthProvider.GOOGLE:
            email = claims.get("email")
            profile = OAuthProfile(
                provider=self.provider_name(),
                subject=str(claims.get("sub") or ""),
                email=str(email).strip().lower() if email else None,
                email_verified=bool(claims.get("email_verified")),
                name=claims.get("name"),
                avatar=claims.get("picture"),
                raw_claims=claims,
            )
            if id_claims is not None:
                id_sub = str(id_claims.get("sub") or "")
                if id_sub and id_sub != profile.subject:
                    raise AuthenticationError(
                        "Google id_token subject does not match userinfo response."
                    )
                id_email = id_claims.get("email")
                if id_email and profile.email and str(id_email).strip().lower() != profile.email:
                    raise AuthenticationError(
                        "Google id_token email does not match userinfo response."
                    )
            return profile
        if self.provider == AuthProvider.MICROSOFT:
            email = claims.get("mail") or claims.get("userPrincipalName") or claims.get("email")
            profile = OAuthProfile(
                provider=self.provider_name(),
                subject=str(claims.get("id") or claims.get("sub") or ""),
                email=str(email).strip().lower() if email else None,
                email_verified=bool(email),
                name=claims.get("displayName") or claims.get("name"),
                avatar=None,
                raw_claims=claims,
            )
            if id_claims is not None:
                id_oid = str(id_claims.get("oid") or id_claims.get("sub") or "")
                if id_oid and id_oid != profile.subject:
                    raise AuthenticationError(
                        "Microsoft id_token subject does not match Graph profile."
                    )
            return profile
        if self.provider == AuthProvider.FACEBOOK:
            # Facebook's `email` permission only ever returns a confirmed,
            # owner-verified address (or omits the field entirely) — there
            # is no separate "email_verified" claim to cross-check, so
            # presence of the field is itself the verification signal, the
            # same convention already used for Microsoft's Graph `/me`.
            email = claims.get("email")
            first_name = claims.get("first_name")
            last_name = claims.get("last_name")
            display_name = claims.get("name") or " ".join(
                part for part in (first_name, last_name) if part
            ).strip() or None
            picture = None
            pic = claims.get("picture")
            if isinstance(pic, dict):
                picture = (pic.get("data") or {}).get("url")
            subject = str(claims.get("id") or "")
            if not subject:
                raise AuthenticationError("Facebook profile response did not include a user id.")
            return OAuthProfile(
                provider=self.provider_name(),
                subject=subject,
                email=str(email).strip().lower() if email else None,
                email_verified=bool(email),
                name=display_name,
                avatar=picture,
                raw_claims=claims,
            )
        raise AuthenticationError(f"Unsupported OAuth provider {self.provider_name()!r}.")


class OAuthProviderRegistry:
    def __init__(self, adapters: dict[str, OAuthProviderAdapter] | None = None) -> None:
        self._adapters = adapters or {}

    def get(self, provider: str) -> OAuthProviderAdapter | None:
        return self._adapters.get(provider.strip().upper())

    def require(self, provider: str) -> OAuthProviderAdapter:
        adapter = self.get(provider)
        if adapter is None:
            raise ValidationError(f"Unknown OAuth provider {provider!r}")
        return adapter

    def status(self) -> list[dict[str, Any]]:
        return [a.status() for a in self._adapters.values()]

    def begin(self, provider: str, *, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        return self.require(provider).begin_login(redirect_uri=redirect_uri, state=state)

    def complete(
        self,
        provider: str,
        *,
        code: str,
        state: str | None,
        redirect_uri: str,
    ) -> OAuthProfile:
        return self.require(provider).complete_login(
            code=code, state=state, redirect_uri=redirect_uri
        )


def build_oauth_registry() -> OAuthProviderRegistry:
    tenant = os.environ.get("DSP_MICROSOFT_TENANT_ID", "common").strip() or "common"
    adapters = {
        AuthProvider.GOOGLE.value: OAuthProviderAdapter(
            provider=AuthProvider.GOOGLE,
            client_id=os.environ.get(GOOGLE_CLIENT_ID_ENV, ""),
            client_secret=os.environ.get(GOOGLE_CLIENT_SECRET_ENV, ""),
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scopes=("openid", "email", "profile"),
            flag_env="DSP_AUTH_PROVIDER_GOOGLE",
            oidc_jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
            oidc_issuers=("https://accounts.google.com", "accounts.google.com"),
        ),
        AuthProvider.MICROSOFT.value: OAuthProviderAdapter(
            provider=AuthProvider.MICROSOFT,
            client_id=os.environ.get("DSP_MICROSOFT_CLIENT_ID", ""),
            client_secret=os.environ.get("DSP_MICROSOFT_CLIENT_SECRET", ""),
            authorize_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            scopes=("openid", "email", "profile", "User.Read"),
            flag_env="DSP_AUTH_PROVIDER_MICROSOFT",
            oidc_jwks_uri=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
            oidc_issuers=(
                f"https://login.microsoftonline.com/{tenant}/v2.0",
                "https://login.microsoftonline.com/*/v2.0",
            ),
        ),
        AuthProvider.FACEBOOK.value: OAuthProviderAdapter(
            provider=AuthProvider.FACEBOOK,
            # DSP_FACEBOOK_CLIENT_ID/SECRET is the canonical name (matches
            # Google/Microsoft's DSP_<PROVIDER>_CLIENT_ID/SECRET convention);
            # DSP_FACEBOOK_APP_ID/SECRET (Meta's own terminology) is kept as
            # a fallback for backward compatibility with existing deployments.
            client_id=(
                os.environ.get("DSP_FACEBOOK_CLIENT_ID")
                or os.environ.get("DSP_FACEBOOK_APP_ID", "")
            ),
            client_secret=(
                os.environ.get("DSP_FACEBOOK_CLIENT_SECRET")
                or os.environ.get("DSP_FACEBOOK_APP_SECRET", "")
            ),
            authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
            token_url="https://graph.facebook.com/v19.0/oauth/access_token",
            userinfo_url="https://graph.facebook.com/me",
            scopes=("email", "public_profile"),
            flag_env="DSP_AUTH_PROVIDER_FACEBOOK",
        ),
    }
    return OAuthProviderRegistry(adapters)


def stable_username_from_email(email: str, provider: str) -> str:
    local = email.split("@", 1)[0]
    cleaned = "".join(ch for ch in local.lower() if ch.isalnum() or ch in "._-")[:24]
    suffix = hashlib.sha256(f"{provider}:{email}".encode()).hexdigest()[:6]
    base = cleaned or "user"
    return f"{base}_{suffix}"
