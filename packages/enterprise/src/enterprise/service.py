"""Enterprise commercial platform service (EPS-002)."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from enterprise.billing import BillingPort, NullBillingAdapter, build_billing_adapter
from enterprise.collaboration import (
    NullCollaborationAdapter,
    collaboration_blueprint,
)
from enterprise.exceptions import ForbiddenError, NotFoundError, ValidationError
from enterprise.models import (
    ENTERPRISE_SCHEMA_VERSION,
    ENTERPRISE_SERVICE_VERSION,
    LICENSE_TIERS,
    ORG_STATUSES,
    TEAM_KINDS,
    UNAVAILABLE_MESSAGES,
    ApiKeyRecord,
    AuditRecord,
    Invitation,
    License,
    Organization,
    OrgMember,
    OrgSession,
    Team,
    UsageSnapshot,
    freeze_mapping,
    utc_now,
)
from enterprise.permissions import (
    BUILTIN_ENTERPRISE_ROLES,
    ENTERPRISE_PERMISSIONS,
    ROLE_PERMISSIONS,
    assert_permission,
    has_permission,
    permissions_for_role,
)
from enterprise.ports import EnterpriseStorePort
from enterprise.store import InMemoryEnterpriseStore

__all__ = [
    "EnterpriseService",
    "enterprise_service_configured",
    "get_enterprise_service",
    "reset_enterprise_service_for_tests",
]

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class EnterpriseService:
    """Multi-tenant enterprise foundation — org isolation, RBAC, commercial ports."""

    def __init__(
        self,
        store: EnterpriseStorePort | InMemoryEnterpriseStore | None = None,
        *,
        billing: BillingPort | None = None,
        collaboration: Any | None = None,
    ) -> None:
        self.store: EnterpriseStorePort = store or InMemoryEnterpriseStore()
        self.billing: BillingPort = billing or NullBillingAdapter()
        self.collaboration = collaboration or NullCollaborationAdapter()

    def _ensure_fresh(self) -> None:
        """P0-06 — sync durable store before reads/writes across workers."""
        ensure = getattr(self.store, "ensure_fresh", None)
        if callable(ensure):
            ensure()

    # ------------------------------------------------------------------ schema
    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": ENTERPRISE_SCHEMA_VERSION,
            "service_version": ENTERPRISE_SERVICE_VERSION,
            "capabilities": [
                "organizations",
                "teams",
                "enterprise_rbac",
                "licensing",
                "billing_port",
                "billing_providers_stripe_razorpay_paddle",
                "customer_portal",
                "sessions",
                "immutable_audit",
                "durable_enterprise_store",
                "api_keys",
                "usage_analytics",
                "ops_incident_center",
                "collaboration_architecture",
            ],
            "roles": list(BUILTIN_ENTERPRISE_ROLES),
            "permissions": list(ENTERPRISE_PERMISSIONS),
            "license_tiers": list(LICENSE_TIERS),
            "team_kinds": list(TEAM_KINDS),
            "billing_provider": self.billing.provider_name(),
            "billing_available": self.billing.is_available(),
            "collaboration": self.collaboration.architecture(),
            "rules": [
                "permission_based_authorization",
                "org_isolation",
                "never_fabricate_enterprise_data",
                "honest_empty_states",
                "no_fake_payment_flows",
                "secrets_server_side_only",
                "audit_immutable",
                "research_engines_untouched",
            ],
            "unavailable_messages": dict(UNAVAILABLE_MESSAGES),
        }

    # -------------------------------------------------------------- permissions
    def require_permission(
        self, org_id: str, user_id: str, permission: str
    ) -> OrgMember:
        member = self.get_member(org_id, user_id)
        if member is None or member.status != "active":
            raise ForbiddenError("not a member of organization")
        assert_permission(permission)
        if not has_permission(member.permissions, permission):
            raise ForbiddenError(f"missing permission {permission}")
        return member

    def evaluate_permission(
        self, org_id: str, user_id: str, permission: str
    ) -> dict[str, Any]:
        try:
            self.require_permission(org_id, user_id, permission)
            allowed = True
            reason = "granted"
        except (ForbiddenError, ValidationError, NotFoundError) as exc:
            allowed = False
            reason = str(exc)
        return {
            "org_id": org_id,
            "user_id": user_id,
            "permission": permission,
            "allowed": allowed,
            "reason": reason,
        }

    def list_roles(self, org_id: str) -> list[dict[str, Any]]:
        builtin = [
            {
                "role_id": rid,
                "name": rid.replace("_", " ").title(),
                "permissions": list(ROLE_PERMISSIONS[rid]),
                "custom": False,
                "org_id": org_id,
            }
            for rid in BUILTIN_ENTERPRISE_ROLES
        ]
        custom = [
            v
            for k, v in self.store.custom_roles.items()
            if k.startswith(f"{org_id}:")
        ]
        return builtin + custom

    def upsert_custom_role(
        self,
        org_id: str,
        role_id: str,
        *,
        name: str | None = None,
        permissions: list[str] | None = None,
        actor_user_id: str | None = None,
    ) -> dict[str, Any]:
        if actor_user_id:
            self.require_permission(org_id, actor_user_id, "roles.manage")
        rid = str(role_id or "").strip().lower()
        if not rid or rid in BUILTIN_ENTERPRISE_ROLES:
            raise ValidationError("invalid or reserved role_id")
        perms = tuple(assert_permission(p) for p in (permissions or []))
        row = {
            "role_id": rid,
            "name": (name or rid).strip(),
            "permissions": list(perms),
            "custom": True,
            "org_id": org_id,
        }
        self.store.custom_roles[f"{org_id}:{rid}"] = row
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="role.upsert",
            resource_type="role",
            resource_id=rid,
        )
        return row

    def _resolve_permissions(self, org_id: str, role_id: str) -> tuple[str, ...]:
        rid = str(role_id or "").strip().lower()
        if rid in ROLE_PERMISSIONS:
            return ROLE_PERMISSIONS[rid]
        custom = self.store.custom_roles.get(f"{org_id}:{rid}")
        if custom is None:
            raise ValidationError(f"unknown role {role_id!r}")
        return tuple(custom["permissions"])

    # ----------------------------------------------------------- organizations
    def create_organization(
        self,
        *,
        name: str,
        slug: str,
        owner_user_id: str,
        org_id: str | None = None,
        seat_limit: int | None = None,
        branding: dict[str, Any] | None = None,
        preferences: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_fresh()
        clean_name = str(name or "").strip()
        clean_slug = str(slug or "").strip().lower()
        owner = str(owner_user_id or "").strip()
        if not clean_name:
            raise ValidationError("name required")
        if not _SLUG_RE.match(clean_slug):
            raise ValidationError("invalid slug")
        if not owner:
            raise ValidationError("owner_user_id required")
        if any(o.slug == clean_slug for o in self.store.organizations.values()):
            raise ValidationError("slug already exists")
        now = created_at or utc_now().isoformat()
        oid = (org_id or f"org_{uuid.uuid4().hex[:12]}").strip()
        if oid in self.store.organizations:
            raise ValidationError("org_id already exists")
        org = Organization(
            org_id=oid,
            name=clean_name,
            slug=clean_slug,
            status="active",
            owner_user_id=owner,
            created_at=now,
            updated_at=now,
            branding=freeze_mapping(branding),
            preferences=freeze_mapping(preferences),
            metadata=freeze_mapping(metadata),
            seat_limit=seat_limit,
        )
        self.store.organizations[oid] = org
        member = OrgMember(
            org_id=oid,
            user_id=owner,
            role_id="owner",
            status="active",
            joined_at=now,
            permissions=permissions_for_role("owner"),
            display_name=None,
            email=None,
        )
        self.store.members[self.store.member_key(oid, owner)] = member
        self._audit(
            org_id=oid,
            actor_user_id=owner,
            action="org.create",
            resource_type="organization",
            resource_id=oid,
        )
        return org.to_dict()

    def list_organizations(self, *, user_id: str | None = None) -> list[dict[str, Any]]:
        self._ensure_fresh()
        orgs = list(self.store.organizations.values())
        if user_id:
            member_orgs = {
                m.org_id
                for m in self.store.members.values()
                if m.user_id == user_id and m.status == "active"
            }
            orgs = [o for o in orgs if o.org_id in member_orgs]
        if not orgs:
            return []
        return [o.to_dict() for o in sorted(orgs, key=lambda x: x.name.lower())]

    def get_organization(self, org_id: str) -> dict[str, Any] | None:
        self._ensure_fresh()
        org = self.store.organizations.get(org_id)
        return org.to_dict() if org else None

    def update_organization(
        self,
        org_id: str,
        *,
        actor_user_id: str,
        name: str | None = None,
        status: str | None = None,
        branding: dict[str, Any] | None = None,
        preferences: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        seat_limit: int | None = None,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "org.manage")
        org = self.store.organizations.get(org_id)
        if org is None:
            raise NotFoundError("organization not found")
        if status is not None and status not in ORG_STATUSES:
            raise ValidationError("invalid status")
        updated = Organization(
            org_id=org.org_id,
            name=(name or org.name).strip(),
            slug=org.slug,
            status=status or org.status,
            owner_user_id=org.owner_user_id,
            created_at=org.created_at,
            updated_at=utc_now().isoformat(),
            branding=freeze_mapping(branding) if branding is not None else org.branding,
            preferences=(
                freeze_mapping(preferences)
                if preferences is not None
                else org.preferences
            ),
            metadata=freeze_mapping(metadata) if metadata is not None else org.metadata,
            seat_limit=seat_limit if seat_limit is not None else org.seat_limit,
            parent_org_id=org.parent_org_id,
        )
        self.store.organizations[org_id] = updated
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="org.update",
            resource_type="organization",
            resource_id=org_id,
        )
        return updated.to_dict()

    # ------------------------------------------------------------------- teams
    def create_team(
        self,
        org_id: str,
        *,
        name: str,
        kind: str = "custom",
        actor_user_id: str,
        parent_team_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "teams.manage")
        if kind not in TEAM_KINDS:
            raise ValidationError("invalid team kind")
        if parent_team_id and parent_team_id not in self.store.teams:
            raise ValidationError("parent team not found")
        if parent_team_id:
            parent = self.store.teams[parent_team_id]
            if parent.org_id != org_id:
                raise ForbiddenError("parent team org mismatch")
        now = utc_now().isoformat()
        tid = (team_id or f"team_{uuid.uuid4().hex[:12]}").strip()
        team = Team(
            team_id=tid,
            org_id=org_id,
            name=str(name).strip(),
            kind=kind,
            created_at=now,
            updated_at=now,
            parent_team_id=parent_team_id,
        )
        self.store.teams[tid] = team
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="team.create",
            resource_type="team",
            resource_id=tid,
        )
        return team.to_dict()

    def list_teams(self, org_id: str, *, actor_user_id: str) -> list[dict[str, Any]]:
        self.require_permission(org_id, actor_user_id, "teams.view")
        rows = [t for t in self.store.teams.values() if t.org_id == org_id]
        if not rows:
            return []
        return [t.to_dict() for t in sorted(rows, key=lambda x: x.name.lower())]

    # ----------------------------------------------------------------- members
    def get_member(self, org_id: str, user_id: str) -> OrgMember | None:
        self._ensure_fresh()
        return self.store.members.get(self.store.member_key(org_id, user_id))

    def list_members(self, org_id: str, *, actor_user_id: str) -> list[dict[str, Any]]:
        self.require_permission(org_id, actor_user_id, "members.view")
        rows = [
            m
            for m in self.store.members.values()
            if m.org_id == org_id and m.status != "removed"
        ]
        if not rows:
            return []
        return [m.to_dict() for m in sorted(rows, key=lambda x: x.user_id)]

    def add_member(
        self,
        org_id: str,
        *,
        user_id: str,
        role_id: str,
        actor_user_id: str,
        display_name: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "members.manage")
        if org_id not in self.store.organizations:
            raise NotFoundError("organization not found")
        org = self.store.organizations[org_id]
        active = [
            m
            for m in self.store.members.values()
            if m.org_id == org_id and m.status == "active"
        ]
        if org.seat_limit is not None and len(active) >= org.seat_limit:
            raise ValidationError("seat limit reached")
        perms = self._resolve_permissions(org_id, role_id)
        now = utc_now().isoformat()
        member = OrgMember(
            org_id=org_id,
            user_id=user_id.strip(),
            role_id=role_id.strip().lower(),
            status="active",
            joined_at=now,
            permissions=perms,
            display_name=display_name,
            email=email,
        )
        self.store.members[self.store.member_key(org_id, user_id)] = member
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="member.add",
            resource_type="member",
            resource_id=user_id,
            metadata={"role_id": role_id},
        )
        return member.to_dict()

    def set_member_role(
        self,
        org_id: str,
        user_id: str,
        role_id: str,
        *,
        actor_user_id: str,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "members.manage")
        member = self.get_member(org_id, user_id)
        if member is None:
            raise NotFoundError("member not found")
        perms = self._resolve_permissions(org_id, role_id)
        updated = OrgMember(
            org_id=member.org_id,
            user_id=member.user_id,
            role_id=role_id.strip().lower(),
            status=member.status,
            joined_at=member.joined_at,
            permissions=perms,
            team_ids=member.team_ids,
            display_name=member.display_name,
            email=member.email,
        )
        self.store.members[self.store.member_key(org_id, user_id)] = updated
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="member.role_change",
            resource_type="member",
            resource_id=user_id,
            metadata={"role_id": role_id},
        )
        return updated.to_dict()

    def invite_member(
        self,
        org_id: str,
        *,
        email: str,
        role_id: str,
        actor_user_id: str,
        expires_in_days: int = 14,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "members.invite")
        self._resolve_permissions(org_id, role_id)
        now = utc_now()
        inv = Invitation(
            invitation_id=f"inv_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            email=email.strip().lower(),
            role_id=role_id.strip().lower(),
            status="pending",
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=expires_in_days)).isoformat(),
            invited_by=actor_user_id,
        )
        self.store.invitations[inv.invitation_id] = inv
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="member.invite",
            resource_type="invitation",
            resource_id=inv.invitation_id,
        )
        return inv.to_dict()

    def list_invitations(
        self, org_id: str, *, actor_user_id: str
    ) -> list[dict[str, Any]]:
        self.require_permission(org_id, actor_user_id, "members.view")
        rows = [i for i in self.store.invitations.values() if i.org_id == org_id]
        return [i.to_dict() for i in rows]

    # --------------------------------------------------------------- licensing
    def assign_license(
        self,
        org_id: str,
        *,
        tier: str,
        seats: int,
        actor_user_id: str,
        expires_at: str | None = None,
        usage_limits: dict[str, Any] | None = None,
        license_id: str | None = None,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "license.manage")
        if tier not in LICENSE_TIERS:
            raise ValidationError("invalid license tier")
        if seats < 1:
            raise ValidationError("seats must be >= 1")
        now = utc_now().isoformat()
        lic = License(
            license_id=(license_id or f"lic_{uuid.uuid4().hex[:12]}").strip(),
            org_id=org_id,
            tier=tier,
            status="active",
            seats=seats,
            created_at=now,
            expires_at=expires_at,
            usage_limits=freeze_mapping(usage_limits),
        )
        self.store.licenses[org_id] = lic
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="license.assign",
            resource_type="license",
            resource_id=lic.license_id,
            metadata={"tier": tier, "seats": seats},
        )
        return lic.to_dict()

    def get_license(self, org_id: str, *, actor_user_id: str) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "license.view")
        lic = self.store.licenses.get(org_id)
        if lic is None:
            return {
                "available": False,
                "message": UNAVAILABLE_MESSAGES["license"],
                "license": None,
            }
        status = lic.status
        if lic.expires_at:
            try:
                exp = datetime.fromisoformat(lic.expires_at.replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=UTC)
                if exp < utc_now():
                    status = "expired"
            except ValueError:
                pass
        row = lic.to_dict()
        row["status"] = status
        row["valid"] = status == "active"
        return {"available": True, "message": None, "license": row}

    def validate_license(self, org_id: str) -> dict[str, Any]:
        lic = self.store.licenses.get(org_id)
        if lic is None:
            return {
                "valid": False,
                "reason": UNAVAILABLE_MESSAGES["license"],
                "tier": None,
            }
        if lic.expires_at:
            try:
                exp = datetime.fromisoformat(lic.expires_at.replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=UTC)
                if exp < utc_now():
                    return {"valid": False, "reason": "license expired", "tier": lic.tier}
            except ValueError:
                return {"valid": False, "reason": "invalid expiration", "tier": lic.tier}
        return {"valid": lic.status == "active", "reason": None, "tier": lic.tier}

    # ------------------------------------------------------------------ billing
    def billing_status(self, org_id: str, *, actor_user_id: str) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "billing.view")
        return self.billing.payment_status(org_id)

    def list_invoices(self, org_id: str, *, actor_user_id: str) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "billing.view")
        if not self.billing.is_available():
            return {
                "available": False,
                "message": UNAVAILABLE_MESSAGES["billing"],
                "invoices": [],
            }
        invoices = [i.to_dict() for i in self.billing.list_invoices(org_id)]
        return {
            "available": True,
            "message": None if invoices else UNAVAILABLE_MESSAGES["invoices"],
            "invoices": invoices,
        }

    # ------------------------------------------------------------------ portal
    def customer_portal(
        self, org_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "org.view")
        org = self.get_organization(org_id)
        if org is None:
            raise NotFoundError("organization not found")
        license_info = self.get_license(org_id, actor_user_id=actor_user_id)
        members = self.list_members(org_id, actor_user_id=actor_user_id)
        usage = self.usage_snapshot(org_id, actor_user_id=actor_user_id)
        billing = self.billing_status(org_id, actor_user_id=actor_user_id)
        keys = self.list_api_keys(org_id, actor_user_id=actor_user_id)
        return {
            "organization": org,
            "license": license_info,
            "members": members,
            "members_message": (
                None if members else UNAVAILABLE_MESSAGES["members"]
            ),
            "usage": usage,
            "billing": billing,
            "api_keys": keys,
            "settings": {
                "branding": org.get("branding") or {},
                "preferences": org.get("preferences") or {},
            },
        }

    # ----------------------------------------------------------------- sessions
    def create_session(
        self,
        org_id: str,
        *,
        user_id: str,
        device_label: str = "unknown",
        ip_hint: str | None = None,
        user_agent_hint: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        if self.get_member(org_id, user_id) is None:
            raise ForbiddenError("not a member of organization")
        now = utc_now().isoformat()
        sid = (session_id or f"es_{uuid.uuid4().hex[:16]}").strip()
        session = OrgSession(
            session_id=sid,
            org_id=org_id,
            user_id=user_id,
            device_label=device_label.strip() or "unknown",
            created_at=now,
            last_seen_at=now,
            status="active",
            ip_hint=ip_hint,
            user_agent_hint=user_agent_hint,
        )
        self.store.sessions[sid] = session
        self._audit(
            org_id=org_id,
            actor_user_id=user_id,
            action="session.create",
            resource_type="session",
            resource_id=sid,
        )
        return session.to_dict()

    def list_sessions(
        self, org_id: str, *, actor_user_id: str, active_only: bool = True
    ) -> list[dict[str, Any]]:
        self.require_permission(org_id, actor_user_id, "sessions.view")
        rows = [s for s in self.store.sessions.values() if s.org_id == org_id]
        if active_only:
            rows = [s for s in rows if s.status == "active"]
        if not rows:
            return []
        return [s.to_dict() for s in rows]

    def revoke_session(
        self, org_id: str, session_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "sessions.revoke")
        session = self.store.sessions.get(session_id)
        if session is None or session.org_id != org_id:
            raise NotFoundError("session not found")
        revoked = OrgSession(
            session_id=session.session_id,
            org_id=session.org_id,
            user_id=session.user_id,
            device_label=session.device_label,
            created_at=session.created_at,
            last_seen_at=utc_now().isoformat(),
            status="revoked",
            ip_hint=session.ip_hint,
            user_agent_hint=session.user_agent_hint,
        )
        self.store.sessions[session_id] = revoked
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="session.revoke",
            resource_type="session",
            resource_id=session_id,
        )
        return revoked.to_dict()

    # -------------------------------------------------------------------- audit
    def _audit(
        self,
        *,
        org_id: str | None,
        actor_user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        metadata: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditRecord:
        # Persist working set after mutation; durable stores flush to shared DB.
        record = AuditRecord(
            event_id=f"aud_{uuid.uuid4().hex[:16]}",
            org_id=org_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            created_at=utc_now().isoformat(),
            metadata=freeze_mapping(metadata),
            immutable=True,
            before_state=freeze_mapping(before) if before is not None else None,
            after_state=freeze_mapping(after) if after is not None else None,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        self.store.audit.append(record)
        self.store.flush()
        return record

    def record_audit(
        self,
        *,
        org_id: str | None,
        actor_user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            before=before,
            after=after,
            ip_address=ip_address,
            correlation_id=correlation_id,
        ).to_dict()

    def list_audit(
        self, org_id: str, *, actor_user_id: str
    ) -> list[dict[str, Any]]:
        self.require_permission(org_id, actor_user_id, "audit.view")
        rows = [a for a in self.store.audit if a.org_id == org_id]
        if not rows:
            return []
        return [a.to_dict() for a in rows]

    def mutate_audit_forbidden(self, event_id: str) -> None:
        """Audit records are immutable — any mutation attempt raises."""
        raise ForbiddenError("audit records are immutable")

    # ---------------------------------------------------------------- api keys
    def create_api_key(
        self,
        org_id: str,
        *,
        name: str,
        scopes: list[str],
        actor_user_id: str,
        expires_at: str | None = None,
        key_id: str | None = None,
        raw_secret: str | None = None,
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "api_keys.manage")
        for scope in scopes:
            assert_permission(scope)
        kid = (key_id or f"ak_{secrets.token_hex(8)}").strip()
        if kid in self.store.api_keys:
            raise ValidationError("duplicate key_id")
        secret = raw_secret or f"dsp_{secrets.token_urlsafe(24)}"
        record = ApiKeyRecord(
            key_id=kid,
            org_id=org_id,
            name=name.strip(),
            scopes=tuple(scopes),
            status="active",
            created_at=utc_now().isoformat(),
            secret_hash=_hash_secret(secret),
            expires_at=expires_at,
            created_by=actor_user_id,
        )
        self.store.api_keys[kid] = record
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="api_key.create",
            resource_type="api_key",
            resource_id=kid,
            metadata={"scopes": scopes},
        )
        # Secret returned once — never stored in plaintext
        return {
            **record.to_public_dict(),
            "secret": secret,
            "secret_shown_once": True,
        }

    def list_api_keys(
        self, org_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "api_keys.view")
        rows = [
            k.to_public_dict()
            for k in self.store.api_keys.values()
            if k.org_id == org_id
        ]
        return {
            "keys": rows,
            "message": None if rows else UNAVAILABLE_MESSAGES["api_keys"],
        }

    def rotate_api_key(
        self, org_id: str, key_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "api_keys.manage")
        existing = self.store.api_keys.get(key_id)
        if existing is None or existing.org_id != org_id:
            raise NotFoundError("api key not found")
        secret = f"dsp_{secrets.token_urlsafe(24)}"
        rotated = ApiKeyRecord(
            key_id=existing.key_id,
            org_id=existing.org_id,
            name=existing.name,
            scopes=existing.scopes,
            status="active",
            created_at=existing.created_at,
            secret_hash=_hash_secret(secret),
            expires_at=existing.expires_at,
            created_by=existing.created_by,
            last_used_at=existing.last_used_at,
        )
        self.store.api_keys[key_id] = rotated
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="api_key.rotate",
            resource_type="api_key",
            resource_id=key_id,
        )
        return {**rotated.to_public_dict(), "secret": secret, "secret_shown_once": True}

    def disable_api_key(
        self, org_id: str, key_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "api_keys.manage")
        existing = self.store.api_keys.get(key_id)
        if existing is None or existing.org_id != org_id:
            raise NotFoundError("api key not found")
        disabled = ApiKeyRecord(
            key_id=existing.key_id,
            org_id=existing.org_id,
            name=existing.name,
            scopes=existing.scopes,
            status="disabled",
            created_at=existing.created_at,
            secret_hash=existing.secret_hash,
            expires_at=existing.expires_at,
            created_by=existing.created_by,
            last_used_at=existing.last_used_at,
        )
        self.store.api_keys[key_id] = disabled
        self._audit(
            org_id=org_id,
            actor_user_id=actor_user_id,
            action="api_key.disable",
            resource_type="api_key",
            resource_id=key_id,
        )
        return disabled.to_public_dict()

    def verify_api_key(
        self, key_id: str, raw_secret: str, *, required_scope: str | None = None
    ) -> dict[str, Any]:
        record = self.store.api_keys.get(key_id)
        if record is None or record.status != "active":
            raise ForbiddenError("invalid api key")
        if not hmac.compare_digest(record.secret_hash, _hash_secret(raw_secret)):
            raise ForbiddenError("invalid api key")
        if record.expires_at:
            try:
                exp = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=UTC)
                if exp < utc_now():
                    raise ForbiddenError("api key expired")
            except ValueError as exc:
                raise ForbiddenError("api key expired") from exc
        if required_scope and required_scope not in record.scopes:
            raise ForbiddenError("insufficient api key scope")
        return record.to_public_dict()

    # ------------------------------------------------------------------- usage
    def increment_usage(self, org_id: str, metric: str, amount: int = 1) -> None:
        counters = self.store.usage_counters.setdefault(org_id, {})
        counters[metric] = counters.get(metric, 0) + amount
        self.store.flush()

    def usage_snapshot(
        self, org_id: str, *, actor_user_id: str
    ) -> dict[str, Any]:
        self.require_permission(org_id, actor_user_id, "usage.view")
        counters = self.store.usage_counters.get(org_id)
        if counters is None:
            snap = UsageSnapshot(
                org_id=org_id,
                generated_at=utc_now().isoformat(),
                dau=0,
                research_count=0,
                export_count=0,
                comparison_count=0,
                api_request_count=0,
                storage_bytes=0,
                available=True,
                message=None,
            )
            # Honest zeros when tracking exists but empty; org may have no activity
            return snap.to_dict()
        snap = UsageSnapshot(
            org_id=org_id,
            generated_at=utc_now().isoformat(),
            dau=counters.get("dau", 0),
            research_count=counters.get("research", 0),
            export_count=counters.get("exports", 0),
            comparison_count=counters.get("comparisons", 0),
            api_request_count=counters.get("api_requests", 0),
            storage_bytes=counters.get("storage_bytes", 0),
            available=True,
        )
        return snap.to_dict()

    def platform_usage_analytics(self) -> dict[str, Any]:
        """Platform-wide usage for admin — honest zeros when no data."""
        org_count = len(self.store.organizations)
        if org_count == 0:
            return {
                "available": True,
                "dau": 0,
                "organizations": 0,
                "research": 0,
                "exports": 0,
                "comparisons": 0,
                "storage_bytes": 0,
                "api_usage": 0,
                "message": None,
            }
        totals = {
            "dau": 0,
            "research": 0,
            "exports": 0,
            "comparisons": 0,
            "storage_bytes": 0,
            "api_requests": 0,
        }
        for counters in self.store.usage_counters.values():
            for k in totals:
                totals[k] += counters.get(k, 0)
        return {
            "available": True,
            "dau": totals["dau"],
            "organizations": org_count,
            "research": totals["research"],
            "exports": totals["exports"],
            "comparisons": totals["comparisons"],
            "storage_bytes": totals["storage_bytes"],
            "api_usage": totals["api_requests"],
            "message": None,
        }

    # ---------------------------------------------------------------------- ops
    def incident_center(self, *, infrastructure: Any | None = None) -> dict[str, Any]:
        """Runtime/deps/Redis/DB/storage/jobs status — honest unavailable when unknown."""
        components: dict[str, Any] = {
            "runtime": {"status": "ok", "detail": "enterprise service running"},
            "database": {"status": "unknown", "detail": "Data unavailable."},
            "redis": {"status": "unknown", "detail": "Data unavailable."},
            "storage": {"status": "unknown", "detail": "Data unavailable."},
            "jobs": {"status": "unknown", "detail": "Data unavailable."},
            "dependencies": {"status": "unknown", "detail": "Data unavailable."},
        }
        if infrastructure is not None:
            for name, attr in (
                ("database", "database"),
                ("redis", "cache"),
                ("storage", "storage"),
                ("jobs", "jobs"),
            ):
                port = getattr(infrastructure, attr, None)
                if port is None:
                    continue
                try:
                    healthy = True
                    if hasattr(port, "ping"):
                        healthy = bool(port.ping())
                    elif hasattr(port, "health"):
                        healthy = bool(port.health())
                    components[name] = {
                        "status": "ok" if healthy else "degraded",
                        "detail": type(port).__name__,
                    }
                except Exception as exc:  # noqa: BLE001
                    components[name] = {
                        "status": "error",
                        "detail": str(exc) or "Data unavailable.",
                    }
        overall = "ok"
        for c in components.values():
            if c.get("status") == "error":
                overall = "error"
                break
            if c.get("status") in {"degraded", "unknown"} and overall == "ok":
                overall = "degraded"
        return {
            "overall": overall,
            "generated_at": utc_now().isoformat(),
            "components": components,
        }

    def operational_dashboard(
        self, *, infrastructure: Any | None = None
    ) -> dict[str, Any]:
        return {
            "enterprise_health": self.incident_center(infrastructure=infrastructure),
            "organizations": len(self.store.organizations),
            "active_sessions": sum(
                1 for s in self.store.sessions.values() if s.status == "active"
            ),
            "usage": self.platform_usage_analytics(),
            "billing_provider": self.billing.provider_name(),
            "billing_available": self.billing.is_available(),
            "deployments": {
                "available": False,
                "message": "Data unavailable.",
            },
            "alerts": [],
            "services": [
                {"name": "enterprise", "status": "ok"},
                {"name": "auth", "status": "ok"},
                {"name": "admin", "status": "ok"},
            ],
            "collaboration": collaboration_blueprint(),
        }

    def admin_overview(self) -> dict[str, Any]:
        orgs = [o.to_dict() for o in self.store.organizations.values()]
        return {
            "organizations": orgs,
            "organizations_message": (
                None if orgs else UNAVAILABLE_MESSAGES["organizations"]
            ),
            "licenses": [lic.to_dict() for lic in self.store.licenses.values()],
            "usage": self.platform_usage_analytics(),
            "audit_count": len(self.store.audit),
            "ops": self.operational_dashboard(),
        }


_SVC: EnterpriseService | None = None


def enterprise_service_configured() -> bool:
    return _SVC is not None


def get_enterprise_service(
    *,
    database: Any | None = None,
    billing: BillingPort | None = None,
) -> EnterpriseService:
    """Return process singleton — durable store when DatabasePort is supplied."""
    global _SVC
    if _SVC is None:
        store: EnterpriseStorePort | None = None
        if database is not None:
            from enterprise.db_store import DatabaseEnterpriseStore

            store = DatabaseEnterpriseStore(database)
        _SVC = EnterpriseService(
            store=store,
            billing=billing or build_billing_adapter(),
        )
    return _SVC


def reset_enterprise_service_for_tests(
    service: EnterpriseService | None = None,
) -> None:
    global _SVC
    _SVC = service
