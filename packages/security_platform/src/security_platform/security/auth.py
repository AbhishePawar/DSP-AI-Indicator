"""Authentication / authorization managers and OAuth2-ready ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from security_platform.security.api_keys import ApiKeyManager
from security_platform.security.audit import AuditLogger
from security_platform.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from security_platform.security.jwt import JWTManager
from security_platform.security.permissions import Permission, assert_permission
from security_platform.security.rate_limit import RateLimitConfig, RateLimiter
from security_platform.security.roles import Role, RoleManager
from security_platform.security.users import (
    PermissionManager,
    SecurityContext,
    UserPrincipal,
    UserRecord,
    UserStore,
)

__all__ = [
    "AuthenticationManager",
    "AuthorizationManager",
    "OAuth2TokenValidator",
    "SecurityBundle",
    "SecuritySettings",
]


@runtime_checkable
class OAuth2TokenValidator(Protocol):
    """OAuth2-ready interface — adapters validate opaque / IdP tokens."""

    def validate_access_token(self, token: str) -> UserPrincipal:
        """Return a principal for a validated access token."""


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    """Immutable security configuration for API composition."""

    jwt_secret: str = "dev-only-change-me"
    jwt_issuer: str = "dsp-security"
    jwt_audience: str = "dsp-api"
    jwt_ttl_seconds: int = 3600
    allow_guest: bool = False
    require_auth: bool = True
    public_paths: tuple[str, ...] = (
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/auth/login",
        "/api/v1/auth/login",
        "/platform",
        "/api/v1/platform",
    )
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)


@dataclass
class SecurityBundle:
    """Composition root for security services — injected into the API layer."""

    settings: SecuritySettings
    users: UserStore
    jwt: JWTManager
    api_keys: ApiKeyManager
    roles: RoleManager
    permissions: PermissionManager
    authentication: AuthenticationManager
    authorization: AuthorizationManager
    audit: AuditLogger
    rate_limiter: RateLimiter

    @classmethod
    def create(
        cls,
        settings: SecuritySettings | None = None,
        *,
        seed_admin: bool = True,
    ) -> SecurityBundle:
        """Build a default in-memory security bundle."""
        cfg = settings or SecuritySettings()
        users = UserStore()
        jwt = JWTManager(
            secret=cfg.jwt_secret,
            issuer=cfg.jwt_issuer,
            audience=cfg.jwt_audience,
            default_ttl_seconds=cfg.jwt_ttl_seconds,
        )
        api_keys = ApiKeyManager()
        roles = RoleManager()
        permissions = PermissionManager()
        audit = AuditLogger()
        rate_limiter = RateLimiter(cfg.rate_limit)
        authentication = AuthenticationManager(
            users=users,
            jwt=jwt,
            api_keys=api_keys,
            permissions=permissions,
            allow_guest=cfg.allow_guest,
            oauth2_validator=None,
        )
        authorization = AuthorizationManager()
        bundle = cls(
            settings=cfg,
            users=users,
            jwt=jwt,
            api_keys=api_keys,
            roles=roles,
            permissions=permissions,
            authentication=authentication,
            authorization=authorization,
            audit=audit,
            rate_limiter=rate_limiter,
        )
        if seed_admin:
            users.add(
                UserRecord(
                    user_id="usr_admin",
                    username="admin",
                    role=Role.ADMIN,
                    display_name="Platform Admin",
                )
            )
        return bundle


class AuthenticationManager:
    """Authenticate JWT, API keys, optional OAuth2, or guest."""

    def __init__(
        self,
        *,
        users: UserStore,
        jwt: JWTManager,
        api_keys: ApiKeyManager,
        permissions: PermissionManager,
        allow_guest: bool = False,
        oauth2_validator: OAuth2TokenValidator | None = None,
    ) -> None:
        self._users = users
        self._jwt = jwt
        self._api_keys = api_keys
        self._permissions = permissions
        self._allow_guest = allow_guest
        self._oauth2 = oauth2_validator

    @property
    def allow_guest(self) -> bool:
        return self._allow_guest

    def authenticate_jwt(self, token: str) -> UserPrincipal:
        claims = self._jwt.verify(token)
        permissions: frozenset[Permission]
        username = claims.username
        try:
            user = self._users.get(claims.subject)
            if not user.active:
                msg = f"user inactive: {claims.subject!r}"
                raise AuthenticationError(msg)
            permissions = self._permissions.permissions_for_user(user)
            username = user.username
            role = user.role
        except AuthenticationError:
            raise
        except Exception:
            # Token may carry role without a local user record (stateless JWT).
            from security_platform.security.roles import ROLE_PERMISSIONS

            role = claims.role
            permissions = ROLE_PERMISSIONS[role]
        return UserPrincipal(
            subject=claims.subject,
            role=role,
            permissions=permissions,
            auth_method="jwt",
            username=username,
        )

    def authenticate_api_key(self, key_id: str, secret: str) -> UserPrincipal:
        record = self._api_keys.verify(key_id, secret)
        from security_platform.security.roles import ROLE_PERMISSIONS

        return UserPrincipal(
            subject=record.owner_user_id or record.key_id,
            role=record.role,
            permissions=ROLE_PERMISSIONS[record.role],
            auth_method="api_key",
            api_key_id=record.key_id,
        )

    def authenticate_api_key_bearer(self, token: str) -> UserPrincipal:
        record = self._api_keys.verify_bearer(token)
        from security_platform.security.roles import ROLE_PERMISSIONS

        return UserPrincipal(
            subject=record.owner_user_id or record.key_id,
            role=record.role,
            permissions=ROLE_PERMISSIONS[record.role],
            auth_method="api_key",
            api_key_id=record.key_id,
        )

    def authenticate_oauth2(self, access_token: str) -> UserPrincipal:
        if self._oauth2 is None:
            msg = "OAuth2 validator is not configured"
            raise AuthenticationError(msg)
        return self._oauth2.validate_access_token(access_token)

    def guest_principal(self) -> UserPrincipal:
        if not self._allow_guest:
            msg = "guest mode is disabled"
            raise AuthenticationError(msg)
        from security_platform.security.roles import ROLE_PERMISSIONS

        return UserPrincipal(
            subject="guest",
            role=Role.GUEST,
            permissions=ROLE_PERMISSIONS[Role.GUEST],
            auth_method="guest",
            username="guest",
        )

    def authenticate_headers(
        self,
        *,
        authorization: str | None = None,
        api_key_id: str | None = None,
        api_key_secret: str | None = None,
    ) -> UserPrincipal:
        """Resolve a principal from HTTP auth headers."""
        if api_key_id and api_key_secret:
            return self.authenticate_api_key(api_key_id, api_key_secret)

        if authorization:
            scheme, _, material = authorization.partition(" ")
            scheme_l = scheme.strip().lower()
            token = material.strip()
            if not token:
                msg = "empty authorization material"
                raise AuthenticationError(msg)
            if scheme_l == "bearer":
                # Prefer JWT; fall back to API key bearer; then OAuth2 port.
                try:
                    return self.authenticate_jwt(token)
                except Exception:
                    try:
                        return self.authenticate_api_key_bearer(token)
                    except Exception:
                        if self._oauth2 is not None:
                            return self.authenticate_oauth2(token)
                        raise
            if scheme_l == "apikey":
                return self.authenticate_api_key_bearer(token)
            msg = f"unsupported authorization scheme: {scheme!r}"
            raise AuthenticationError(msg)

        return self.guest_principal()

    def build_context(
        self,
        principal: UserPrincipal,
        *,
        request_id: str | None = None,
    ) -> SecurityContext:
        return SecurityContext(
            principal=principal,
            authenticated=principal.auth_method != "guest",
            guest=principal.auth_method == "guest",
            request_id=request_id,
        )


class AuthorizationManager:
    """Permission checks against a security context / principal."""

    def check(
        self,
        principal: UserPrincipal,
        permission: Permission | str,
    ) -> None:
        perm = assert_permission(permission)
        if not principal.has_permission(perm):
            msg = (
                f"permission denied: {perm.value} "
                f"(role={principal.role.value})"
            )
            raise AuthorizationError(msg)

    def is_allowed(
        self,
        principal: UserPrincipal,
        permission: Permission | str,
    ) -> bool:
        try:
            self.check(principal, permission)
            return True
        except AuthorizationError:
            return False
