"""DatabasePort-backed SaaS overlay store (P0-06)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from typing import Any

from dsp_platform.durable_snapshot import (
    ensure_snapshot_table,
    load_snapshot,
    save_snapshot,
)
from dsp_platform.saas_platform.store import SaasOverlayStore

__all__ = [
    "SAAS_SNAPSHOT_TABLE",
    "SAAS_SNAPSHOT_KEY",
    "DatabaseSaasOverlayStore",
    "build_saas_overlay_store",
]

SAAS_SNAPSHOT_TABLE = "saas_overlay_snapshots"
SAAS_SNAPSHOT_KEY = "saas_overlay_v1"

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

    def ensure_fresh(self) -> None:
        with self._persist_lock:
            self.hydrate()

    def export_state(self) -> dict[str, Any]:
        return {
            "subscriptions": dict(self._subscriptions),
            "billing_profiles": dict(self._billing_profiles),
            "coupons": dict(self._coupons),
            "license_keys": dict(self._license_keys),
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

    def hydrate(self) -> None:
        payload = load_snapshot(
            self._db, table=SAAS_SNAPSHOT_TABLE, snapshot_key=SAAS_SNAPSHOT_KEY
        )
        if not payload:
            return
        self.import_state(payload)

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
