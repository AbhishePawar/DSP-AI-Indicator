"""Identity & security ports (PEP-001) — implementation-independent."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from security_platform.security.audit import AuditEvent

__all__ = [
    "AadhaarPort",
    "AuditStorePort",
    "ConsentRecord",
    "ConsentRecordPort",
    "DigiLockerIdentityPort",
    "EnterpriseKycPort",
    "MfaPort",
    "WebAuthnPort",
    "OidcClientPort",
    "OrgMembership",
    "Organisation",
    "OrganisationStorePort",
    "PanVerificationPort",
    "PasswordHasherPort",
    "RefreshTokenRecord",
    "RefreshTokenStorePort",
    "ScimProvisioningPort",
    "SessionRecord",
    "SessionTrackerPort",
    "UserRepositoryPort",
]


@runtime_checkable
class PasswordHasherPort(Protocol):
    """Password hashing — never log inputs or outputs."""

    def hash(self, password: str) -> str:
        """Return a salted hash string."""

    def verify(self, password: str, password_hash: str) -> bool:
        """Constant-time verify."""


@runtime_checkable
class UserRepositoryPort(Protocol):
    """Durable or in-memory user persistence."""

    def upsert(self, user: Any) -> Any:
        """Create or replace a user."""

    def get(self, user_id: str) -> Any | None:
        """Return user by id or None."""

    def get_by_username(self, username: str) -> Any | None:
        """Return user by username or None."""

    def list_users(self) -> Sequence[Any]:
        """Return all users."""

    def set_active(self, user_id: str, *, active: bool) -> Any:
        """Activate or deactivate a user."""


@runtime_checkable
class RefreshTokenStorePort(Protocol):
    """Opaque refresh-token persistence."""

    def save(self, record: "RefreshTokenRecord") -> None:
        """Persist a refresh token record."""

    def get(self, token_hash: str) -> "RefreshTokenRecord | None":
        """Lookup by hash of the opaque token."""

    def revoke(self, token_hash: str) -> None:
        """Revoke one token."""

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all refresh tokens for a user; return count."""


@runtime_checkable
class SessionTrackerPort(Protocol):
    """Server-side session metadata tracking."""

    def create(self, record: "SessionRecord") -> None:
        """Create a session."""

    def get(self, session_id: str) -> "SessionRecord | None":
        """Fetch session metadata."""

    def touch(self, session_id: str) -> None:
        """Update last-seen."""

    def delete(self, session_id: str) -> None:
        """End a session."""

    def delete_all_for_user(self, user_id: str) -> int:
        """End all sessions for a user."""


@runtime_checkable
class AuditStorePort(Protocol):
    """Append-only security audit sink."""

    def append(self, event: AuditEvent) -> None:
        """Append one audit event."""

    def list_events(self, *, limit: int = 100) -> Sequence[AuditEvent]:
        """Return recent events (newest last)."""


@runtime_checkable
class ConsentRecordPort(Protocol):
    """DPDP consent record store — architecture + minimal implementation."""

    def record(self, consent: "ConsentRecord") -> None:
        """Store a consent decision."""

    def list_for_subject(self, subject_id: str) -> Sequence["ConsentRecord"]:
        """List consents for a data principal."""


@runtime_checkable
class MfaPort(Protocol):
    """MFA enrollment / verification — architecture (TOTP)."""

    def enroll(self, user_id: str) -> str:
        """Begin enrollment; return secret or provisioning URI material."""

    def verify(self, user_id: str, code: str) -> bool:
        """Verify an MFA code."""

    def is_enabled(self, user_id: str) -> bool:
        """Return True when MFA is active for the user."""


@runtime_checkable
class WebAuthnPort(Protocol):
    """Passkeys / FIDO2 — architecture; plug in without changing primary login APIs."""

    def begin_registration(self, user_id: str) -> dict[str, Any]:
        """Return WebAuthn registration options."""

    def complete_registration(self, user_id: str, credential: dict[str, Any]) -> dict[str, Any]:
        """Persist credential after client attestation."""

    def begin_authentication(self, user_id: str) -> dict[str, Any]:
        """Return WebAuthn authentication options."""

    def complete_authentication(self, user_id: str, assertion: dict[str, Any]) -> bool:
        """Verify assertion; return True on success."""


@runtime_checkable
class OrganisationStorePort(Protocol):
    """Organisation + membership — architecture foundation."""

    def upsert_org(self, org: "Organisation") -> Organisation:
        """Create or update an organisation."""

    def get_org(self, org_id: str) -> "Organisation | None":
        """Fetch organisation."""

    def set_membership(self, membership: "OrgMembership") -> None:
        """Bind a user to an org role."""

    def memberships_for_user(self, user_id: str) -> Sequence["OrgMembership"]:
        """List org memberships."""


@runtime_checkable
class OidcClientPort(Protocol):
    """Future OIDC authorization-code client."""

    def exchange_code(self, code: str, *, redirect_uri: str) -> dict[str, Any]:
        """Exchange code for tokens / claims."""


@runtime_checkable
class ScimProvisioningPort(Protocol):
    """Future SCIM user provisioning."""

    def provision_user(self, payload: dict[str, Any]) -> str:
        """Provision a user; return user_id."""


@runtime_checkable
class PanVerificationPort(Protocol):
    """Future PAN verification — hash-only inputs."""

    def verify(self, pan_hash: str) -> dict[str, Any]:
        """Verify PAN hash without storing PAN."""


@runtime_checkable
class DigiLockerIdentityPort(Protocol):
    """Future DigiLocker document fetch."""

    def fetch_document(self, document_id: str) -> bytes:
        """Fetch a document blob."""


@runtime_checkable
class AadhaarPort(Protocol):
    """Future Aadhaar — must not store Aadhaar without legal epic."""

    def verify_offline(self, reference: str) -> dict[str, Any]:
        """Verify via reference only."""


@runtime_checkable
class EnterpriseKycPort(Protocol):
    """Future enterprise KYC."""

    def start_kyc(self, org_id: str, subject_id: str) -> str:
        """Start KYC workflow; return case id."""


# --- records ---


class RefreshTokenRecord:
    __slots__ = (
        "token_hash",
        "user_id",
        "session_id",
        "expires_at",
        "revoked",
        "created_at",
        "family_id",
    )

    def __init__(
        self,
        *,
        token_hash: str,
        user_id: str,
        session_id: str,
        expires_at: datetime,
        revoked: bool = False,
        created_at: datetime | None = None,
        family_id: str | None = None,
    ) -> None:
        from datetime import UTC

        self.token_hash = token_hash
        self.user_id = user_id
        self.session_id = session_id
        self.expires_at = expires_at
        self.revoked = revoked
        self.created_at = created_at or datetime.now(tz=UTC)
        self.family_id = family_id


class SessionRecord:
    __slots__ = (
        "session_id",
        "user_id",
        "expires_at",
        "remember_me",
        "created_at",
        "last_seen_at",
        "client_fingerprint",
    )

    def __init__(
        self,
        *,
        session_id: str,
        user_id: str,
        expires_at: datetime,
        remember_me: bool = False,
        created_at: datetime | None = None,
        last_seen_at: datetime | None = None,
        client_fingerprint: str | None = None,
    ) -> None:
        from datetime import UTC

        now = datetime.now(tz=UTC)
        self.session_id = session_id
        self.user_id = user_id
        self.expires_at = expires_at
        self.remember_me = remember_me
        self.created_at = created_at or now
        self.last_seen_at = last_seen_at or now
        self.client_fingerprint = client_fingerprint


class ConsentRecord:
    __slots__ = (
        "consent_id",
        "subject_id",
        "purpose",
        "granted",
        "recorded_at",
        "policy_version",
    )

    def __init__(
        self,
        *,
        consent_id: str,
        subject_id: str,
        purpose: str,
        granted: bool,
        recorded_at: datetime | None = None,
        policy_version: str = "1",
    ) -> None:
        from datetime import UTC

        self.consent_id = consent_id
        self.subject_id = subject_id
        self.purpose = purpose
        self.granted = granted
        self.recorded_at = recorded_at or datetime.now(tz=UTC)
        self.policy_version = policy_version


class Organisation:
    __slots__ = ("org_id", "name", "status")

    def __init__(self, *, org_id: str, name: str, status: str = "active") -> None:
        self.org_id = org_id
        self.name = name
        self.status = status


class OrgMembership:
    __slots__ = ("user_id", "org_id", "org_role")

    def __init__(self, *, user_id: str, org_id: str, org_role: str) -> None:
        self.user_id = user_id
        self.org_id = org_id
        self.org_role = org_role
