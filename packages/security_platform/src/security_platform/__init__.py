"""DSP Authentication & Security Platform (K1.2 + PEP-001).

Protects the API Platform. Never imports ``dsp_platform`` business façades
and contains no financial / recommendation logic.
"""

from __future__ import annotations

from security_platform.security.api_keys import ApiKeyManager, ApiKeyRecord
from security_platform.security.audit import AuditEvent, AuditLogger
from security_platform.security.auth import (
    AuthenticationManager,
    AuthorizationManager,
    OAuth2TokenValidator,
    SecurityBundle,
    SecuritySettings,
)
from security_platform.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    SecurityError,
    TokenError,
)
from security_platform.security.identity import (
    ConsentRecord,
    IdentityService,
    InMemoryUserRepository,
    LockoutPolicy,
    PasswordPolicy,
    SqlUserRepository,
    TokenPair,
    TokenService,
    build_password_hasher,
)
from security_platform.security.jwt import JWTManager, TokenClaims
from security_platform.security.middleware import SecurityMiddleware
from security_platform.security.permissions import (
    PERMISSIONS,
    Permission,
    assert_permission,
)
from security_platform.security.rate_limit import (
    DistributedRateLimiter,
    RateLimitConfig,
    RateLimiter,
)
from security_platform.security.roles import (
    ROLE_PERMISSIONS,
    ROLES,
    Role,
    RoleManager,
    assert_role,
)
from security_platform.security.users import (
    PermissionManager,
    SecurityContext,
    UserPrincipal,
    UserRecord,
    UserStore,
)

__all__ = [
    "ApiKeyManager",
    "ApiKeyRecord",
    "AuditEvent",
    "AuditLogger",
    "AuthenticationError",
    "AuthenticationManager",
    "AuthorizationError",
    "AuthorizationManager",
    "ConsentRecord",
    "DistributedRateLimiter",
    "IdentityService",
    "InMemoryUserRepository",
    "JWTManager",
    "LockoutPolicy",
    "OAuth2TokenValidator",
    "PERMISSIONS",
    "PasswordPolicy",
    "Permission",
    "PermissionManager",
    "ROLE_PERMISSIONS",
    "ROLES",
    "RateLimitConfig",
    "RateLimitError",
    "RateLimiter",
    "Role",
    "RoleManager",
    "SecurityBundle",
    "SecurityContext",
    "SecurityError",
    "SecurityMiddleware",
    "SecuritySettings",
    "SqlUserRepository",
    "TokenClaims",
    "TokenError",
    "TokenPair",
    "TokenService",
    "UserPrincipal",
    "UserRecord",
    "UserStore",
    "assert_permission",
    "assert_role",
    "build_password_hasher",
    "__version__",
]

__version__ = "0.2.0"
