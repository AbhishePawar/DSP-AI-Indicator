"""SaaS overlay store — billing profiles / coupons / subscription records only.

Does NOT store organizations, teams, licenses, or API keys (those live in
packages/enterprise). Prefer DatabaseSaasOverlayStore when a DatabasePort is
available (P0-06). Never fabricates payments.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any
from uuid import uuid4

__all__ = [
    "SaasOverlayStore",
    "get_saas_overlay_store",
    "reset_saas_overlay_store_for_tests",
]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class SaasOverlayStore:
    def __init__(self) -> None:
        self._lock = RLock()
        # org_id -> subscription overlay
        self._subscriptions: dict[str, dict[str, Any]] = {}
        # org_id -> billing profile
        self._billing_profiles: dict[str, dict[str, Any]] = {}
        # coupon_code -> coupon
        self._coupons: dict[str, dict[str, Any]] = {}
        # license_key -> record (enterprise license keys for activation)
        self._license_keys: dict[str, dict[str, Any]] = {}
        # razorpay_order_id -> checkout intent (amount locked server-side)
        self._checkout_intents: dict[str, dict[str, Any]] = {}
        # razorpay event id -> processed marker (webhook idempotency)
        self._billing_events: dict[str, dict[str, Any]] = {}
        # razorpay payment id -> processed marker (entitlement idempotency)
        self._processed_payments: dict[str, dict[str, Any]] = {}

    def upsert_subscription(self, org_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            row = self._subscriptions.get(org_id) or {
                "org_id": org_id,
                "created_at": _now(),
            }
            row.update(
                {
                    "plan_id": payload.get("plan_id") or row.get("plan_id"),
                    "status": payload.get("status") or row.get("status") or "trialing",
                    "trial_ends_at": payload.get("trial_ends_at", row.get("trial_ends_at")),
                    "renews_at": payload.get("renews_at", row.get("renews_at")),
                    "coupon_code": payload.get("coupon_code", row.get("coupon_code")),
                    "discount_pct": payload.get("discount_pct", row.get("discount_pct")),
                    "updated_at": _now(),
                }
            )
            self._subscriptions[org_id] = row
            return deepcopy(row)

    def get_subscription(self, org_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._subscriptions.get(org_id)
            return deepcopy(row) if row else None

    def list_subscriptions(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(v) for v in self._subscriptions.values()]

    def upsert_billing_profile(
        self, org_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        with self._lock:
            row = self._billing_profiles.get(org_id) or {
                "org_id": org_id,
                "created_at": _now(),
            }
            row.update(
                {
                    "legal_name": payload.get("legal_name", row.get("legal_name")),
                    "tax_id": payload.get("tax_id", row.get("tax_id")),
                    "tax_regime": payload.get("tax_regime", row.get("tax_regime")),
                    "gstin": payload.get("gstin", row.get("gstin")),
                    "vat_number": payload.get("vat_number", row.get("vat_number")),
                    "billing_email": payload.get(
                        "billing_email", row.get("billing_email")
                    ),
                    "billing_address": payload.get(
                        "billing_address", row.get("billing_address")
                    ),
                    "country": payload.get("country", row.get("country")),
                    "currency": payload.get("currency", row.get("currency")),
                    "updated_at": _now(),
                }
            )
            self._billing_profiles[org_id] = row
            return deepcopy(row)

    def get_billing_profile(self, org_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._billing_profiles.get(org_id)
            return deepcopy(row) if row else None

    def upsert_coupon(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            code = str(payload.get("code") or "").strip().upper()
            if not code:
                raise ValueError("coupon code required")
            row = self._coupons.get(code) or {
                "code": code,
                "created_at": _now(),
            }
            row.update(
                {
                    "discount_pct": payload.get("discount_pct", row.get("discount_pct")),
                    "active": bool(payload.get("active", row.get("active", True))),
                    "expires_at": payload.get("expires_at", row.get("expires_at")),
                    "updated_at": _now(),
                    "note": "Coupon metadata only — no payment applied without billing provider",
                }
            )
            self._coupons[code] = row
            return deepcopy(row)

    def get_coupon(self, code: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._coupons.get(str(code or "").strip().upper())
            return deepcopy(row) if row else None

    def issue_license_key(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = str(payload.get("license_key") or f"DSP-{uuid4().hex[:16].upper()}")
            row = {
                "license_key": key,
                "org_id": payload.get("org_id"),
                "plan_id": payload.get("plan_id") or "enterprise",
                "seats": int(payload.get("seats") or 1),
                "status": payload.get("status") or "issued",
                "expires_at": payload.get("expires_at"),
                "created_at": _now(),
                "activated_at": None,
            }
            self._license_keys[key] = row
            return deepcopy(row)

    def activate_license_key(
        self, license_key: str, *, org_id: str
    ) -> dict[str, Any]:
        with self._lock:
            row = self._license_keys.get(license_key)
            if row is None:
                raise ValueError("license key not found")
            if row.get("status") == "revoked":
                raise ValueError("license key revoked")
            row = dict(row)
            row["org_id"] = org_id
            row["status"] = "active"
            row["activated_at"] = _now()
            self._license_keys[license_key] = row
            return deepcopy(row)

    def get_license_key(self, license_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._license_keys.get(license_key)
            return deepcopy(row) if row else None

    def list_license_keys(self, org_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = [deepcopy(v) for v in self._license_keys.values()]
            if org_id:
                rows = [r for r in rows if r.get("org_id") == org_id]
            return rows

    def record_checkout_intent(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = str(payload.get("order_id") or "").strip()
        if not order_id:
            raise ValueError("order_id required")
        with self._lock:
            row = {
                "order_id": order_id,
                "org_id": str(payload.get("org_id") or ""),
                "plan_id": str(payload.get("plan_id") or ""),
                "amount_paise": int(payload.get("amount_paise") or 0),
                "currency": str(payload.get("currency") or "INR").upper(),
                "actor_user_id": payload.get("actor_user_id"),
                "receipt": payload.get("receipt"),
                "status": str(payload.get("status") or "created"),
                "payment_id": payload.get("payment_id"),
                "created_at": _now(),
                "updated_at": _now(),
            }
            self._checkout_intents[order_id] = row
            return deepcopy(row)

    def get_checkout_intent(self, order_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._checkout_intents.get(str(order_id or "").strip())
            return deepcopy(row) if row else None

    def update_checkout_intent(
        self, order_id: str, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        key = str(order_id or "").strip()
        with self._lock:
            row = self._checkout_intents.get(key)
            if row is None:
                return None
            row = dict(row)
            for field in ("status", "payment_id", "failure_reason"):
                if field in payload:
                    row[field] = payload[field]
            row["updated_at"] = _now()
            self._checkout_intents[key] = row
            return deepcopy(row)

    def has_processed_billing_event(self, event_id: str) -> bool:
        eid = str(event_id or "").strip()
        if not eid:
            return False
        with self._lock:
            return eid in self._billing_events

    def claim_billing_event(
        self, event_id: str, event_name: str | None = None
    ) -> bool:
        """Persist-and-claim a provider event id. True if this caller owns it."""
        eid = str(event_id or "").strip()
        if not eid:
            return True
        with self._lock:
            if eid in self._billing_events:
                return False
            now = _now()
            self._billing_events[eid] = {
                "event_id": eid,
                "event": event_name,
                "created_at": now,
                "updated_at": now,
            }
            return True

    def mark_billing_event_processed(
        self, event_id: str, event_name: str | None = None
    ) -> dict[str, Any]:
        eid = str(event_id or "").strip()
        if not eid:
            raise ValueError("event_id required")
        with self._lock:
            row = self._billing_events.get(eid) or {
                "event_id": eid,
                "created_at": _now(),
            }
            row["event"] = event_name or row.get("event")
            row["updated_at"] = _now()
            self._billing_events[eid] = row
            return deepcopy(row)

    def has_processed_payment(self, payment_id: str) -> bool:
        pid = str(payment_id or "").strip()
        if not pid:
            return False
        with self._lock:
            return pid in self._processed_payments

    def claim_payment(
        self,
        payment_id: str,
        *,
        order_id: str | None = None,
        org_id: str | None = None,
    ) -> bool:
        """Persist-and-claim a provider payment id. True if this caller owns it."""
        pid = str(payment_id or "").strip()
        if not pid:
            return False
        with self._lock:
            if pid in self._processed_payments:
                return False
            now = _now()
            row: dict[str, Any] = {
                "payment_id": pid,
                "created_at": now,
                "updated_at": now,
            }
            if order_id:
                row["order_id"] = order_id
            if org_id:
                row["org_id"] = org_id
            self._processed_payments[pid] = row
            return True

    def mark_payment_processed(
        self, payment_id: str, *, order_id: str | None = None, org_id: str | None = None
    ) -> dict[str, Any]:
        pid = str(payment_id or "").strip()
        if not pid:
            raise ValueError("payment_id required")
        with self._lock:
            row = self._processed_payments.get(pid) or {
                "payment_id": pid,
                "created_at": _now(),
            }
            if order_id:
                row["order_id"] = order_id
            if org_id:
                row["org_id"] = org_id
            row["updated_at"] = _now()
            self._processed_payments[pid] = row
            return deepcopy(row)


_STORE: SaasOverlayStore | None = None


def get_saas_overlay_store(*, database: Any | None = None) -> SaasOverlayStore:
    """Return process singleton — durable when DatabasePort is supplied (P0-06)."""
    global _STORE
    if _STORE is None:
        if database is not None:
            from dsp_platform.saas_platform.db_store import DatabaseSaasOverlayStore

            _STORE = DatabaseSaasOverlayStore(database)
        else:
            _STORE = SaasOverlayStore()
    return _STORE


def reset_saas_overlay_store_for_tests(
    store: SaasOverlayStore | None = None,
) -> SaasOverlayStore:
    global _STORE
    _STORE = store if store is not None else SaasOverlayStore()
    return _STORE


def default_trial_ends(days: int) -> str | None:
    if days <= 0:
        return None
    return (datetime.now(tz=UTC) + timedelta(days=days)).isoformat()
