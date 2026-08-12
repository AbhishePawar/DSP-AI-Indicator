"""DatabasePort-backed enterprise store (EPIC-016).

Uses JSON document snapshots compatible with InMemoryDatabasePort's limited
SQL dialect and PostgresDatabasePort. InMemoryEnterpriseStore remains the
test adapter.
"""

from __future__ import annotations

import base64
import json
from threading import Lock
from typing import Any

from enterprise.models import (
    ApiKeyRecord,
    AuditRecord,
    Invitation,
    License,
    Organization,
    OrgMember,
    OrgSession,
    Team,
    freeze_mapping,
    utc_now,
)
from enterprise.store import InMemoryEnterpriseStore

__all__ = [
    "ENTERPRISE_MIGRATIONS_SQL",
    "DatabaseEnterpriseStore",
    "build_enterprise_store",
]

ENTERPRISE_MIGRATIONS_SQL = (
    """
    CREATE TABLE IF NOT EXISTS enterprise_snapshots (
        snapshot_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enterprise_audit_log (
        event_id TEXT PRIMARY KEY,
        org_id TEXT,
        actor_user_id TEXT,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id TEXT,
        created_at TEXT NOT NULL,
        before_state TEXT,
        after_state TEXT,
        ip_address TEXT,
        correlation_id TEXT,
        metadata TEXT,
        immutable INTEGER NOT NULL
    )
    """,
)

_SNAPSHOT_KEY = "enterprise_v1"


class DatabaseEnterpriseStore(InMemoryEnterpriseStore):
    """Enterprise store hydrated from / flushed to DatabasePort."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        for stmt in ENTERPRISE_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def hydrate(self) -> None:
        rows = self._db.fetchall("SELECT * FROM enterprise_snapshots")
        payload: dict[str, Any] | None = None
        for row in rows:
            if str(row.get("snapshot_key")) == _SNAPSHOT_KEY:
                raw = row.get("payload")
                if isinstance(raw, dict):
                    payload = raw
                elif isinstance(raw, str):
                    payload = _decode_payload(raw)
                break
        if not payload:
            self._hydrate_audit_only()
            return
        with self._lock:
            self.organizations = {
                k: _org_from_dict(v) for k, v in (payload.get("organizations") or {}).items()
            }
            self.teams = {k: _team_from_dict(v) for k, v in (payload.get("teams") or {}).items()}
            self.members = {
                k: _member_from_dict(v) for k, v in (payload.get("members") or {}).items()
            }
            self.invitations = {
                k: _invite_from_dict(v)
                for k, v in (payload.get("invitations") or {}).items()
            }
            self.licenses = {
                k: _license_from_dict(v) for k, v in (payload.get("licenses") or {}).items()
            }
            self.api_keys = {
                k: _api_key_from_dict(v) for k, v in (payload.get("api_keys") or {}).items()
            }
            self.sessions = {
                k: _session_from_dict(v) for k, v in (payload.get("sessions") or {}).items()
            }
            self.custom_roles = dict(payload.get("custom_roles") or {})
            self.usage_counters = {
                k: dict(v) for k, v in (payload.get("usage_counters") or {}).items()
            }
        self._hydrate_audit_only()

    def _hydrate_audit_only(self) -> None:
        rows = self._db.fetchall("SELECT * FROM enterprise_audit_log")
        records: list[AuditRecord] = []
        for row in sorted(rows, key=lambda r: str(r.get("created_at") or "")):
            records.append(_audit_from_row(row))
        with self._lock:
            self.audit = records

    def flush(self) -> None:
        """Persist working set + append-only audit rows."""
        with self._persist_lock:
            snapshot = {
                "organizations": {k: v.to_dict() for k, v in self.organizations.items()},
                "teams": {k: v.to_dict() for k, v in self.teams.items()},
                "members": {k: v.to_dict() for k, v in self.members.items()},
                "invitations": {k: v.to_dict() for k, v in self.invitations.items()},
                "licenses": {k: v.to_dict() for k, v in self.licenses.items()},
                "api_keys": {
                    k: {**v.to_public_dict(), "secret_hash": v.secret_hash}
                    for k, v in self.api_keys.items()
                },
                "sessions": {k: v.to_dict() for k, v in self.sessions.items()},
                "custom_roles": dict(self.custom_roles),
                "usage_counters": {
                    k: dict(v) for k, v in self.usage_counters.items()
                },
            }
            # InMemoryDatabasePort DELETE clears the table — rewrite snapshot row.
            self._db.execute("DELETE FROM enterprise_snapshots")
            now = utc_now().isoformat()
            # Base64 avoids commas/quotes that break the in-memory SQL dialect parser.
            encoded = base64.b64encode(
                json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            self._db.execute(
                "INSERT INTO enterprise_snapshots (snapshot_key, payload, updated_at) "
                f"VALUES ('{_SNAPSHOT_KEY}', {_sql_literal(encoded)}, {_sql_literal(now)})"
            )
            self._flush_audit_append_only()

    def _flush_audit_append_only(self) -> None:
        """Insert missing audit rows — never update or delete existing events."""
        existing_ids = {
            str(r.get("event_id"))
            for r in self._db.fetchall("SELECT * FROM enterprise_audit_log")
        }
        for record in self.audit:
            if record.event_id in existing_ids:
                continue
            meta = _b64_json(dict(record.metadata))
            before = (
                _b64_json(dict(record.before_state))
                if record.before_state is not None
                else None
            )
            after = (
                _b64_json(dict(record.after_state))
                if record.after_state is not None
                else None
            )
            cols = (
                "event_id, org_id, actor_user_id, action, resource_type, resource_id, "
                "created_at, before_state, after_state, ip_address, correlation_id, "
                "metadata, immutable"
            )
            vals = ", ".join(
                [
                    _sql_literal(record.event_id),
                    _sql_literal(record.org_id),
                    _sql_literal(record.actor_user_id),
                    _sql_literal(record.action),
                    _sql_literal(record.resource_type),
                    _sql_literal(record.resource_id),
                    _sql_literal(record.created_at),
                    _sql_literal(before),
                    _sql_literal(after),
                    _sql_literal(record.ip_address),
                    _sql_literal(record.correlation_id),
                    _sql_literal(meta),
                    "1",
                ]
            )
            self._db.execute(
                f"INSERT INTO enterprise_audit_log ({cols}) VALUES ({vals})"
            )

    def clear(self) -> None:
        super().clear()
        with self._persist_lock:
            self._db.execute("DELETE FROM enterprise_snapshots")
            # Audit remains append-only — do not wipe durable audit on clear.
            # Process-local clear for tests that use DatabaseEnterpriseStore should
            # recreate the store instance instead of expecting audit wipe.


def build_enterprise_store(database: Any | None = None) -> InMemoryEnterpriseStore:
    """Factory — DatabasePort when provided, else in-memory."""
    if database is None:
        return InMemoryEnterpriseStore()
    return DatabaseEnterpriseStore(database)


def _b64_json(value: dict[str, Any]) -> str:
    return base64.b64encode(
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")


def _decode_payload(raw: str) -> dict[str, Any]:
    try:
        decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("enterprise snapshot payload must be an object")
    return data


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _org_from_dict(data: dict[str, Any]) -> Organization:
    return Organization(
        org_id=str(data["org_id"]),
        name=str(data["name"]),
        slug=str(data["slug"]),
        status=str(data["status"]),
        owner_user_id=str(data["owner_user_id"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        branding=freeze_mapping(data.get("branding")),
        preferences=freeze_mapping(data.get("preferences")),
        metadata=freeze_mapping(data.get("metadata")),
        seat_limit=data.get("seat_limit"),
        parent_org_id=data.get("parent_org_id"),
    )


def _team_from_dict(data: dict[str, Any]) -> Team:
    members = data.get("member_user_ids") or ()
    return Team(
        team_id=str(data["team_id"]),
        org_id=str(data["org_id"]),
        name=str(data["name"]),
        kind=str(data["kind"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        parent_team_id=data.get("parent_team_id"),
        member_user_ids=tuple(str(x) for x in members),
        metadata=freeze_mapping(data.get("metadata")),
    )


def _member_from_dict(data: dict[str, Any]) -> OrgMember:
    return OrgMember(
        org_id=str(data["org_id"]),
        user_id=str(data["user_id"]),
        role_id=str(data["role_id"]),
        status=str(data["status"]),
        joined_at=str(data["joined_at"]),
        permissions=tuple(str(p) for p in (data.get("permissions") or ())),
        team_ids=tuple(str(t) for t in (data.get("team_ids") or ())),
        display_name=data.get("display_name"),
        email=data.get("email"),
    )


def _invite_from_dict(data: dict[str, Any]) -> Invitation:
    return Invitation(
        invitation_id=str(data["invitation_id"]),
        org_id=str(data["org_id"]),
        email=str(data["email"]),
        role_id=str(data["role_id"]),
        status=str(data["status"]),
        created_at=str(data["created_at"]),
        expires_at=data.get("expires_at"),
        invited_by=data.get("invited_by"),
    )


def _license_from_dict(data: dict[str, Any]) -> License:
    return License(
        license_id=str(data["license_id"]),
        org_id=str(data["org_id"]),
        tier=str(data["tier"]),
        status=str(data["status"]),
        seats=int(data["seats"]),
        created_at=str(data["created_at"]),
        expires_at=data.get("expires_at"),
        usage_limits=freeze_mapping(data.get("usage_limits")),
        metadata=freeze_mapping(data.get("metadata")),
    )


def _api_key_from_dict(data: dict[str, Any]) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=str(data["key_id"]),
        org_id=str(data["org_id"]),
        name=str(data["name"]),
        scopes=tuple(str(s) for s in (data.get("scopes") or ())),
        status=str(data["status"]),
        created_at=str(data["created_at"]),
        secret_hash=str(data.get("secret_hash") or ""),
        expires_at=data.get("expires_at"),
        created_by=data.get("created_by"),
        last_used_at=data.get("last_used_at"),
    )


def _session_from_dict(data: dict[str, Any]) -> OrgSession:
    return OrgSession(
        session_id=str(data["session_id"]),
        org_id=str(data["org_id"]),
        user_id=str(data["user_id"]),
        device_label=str(data.get("device_label") or "unknown"),
        created_at=str(data["created_at"]),
        last_seen_at=str(data["last_seen_at"]),
        status=str(data["status"]),
        ip_hint=data.get("ip_hint"),
        user_agent_hint=data.get("user_agent_hint"),
    )


def _maybe_decode_json_field(raw: Any) -> dict[str, Any] | None:
    if raw is None or raw == "" or raw == "NULL":
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return _decode_payload(raw)
        except Exception:  # noqa: BLE001
            try:
                data = json.loads(raw)
                return data if isinstance(data, dict) else None
            except Exception:  # noqa: BLE001
                return None
    return None


def _audit_from_row(row: dict[str, Any]) -> AuditRecord:
    meta = _maybe_decode_json_field(row.get("metadata")) or {}
    before = _maybe_decode_json_field(row.get("before_state"))
    after = _maybe_decode_json_field(row.get("after_state"))
    return AuditRecord(
        event_id=str(row["event_id"]),
        org_id=row.get("org_id"),
        actor_user_id=row.get("actor_user_id"),
        action=str(row["action"]),
        resource_type=str(row["resource_type"]),
        resource_id=row.get("resource_id"),
        created_at=str(row["created_at"]),
        metadata=freeze_mapping(meta),
        immutable=True,
        before_state=freeze_mapping(before) if before is not None else None,
        after_state=freeze_mapping(after) if after is not None else None,
        ip_address=row.get("ip_address"),
        correlation_id=row.get("correlation_id"),
    )
