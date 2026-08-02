"""Institutional Authentication & RBAC (EPIC-A009)."""

from __future__ import annotations

from auth.authentication import AuthenticationService
from auth.authorization import AuthorizationService
from auth.exceptions import (
    AuthError,
    AuthenticationError,
    AuthorizationError,
    DuplicateUserError,
    InvalidTokenError,
    SessionError,
    ValidationError,
)
from auth.hashing import hash_password, verify_password
from auth.jwt import JwtService
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
from auth.permissions import assert_permission, list_permissions
from auth.roles import RoleRegistry, builtin_roles, get_role_registry, reset_role_registry_for_tests
from auth.serde import session_to_dict, token_pair_to_dict, user_to_dict
from auth.service import AuthService, get_auth_service, reset_auth_service_for_tests
from auth.sessions import SessionManager
from auth.users import UserStore

__all__ = [
    "AUTH_SCHEMA_VERSION",
    "AUTH_SERVICE_VERSION",
    "BUILTIN_ROLES",
    "PERMISSIONS",
    "ROLE_PERMISSIONS",
    "AuthError",
    "AuthService",
    "AuthSession",
    "AuthTokenPair",
    "AuthUser",
    "AuthenticationError",
    "AuthenticationService",
    "AuthorizationError",
    "AuthorizationService",
    "DuplicateUserError",
    "InvalidTokenError",
    "JwtService",
    "RoleDefinition",
    "RoleRegistry",
    "SessionError",
    "SessionManager",
    "UserStore",
    "ValidationError",
    "assert_permission",
    "builtin_roles",
    "get_auth_service",
    "get_role_registry",
    "hash_password",
    "list_permissions",
    "reset_auth_service_for_tests",
    "reset_role_registry_for_tests",
    "session_to_dict",
    "token_pair_to_dict",
    "user_to_dict",
    "verify_password",
]

__version__ = "0.1.0"
