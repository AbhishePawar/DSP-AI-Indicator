"""Authentication / authorization managers and OAuth2-ready ports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from security_platform.security.api_keys import ApiKeyManager
from security_platform.security.audit import AuditLogger
from security_platform.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from security_platform.security.identity.india import (
    InMemoryOrganisationStore,
    NullAadhaarPort,
    NullDigiLockerIdentityPort,
    NullEnterpriseKycPort,
    NullMfaPort,
    NullOidcClientPort,
    NullPanVerificationPort,
    NullScimProvisioningPort,
)
from security_platform.security.identity.service import (
    CompositeAudit,
    IdentityService,
    InMemoryAuditStore,
    LockoutPolicy,
)
from security_platform.security.identity.tokens import (
    InMemoryRefreshTokenStore,
    InMemorySessionTracker,
    Pep002SessionTracker,
    TokenService,
)
from security_platform.security.jwt import JWTManager
from security_platform.security.permissions import Permission, assert_permission
from security_platform.security.rate_limit import (
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimiter,
)
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
    refresh_ttl_seconds: int = 7 * 24 * 3600
    remember_me_ttl_seconds: int = 30 * 24 * 3600
    allow_guest: bool = False
    allow_passwordless: bool = True
    require_auth: bool = True
    public_paths: tuple[str, ...] = (
        "/health",
        "/health/live",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/ready",
        "/api/v1/metrics",
        "/auth/login",
        "/api/v1/auth/login",
        "/auth/register",
        "/api/v1/auth/register",
        "/auth/session",
        "/api/v1/auth/session",
        "/auth/forgot-password",
        "/api/v1/auth/forgot-password",
        "/auth/reset-password",
        "/api/v1/auth/reset-password",
        "/auth/verify-email/confirm",
        "/api/v1/auth/verify-email/confirm",
        "/auth/enterprise/schema",
        "/api/v1/auth/enterprise/schema",
        "/auth/enterprise/providers",
        "/api/v1/auth/enterprise/providers",
        "/auth/enterprise/register",
        "/api/v1/auth/enterprise/register",
        "/auth/enterprise/login",
        "/api/v1/auth/enterprise/login",
        "/auth/enterprise/verify-email",
        "/api/v1/auth/enterprise/verify-email",
        "/auth/enterprise/password/forgot",
        "/api/v1/auth/enterprise/password/forgot",
        "/auth/enterprise/password/reset",
        "/api/v1/auth/enterprise/password/reset",
        "/auth/enterprise/otp/request",
        "/api/v1/auth/enterprise/otp/request",
        "/auth/enterprise/otp/verify",
        "/api/v1/auth/enterprise/otp/verify",
        "/auth/enterprise/magic-link/request",
        "/api/v1/auth/enterprise/magic-link/request",
        "/auth/enterprise/magic-link/consume",
        "/api/v1/auth/enterprise/magic-link/consume",
        "/auth/enterprise/oauth/begin",
        "/api/v1/auth/enterprise/oauth/begin",
        "/auth/enterprise/oauth/callback",
        "/api/v1/auth/enterprise/oauth/callback",
        "/auth/refresh",
        "/api/v1/auth/refresh",
        "/auth/rbac/login",
        "/api/v1/auth/rbac/login",
        "/auth/rbac/refresh",
        "/api/v1/auth/rbac/refresh",
        "/auth/rbac/schema",
        "/api/v1/auth/rbac/schema",
        "/platform",
        "/api/v1/platform",
        "/version",
        "/api/v1/version",
        "/capabilities",
        "/api/v1/capabilities",
    )
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    lockout: LockoutPolicy = field(default_factory=LockoutPolicy)


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
    rate_limiter: RateLimiter | DistributedRateLimiter
    identity: IdentityService
    organisations: InMemoryOrganisationStore
    mfa: NullMfaPort
    oidc: NullOidcClientPort
    scim: NullScimProvisioningPort
    pan: NullPanVerificationPort
    digilocker: NullDigiLockerIdentityPort
    aadhaar: NullAadhaarPort
    enterprise_kyc: NullEnterpriseKycPort

    @classmethod
    def create(
        cls,
        settings: SecuritySettings | None = None,
        *,
        seed_admin: bool = True,
        seed_admin_password: str | None = None,
        consent_store: Any | None = None,
    ) -> SecurityBundle:
        """Build a default in-memory security bundle (offline / CI)."""
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
        audit_store = InMemoryAuditStore()
        composite = CompositeAudit(audit, audit_store)
        rate_limiter: RateLimiter | DistributedRateLimiter = RateLimiter(cfg.rate_limit)
        tokens = TokenService(
            jwt=jwt,
            refresh_store=InMemoryRefreshTokenStore(),
            sessions=InMemorySessionTracker(),
            access_ttl_seconds=cfg.jwt_ttl_seconds,
            refresh_ttl_seconds=cfg.refresh_ttl_seconds,
            remember_me_ttl_seconds=cfg.remember_me_ttl_seconds,
        )
        identity = IdentityService(
            users=users,
            tokens=tokens,
            audit=composite,
            lockout=cfg.lockout,
            allow_passwordless=cfg.allow_passwordless,
            consents=consent_store,
        )
        authentication = AuthenticationManager(
            users=users,
            jwt=jwt,
            api_keys=api_keys,
            permissions=permissions,
            allow_guest=cfg.allow_guest,
            oauth2_validator=None,
            identity=identity,
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
            identity=identity,
            organisations=InMemoryOrganisationStore(),
            mfa=NullMfaPort(),
            oidc=NullOidcClientPort(),
            scim=NullScimProvisioningPort(),
            pan=NullPanVerificationPort(),
            digilocker=NullDigiLockerIdentityPort(),
            aadhaar=NullAadhaarPort(),
            enterprise_kyc=NullEnterpriseKycPort(),
        )
        if seed_admin:
            if seed_admin_password:
                identity.provision(
                    user_id="usr_admin",
                    username="admin",
                    role=Role.ADMIN,
                    password=seed_admin_password,
                    display_name="Platform Admin",
                )
            else:
                users.add(
                    UserRecord(
                        user_id="usr_admin",
                        username="admin",
                        role=Role.ADMIN,
                        display_name="Platform Admin",
                    )
                )
        return bundle

    @classmethod
    def create_with_infrastructure(
        cls,
        infrastructure: Any,
        settings: SecuritySettings | None = None,
        *,
        seed_admin: bool = True,
        seed_admin_password: str | None = None,
        consent_store: Any | None = None,
    ) -> SecurityBundle:
        """Wire identity onto PEP-002 InfrastructureBundle ports."""
        from security_platform.security.identity.repository import SqlUserRepository

        cfg = settings or SecuritySettings()
        # Prefer secret from infra when present
        secret = cfg.jwt_secret
        try:
            secret_val = infrastructure.secrets.get_secret("JWT_SECRET")
            if secret_val:
                secret = secret_val
                cfg = SecuritySettings(
                    jwt_secret=secret,
                    jwt_issuer=cfg.jwt_issuer,
                    jwt_audience=cfg.jwt_audience,
                    jwt_ttl_seconds=cfg.jwt_ttl_seconds,
                    refresh_ttl_seconds=cfg.refresh_ttl_seconds,
                    remember_me_ttl_seconds=cfg.remember_me_ttl_seconds,
                    allow_guest=cfg.allow_guest,
                    allow_passwordless=cfg.allow_passwordless,
                    require_auth=cfg.require_auth,
                    public_paths=cfg.public_paths,
                    rate_limit=cfg.rate_limit,
                    lockout=cfg.lockout,
                )
        except Exception:
            pass

        repo = SqlUserRepository(infrastructure.database)
        users = UserStore(repository=repo)
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
        composite = CompositeAudit(audit, InMemoryAuditStore())
        rate_limiter: RateLimiter | DistributedRateLimiter = DistributedRateLimiter(
            infrastructure.rate_limit, cfg.rate_limit
        )
        tokens = TokenService(
            jwt=jwt,
            refresh_store=InMemoryRefreshTokenStore(),
            sessions=Pep002SessionTracker(infrastructure.session),
            access_ttl_seconds=cfg.jwt_ttl_seconds,
            refresh_ttl_seconds=cfg.refresh_ttl_seconds,
            remember_me_ttl_seconds=cfg.remember_me_ttl_seconds,
        )
        identity = IdentityService(
            users=users,
            tokens=tokens,
            audit=composite,
            lockout=cfg.lockout,
            rate_limit_port=infrastructure.rate_limit,
            allow_passwordless=cfg.allow_passwordless,
            consents=consent_store,
        )
        authentication = AuthenticationManager(
            users=users,
            jwt=jwt,
            api_keys=api_keys,
            permissions=permissions,
            allow_guest=cfg.allow_guest,
            identity=identity,
        )
        bundle = cls(
            settings=cfg,
            users=users,
            jwt=jwt,
            api_keys=api_keys,
            roles=roles,
            permissions=permissions,
            authentication=authentication,
            authorization=AuthorizationManager(),
            audit=audit,
            rate_limiter=rate_limiter,
            identity=identity,
            organisations=InMemoryOrganisationStore(),
            mfa=NullMfaPort(),
            oidc=NullOidcClientPort(),
            scim=NullScimProvisioningPort(),
            pan=NullPanVerificationPort(),
            digilocker=NullDigiLockerIdentityPort(),
            aadhaar=NullAadhaarPort(),
            enterprise_kyc=NullEnterpriseKycPort(),
        )
        if seed_admin and users.repository.get_by_username("admin") is None:
            if seed_admin_password:
                identity.provision(
                    user_id="usr_admin",
                    username="admin",
                    role=Role.ADMIN,
                    password=seed_admin_password,
                    display_name="Platform Admin",
                )
            else:
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
    """Authenticate JWT, API keys, optional OAuth2, password, or guest."""

    def __init__(
        self,
        *,
        users: UserStore,
        jwt: JWTManager,
        api_keys: ApiKeyManager,
        permissions: PermissionManager,
        allow_guest: bool = False,
        oauth2_validator: OAuth2TokenValidator | None = None,
        identity: IdentityService | None = None,
    ) -> None:
        self._users = users
        self._jwt = jwt
        self._api_keys = api_keys
        self._permissions = permissions
        self._allow_guest = allow_guest
        self._oauth2 = oauth2_validator
        self._identity = identity

    @property
    def allow_guest(self) -> bool:
        return self._allow_guest

    @property
    def identity(self) -> IdentityService | None:
        return self._identity

    def authenticate_jwt(self, token: str) -> UserPrincipal:
        claims = self._jwt.verify(token)
        permissions: frozenset[Permission]
        username = claims.username
        try:
            user = self._users.get(claims.subject)
            if not user.active:
                raise AuthenticationError(f"user inactive: {claims.subject!r}")
            permissions = self._permissions.permissions_for_user(user)
            username = user.username
            role = user.role
        except AuthenticationError:
            raise
        except Exception:
            from security_platform.security.roles import ROLE_PERMISSIONS

            role = claims.role
            permissions = ROLE_PERMISSIONS[role]
        session_id = None
        if claims.extra and isinstance(claims.extra, dict):
            session_id = claims.extra.get("sid")
        return UserPrincipal(
            subject=claims.subject,
            role=role,
            permissions=permissions,
            auth_method="jwt",
            username=username,
            session_id=str(session_id) if session_id else None,
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
            raise AuthenticationError("OAuth2 validator is not configured")
        return self._oauth2.validate_access_token(access_token)

    def guest_principal(self) -> UserPrincipal:
        if not self._allow_guest:
            raise AuthenticationError("guest mode is disabled")
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
                raise AuthenticationError("empty authorization material")
            if scheme_l == "bearer":
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
            raise AuthenticationError(f"unsupported authorization scheme: {scheme!r}")

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
            raise AuthorizationError(
                f"permission denied: {perm.value} "
                f"(role={principal.role.value})"
            )

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
