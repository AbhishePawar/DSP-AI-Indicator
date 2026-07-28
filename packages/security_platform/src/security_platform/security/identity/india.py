"""India identity ports — architecture stubs (PEP-001)."""

from __future__ import annotations

from typing import Any

from security_platform.security.exceptions import SecurityError
from security_platform.security.identity.ports import (
    AadhaarPort,
    DigiLockerIdentityPort,
    EnterpriseKycPort,
    MfaPort,
    OidcClientPort,
    Organisation,
    OrganisationStorePort,
    OrgMembership,
    PanVerificationPort,
    ScimProvisioningPort,
)

__all__ = [
    "InMemoryOrganisationStore",
    "NullAadhaarPort",
    "NullDigiLockerIdentityPort",
    "NullEnterpriseKycPort",
    "NullMfaPort",
    "NullOidcClientPort",
    "NullPanVerificationPort",
    "NullScimProvisioningPort",
]


class NullMfaPort:
    def enroll(self, user_id: str) -> str:
        raise SecurityError("MFA not configured (architecture port)")

    def verify(self, user_id: str, code: str) -> bool:
        return False

    def is_enabled(self, user_id: str) -> bool:
        return False


class NullOidcClientPort:
    def exchange_code(self, code: str, *, redirect_uri: str) -> dict[str, Any]:
        raise SecurityError("OIDC client not configured (future SSO)")


class NullScimProvisioningPort:
    def provision_user(self, payload: dict[str, Any]) -> str:
        raise SecurityError("SCIM provisioning not configured")


class NullPanVerificationPort:
    def verify(self, pan_hash: str) -> dict[str, Any]:
        raise SecurityError("PAN verification not configured (future India epic)")


class NullDigiLockerIdentityPort:
    def fetch_document(self, document_id: str) -> bytes:
        raise SecurityError("DigiLocker not configured (future India epic)")


class NullAadhaarPort:
    def verify_offline(self, reference: str) -> dict[str, Any]:
        raise SecurityError(
            "Aadhaar port blocked until dedicated legal epic (no Aadhaar storage)"
        )


class NullEnterpriseKycPort:
    def start_kyc(self, org_id: str, subject_id: str) -> str:
        raise SecurityError("Enterprise KYC not configured")


class InMemoryOrganisationStore:
    def __init__(self) -> None:
        self._orgs: dict[str, Organisation] = {}
        self._memberships: list[OrgMembership] = []

    def upsert_org(self, org: Organisation) -> Organisation:
        self._orgs[org.org_id] = org
        return org

    def get_org(self, org_id: str) -> Organisation | None:
        return self._orgs.get(org_id)

    def set_membership(self, membership: OrgMembership) -> None:
        self._memberships = [
            m
            for m in self._memberships
            if not (m.user_id == membership.user_id and m.org_id == membership.org_id)
        ]
        self._memberships.append(membership)

    def memberships_for_user(self, user_id: str) -> tuple[OrgMembership, ...]:
        return tuple(m for m in self._memberships if m.user_id == user_id)


# Protocol satisfaction markers
_: tuple[
    MfaPort,
    OidcClientPort,
    ScimProvisioningPort,
    PanVerificationPort,
    DigiLockerIdentityPort,
    AadhaarPort,
    EnterpriseKycPort,
    OrganisationStorePort,
]
