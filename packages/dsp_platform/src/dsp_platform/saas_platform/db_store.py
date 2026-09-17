"""DatabasePort-backed SaaS overlay store (P0-06)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from dsp_platform.durable_snapshot import (
    ensure_snapshot_table,
    load_snapshot,
    save_snapshot,
    sql_literal,
)
from dsp_platform.saas_platform.store import SaasOverlayStore

__all__ = [
    "SAAS_SNAPSHOT_TABLE",
    "SAAS_SNAPSHOT_KEY",
    "SAAS_BILLING_EVENT_TABLE",
    "SAAS_BILLING_PAYMENT_TABLE",
    "DatabaseSaasOverlayStore",
    "build_saas_overlay_store",
]

SAAS_SNAPSHOT_TABLE = "saas_overlay_snapshots"
SAAS_SNAPSHOT_KEY = "saas_overlay_v1"
SAAS_BILLING_EVENT_TABLE = "saas_billing_event_keys"
SAAS_BILLING_PAYMENT_TABLE = "saas_billing_payment_keys"

_META = frozenset(
    {
        "ensure_schema",
        "ensure_fresh",
        "hydrate",
        "flush",
        "export_state",
        "import_state",
    }
)


class DatabaseSaasOverlayStore(SaasOverlayStore):
    """SaaS overlay hydrated from / flushed to a shared DatabasePort."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        ensure_snapshot_table(self._db, SAAS_SNAPSHOT_TABLE)
        self._db.execute(
            f"CREATE TABLE IF NOT EXISTS {SAAS_BILLING_EVENT_TABLE} ("
            "event_id TEXT PRIMARY KEY, "
            "provider TEXT NOT NULL, "
            "event_name TEXT, "
            "created_at TEXT NOT NULL"
            ")"
        )
        self._db.execute(
            f"CREATE TABLE IF NOT EXISTS {SAAS_BILLING_PAYMENT_TABLE} ("
            "payment_id TEXT PRIMARY KEY, "
            "provider TEXT NOT NULL, "
            "order_id TEXT, "
            "org_id TEXT, "
            "created_at TEXT NOT NULL"
            ")"
        )

    def ensure_fresh(self) -> None:
        with self._persist_lock:
            self.hydrate()

    def export_state(self) -> dict[str, Any]:
        return {
            "subscriptions": dict(self._subscriptions),
            "billing_profiles": dict(self._billing_profiles),
            "coupons": dict(self._coupons),
            "license_keys": dict(self._license_keys),
            "checkout_intents": dict(self._checkout_intents),
            "billing_events": dict(self._billing_events),
            "processed_payments": dict(self._processed_payments),
        }

    def import_state(self, payload: dict[str, Any]) -> None:
        self._subscriptions = {
            str(k): dict(v) for k, v in (payload.get("subscriptions") or {}).items()
        }
        self._billing_profiles = {
            str(k): dict(v)
            for k, v in (payload.get("billing_profiles") or {}).items()
        }
        self._coupons = {
            str(k): dict(v) for k, v in (payload.get("coupons") or {}).items()
        }
        self._license_keys = {
            str(k): dict(v) for k, v in (payload.get("license_keys") or {}).items()
        }
        self._checkout_intents = {
            str(k): dict(v)
            for k, v in (payload.get("checkout_intents") or {}).items()
        }
        self._billing_events = {
            str(k): dict(v) for k, v in (payload.get("billing_events") or {}).items()
        }
        self._processed_payments = {
            str(k): dict(v)
            for k, v in (payload.get("processed_payments") or {}).items()
        }

    def hydrate(self) -> None:
        payload = load_snapshot(
            self._db, table=SAAS_SNAPSHOT_TABLE, snapshot_key=SAAS_SNAPSHOT_KEY
        )
        if payload:
            self.import_state(payload)
        self._merge_billing_keys_from_sql()

    def claim_billing_event(
        self, event_id: str, event_name: str | None = None
    ) -> bool:
        eid = str(event_id or "").strip()
        if not eid:
            return True
        if self._sql_has(SAAS_BILLING_EVENT_TABLE, "event_id", eid):
            return False
        claimed = super().claim_billing_event(event_id, event_name)
        if not claimed:
            return False
        self._insert_event_key(eid, event_name)
        return True

    def has_processed_billing_event(self, event_id: str) -> bool:
        if super().has_processed_billing_event(event_id):
            return True
        eid = str(event_id or "").strip()
        if not eid:
            return False
        return self._sql_has(SAAS_BILLING_EVENT_TABLE, "event_id", eid)

    def mark_billing_event_processed(
        self, event_id: str, event_name: str | None = None
    ) -> dict[str, Any]:
        row = super().mark_billing_event_processed(event_id, event_name)
        eid = str(event_id or "").strip()
        if eid and not self._sql_has(SAAS_BILLING_EVENT_TABLE, "event_id", eid):
            self._insert_event_key(eid, event_name)
        return row

    def claim_payment(
        self,
        payment_id: str,
        *,
        order_id: str | None = None,
        org_id: str | None = None,
    ) -> bool:
        pid = str(payment_id or "").strip()
        if not pid:
            return False
        if self._sql_has(SAAS_BILLING_PAYMENT_TABLE, "payment_id", pid):
            return False
        claimed = super().claim_payment(
            payment_id, order_id=order_id, org_id=org_id
        )
        if not claimed:
            return False
        self._insert_payment_key(pid, order_id=order_id, org_id=org_id)
        return True

    def has_processed_payment(self, payment_id: str) -> bool:
        if super().has_processed_payment(payment_id):
            return True
        pid = str(payment_id or "").strip()
        if not pid:
            return False
        return self._sql_has(SAAS_BILLING_PAYMENT_TABLE, "payment_id", pid)

    def mark_payment_processed(
        self, payment_id: str, *, order_id: str | None = None, org_id: str | None = None
    ) -> dict[str, Any]:
        row = super().mark_payment_processed(
            payment_id, order_id=order_id, org_id=org_id
        )
        pid = str(payment_id or "").strip()
        if pid and not self._sql_has(SAAS_BILLING_PAYMENT_TABLE, "payment_id", pid):
            self._insert_payment_key(pid, order_id=order_id, org_id=org_id)
        return row

    def _merge_billing_keys_from_sql(self) -> None:
        for row in self._db.fetchall(f"SELECT * FROM {SAAS_BILLING_EVENT_TABLE}"):
            eid = str(row.get("event_id") or "").strip()
            if not eid:
                continue
            existing = self._billing_events.get(eid) or {}
            existing.update(
                {
                    "event_id": eid,
                    "event": row.get("event_name") or existing.get("event"),
                    "created_at": row.get("created_at") or existing.get("created_at"),
                }
            )
            self._billing_events[eid] = existing
        for row in self._db.fetchall(f"SELECT * FROM {SAAS_BILLING_PAYMENT_TABLE}"):
            pid = str(row.get("payment_id") or "").strip()
            if not pid:
                continue
            existing = self._processed_payments.get(pid) or {}
            existing.update(
                {
                    "payment_id": pid,
                    "order_id": row.get("order_id") or existing.get("order_id"),
                    "org_id": row.get("org_id") or existing.get("org_id"),
                    "created_at": row.get("created_at") or existing.get("created_at"),
                }
            )
            self._processed_payments[pid] = existing

    def _sql_has(self, table: str, key: str, value: str) -> bool:
        rows = self._db.fetchall(f"SELECT * FROM {table}")
        return any(str(row.get(key) or "").strip() == value for row in rows)

    def _insert_event_key(self, event_id: str, event_name: str | None) -> None:
        created_at = datetime.now(tz=UTC).isoformat()
        self._db.execute(
            f"INSERT INTO {SAAS_BILLING_EVENT_TABLE} "
            "(event_id, provider, event_name, created_at) VALUES ("
            f"{sql_literal(event_id)}, 'razorpay', "
            f"{sql_literal(event_name or '')}, {sql_literal(created_at)})"
        )

    def _insert_payment_key(
        self,
        payment_id: str,
        *,
        order_id: str | None,
        org_id: str | None,
    ) -> None:
        created_at = datetime.now(tz=UTC).isoformat()
        self._db.execute(
            f"INSERT INTO {SAAS_BILLING_PAYMENT_TABLE} "
            "(payment_id, provider, order_id, org_id, created_at) VALUES ("
            f"{sql_literal(payment_id)}, 'razorpay', "
            f"{sql_literal(order_id or '')}, {sql_literal(org_id or '')}, "
            f"{sql_literal(created_at)})"
        )

    def flush(self) -> None:
        with self._persist_lock:
            save_snapshot(
                self._db,
                table=SAAS_SNAPSHOT_TABLE,
                snapshot_key=SAAS_SNAPSHOT_KEY,
                payload=self.export_state(),
                updated_at=datetime.now(tz=UTC).isoformat(),
            )

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_") or name in _META:
            return object.__getattribute__(self, name)
        attr = object.__getattribute__(self, name)
        if not callable(attr):
            return attr

        def bound(*args: Any, **kwargs: Any) -> Any:
            object.__getattribute__(self, "ensure_fresh")()
            result = attr(*args, **kwargs)
            object.__getattribute__(self, "flush")()
            return result

        return bound


def build_saas_overlay_store(database: Any | None = None) -> SaasOverlayStore:
    if database is None:
        return SaasOverlayStore()
    return DatabaseSaasOverlayStore(database)
