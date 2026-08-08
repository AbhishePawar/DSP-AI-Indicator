"""Institutional Authentication & RBAC (EPIC-A009)."""

from __future__ import annotations

from auth.audit import AuditLogger
from auth.authentication import AuthenticationService
from auth.authorization import AuthorizationService
from auth.enterprise_models import AuthProvider, PRODUCT_ROLES
from auth.enterprise_platform import (
    EnterpriseAuthPlatform,
    get_enterprise_auth_platform,
    password_strength,
    reset_enterprise_auth_platform_for_tests,
)
from auth.exceptions import (
    AuthError,
    AuthenticationError,
    AuthorizationError,
    DuplicateUserError,
    InvalidTokenError,
    RefreshTokenReuseError,
    SessionError,
    ValidationError,
)
from auth.devices import DeviceRegistry
from auth.email_delivery import ConsoleEmailAdapter, SmtpEmailAdapter, build_email_provider
from auth.hashing import hash_password, needs_rehash, verify_password
from auth.jwt import JwtService
from auth.mfa import MfaGateway, NullTotpAdapter, NullWebAuthnAdapter, build_mfa_gateway
from auth.mfa_totp import TotpAdapter
from auth.mfa_webauthn import WebAuthnAdapter
from auth.models import (
    AUTH_SCHEMA_VERSION,
    AUTH_SERVICE_VERSION,
    BUILTIN_ROLES,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    AuthSession,
    AuthTokenPair,
    AuthUser,
    RoleDefinition,
)
from auth.otp import OtpService, normalize_india_mobile
from auth.permissions import assert_permission, list_permissions
from auth.roles import RoleRegistry, builtin_roles, get_role_registry, reset_role_registry_for_tests
from auth.serde import session_to_dict, token_pair_to_dict, user_to_dict
from auth.service import AuthService, get_auth_service, reset_auth_service_for_tests
from auth.sessions import SessionManager
from auth.single_use_tokens import SingleUseTokenError, SingleUseTokenService
from auth.sms import (
    ConsoleSmsAdapter,
    DevSmsAdapter,
    Fast2SmsAdapter,
    Msg91SmsAdapter,
    NullSmsAdapter,
    TwilioSmsAdapter,
    build_sms_provider,
)
from auth.users import UserStore

__all__ = [
    "AUTH_SCHEMA_VERSION",
    "AUTH_SERVICE_VERSION",
    "BUILTIN_ROLES",
    "PERMISSIONS",
    "PRODUCT_ROLES",
    "ROLE_PERMISSIONS",
    "AuditLogger",
    "AuthError",
    "AuthProvider",
    "AuthService",
    "AuthSession",
    "AuthTokenPair",
    "AuthUser",
    "AuthenticationError",
    "AuthenticationService",
    "AuthorizationError",
    "AuthorizationService",
    "ConsoleEmailAdapter",
    "ConsoleSmsAdapter",
    "DeviceRegistry",
    "DevSmsAdapter",
    "DuplicateUserError",
    "EnterpriseAuthPlatform",
    "Fast2SmsAdapter",
    "InvalidTokenError",
    "JwtService",
    "MfaGateway",
    "Msg91SmsAdapter",
    "NullSmsAdapter",
    "NullTotpAdapter",
    "NullWebAuthnAdapter",
    "OtpService",
    "RefreshTokenReuseError",
    "SmtpEmailAdapter",
    "TotpAdapter",
    "TwilioSmsAdapter",
    "WebAuthnAdapter",
    "RoleDefinition",
    "RoleRegistry",
    "SessionError",
    "SessionManager",
    "SingleUseTokenError",
    "SingleUseTokenService",
    "UserStore",
    "ValidationError",
    "assert_permission",
    "build_email_provider",
    "build_mfa_gateway",
    "build_sms_provider",
    "builtin_roles",
    "get_auth_service",
    "get_enterprise_auth_platform",
    "get_role_registry",
    "hash_password",
    "list_permissions",
    "needs_rehash",
    "normalize_india_mobile",
    "password_strength",
    "reset_auth_service_for_tests",
    "reset_enterprise_auth_platform_for_tests",
    "reset_role_registry_for_tests",
    "session_to_dict",
    "token_pair_to_dict",
    "user_to_dict",
    "verify_password",
]

__version__ = "0.1.0"
