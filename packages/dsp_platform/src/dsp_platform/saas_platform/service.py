"""RC1 Milestone 9 — Commercial SaaS Platform orchestration.

Reuses packages/enterprise (orgs, teams, licenses, API keys, usage, audit,
billing ports). Never duplicates authentication, organizations, or payments.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping
from uuid import uuid4

from dsp_platform.saas_platform.plans import (
    PLAN_IDS,
    PLAN_TO_LICENSE_TIER,
    SAAS_PLANS,
    compare_plans,
    get_plan,
    plan_feature_flags,
    plan_limits,
    resolve_plan_checkout_price,
)
from dsp_platform.saas_platform.store import (
    default_trial_ends,
    get_saas_overlay_store,
)

UNAVAILABLE_MESSAGE = "Data unavailable."
SAAS_SCHEMA_VERSION = "1.0.0"
SAAS_SERVICE_VERSION = "0.1.0"
_LOG = logging.getLogger(__name__)
_RAZORPAY_ENTITLEMENT_EVENTS = frozenset({"payment.captured", "order.paid"})
_RAZORPAY_LIFECYCLE_EVENTS = frozenset(
    {
        "payment.authorized",
        "payment.captured",
        "payment.failed",
        "order.paid",
    }
)

DEFAULT_ORG_PREFERENCES = {
    "timezone": "UTC",
    "country": None,
    "currency": "USD",
    "language": "en",
    "market": None,
    "date_format": "YYYY-MM-DD",
    "number_format": "en-US",
    "default_dashboard": "/dashboards/research",
    "default_landing_page": "/dashboard",
    "email_settings": {},
    "notification_settings": {},
}

DEFAULT_BRANDING = {
    "logo_url": None,
    "primary_color": None,
    "theme": "system",
    "workspace_name": None,
}


def saas_platform_schema() -> dict[str, Any]:
    return {
        "schema_version": SAAS_SCHEMA_VERSION,
        "service_version": SAAS_SERVICE_VERSION,
        "plans": [p["plan_id"] for p in SAAS_PLANS],
        "plan_to_license_tier": dict(PLAN_TO_LICENSE_TIER),
        "routes": [
            "/saas/schema",
            "/saas/organizations",
            "/saas/organization",
            "/saas/subscription",
            "/saas/license",
            "/saas/api-key",
            "/saas/usage",
            "/saas/dashboard",
            "/saas/billing",
            "/saas/plans",
            "/saas/team",
            "/saas/settings",
            "/saas/checkout",
            "/saas/checkout/verify",
            "/saas/webhooks/razorpay",
        ],
        "rules": [
            "orchestration_only",
            "reuse_enterprise_organizations",
            "reuse_enterprise_iam",
            "reuse_billing_port_no_fake_payments",
            "reuse_audit_logger",
            "feature_limits_via_plans_and_flags",
            "missing_is_data_unavailable",
        ],
        "engines_reused": [
            "enterprise.EnterpriseService",
            "enterprise.BillingPort",
            "auth.EnterpriseAuthPlatform",
            "enterprise_dashboards",
            "research_workspace",
            "portfolio_intelligence",
            "copilot_v2",
            "feature_flags",
        ],
        "billing_note": "Razorpay checkout is live only when DSP_BILLING_PROVIDER=razorpay and credentials plus webhook secret are configured. Null/Stripe/Paddle remain unavailable.",
    }


def _json_safe(value: Any) -> Any:
    """Convert MappingProxy / nested mappings to plain JSON-safe structures."""
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def run_saas_platform(
    action: str,
    *,
    platform: Any = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch a SaaS platform action — delegates domain work to enterprise."""
    body = dict(payload or {})
    act = (action or "").strip().lower().replace("-", "_")
    enterprise = _enterprise()
    overlay = get_saas_overlay_store()

    handlers = {
        "schema": lambda: saas_platform_schema(),
        "plans": lambda: compare_plans(),
        "dashboard": lambda: _admin_dashboard(enterprise, overlay, body),
        "list_organizations": lambda: {
            "organizations": enterprise.list_organizations(
                user_id=body.get("user_id") or body.get("actor_user_id")
            )
        },
        "get_organization": lambda: _require_org(
            enterprise, str(body.get("org_id") or ""), _actor(body)
        ),
        "create_organization": lambda: _create_org(enterprise, overlay, body),
        "update_organization": lambda: _update_org(enterprise, body),
        "archive_organization": lambda: _archive_org(enterprise, body),
        "delete_organization": lambda: _delete_org(enterprise, body),
        "organization_settings": lambda: _org_settings(enterprise, body),
        "update_settings": lambda: _update_settings(enterprise, body),
        "create_team": lambda: {
            "team": enterprise.create_team(
                str(body.get("org_id") or ""),
                name=str(body.get("name") or "Team"),
                kind=str(body.get("kind") or "custom"),
                actor_user_id=_actor(body),
                parent_team_id=body.get("parent_team_id"),
            )
        },
        "list_teams": lambda: {
            "teams": enterprise.list_teams(
                str(body.get("org_id") or ""), actor_user_id=_actor(body)
            )
        },
        "invite_member": lambda: {
            "invitation": enterprise.invite_member(
                str(body.get("org_id") or ""),
                email=str(body.get("email") or ""),
                role_id=str(body.get("role_id") or "analyst"),
                actor_user_id=_actor(body),
            )
        },
        "add_member": lambda: {
            "member": enterprise.add_member(
                str(body.get("org_id") or ""),
                user_id=str(body.get("user_id") or ""),
                role_id=str(body.get("role_id") or "analyst"),
                actor_user_id=_actor(body),
                display_name=body.get("display_name"),
                email=body.get("email"),
            )
        },
        "list_members": lambda: {
            "members": enterprise.list_members(
                str(body.get("org_id") or ""), actor_user_id=_actor(body)
            )
        },
        "list_roles": lambda: {
            "roles": enterprise.list_roles(
                str(body.get("org_id") or ""), actor_user_id=_actor(body)
            )
        },
        "create_subscription": lambda: _create_subscription(
            enterprise, overlay, body
        ),
        "get_subscription": lambda: _get_subscription(enterprise, overlay, body),
        "billing_profile": lambda: _billing_profile(enterprise, overlay, body),
        "upsert_billing_profile": lambda: _upsert_billing_profile(
            enterprise, overlay, body
        ),
        "billing_status": lambda: enterprise.billing_status(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "list_invoices": lambda: enterprise.list_invoices(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "checkout": lambda: _checkout(enterprise, overlay, body),
        "checkout_verify": lambda: _checkout_verify(enterprise, overlay, body),
        "upsert_coupon": lambda: {"coupon": overlay.upsert_coupon(body)},
        "get_coupon": lambda: {
            "coupon": overlay.get_coupon(str(body.get("code") or ""))
            or {"available": False, "message": UNAVAILABLE_MESSAGE}
        },
        "assign_license": lambda: _assign_license(enterprise, overlay, body),
        "issue_license_key": lambda: {
            "license_key": overlay.issue_license_key(body)
        },
        "activate_license": lambda: _activate_license(enterprise, overlay, body),
        "get_license": lambda: enterprise.get_license(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "validate_license": lambda: (
            enterprise.require_permission(
                str(body.get("org_id") or ""), _actor(body), "license.view"
            ),
            enterprise.validate_license(str(body.get("org_id") or "")),
        )[1],
        "create_api_key": lambda: {
            "api_key": enterprise.create_api_key(
                str(body.get("org_id") or ""),
                name=str(body.get("name") or "API key"),
                scopes=list(body.get("scopes") or ["org.view", "usage.view"]),
                actor_user_id=_actor(body),
                expires_at=body.get("expires_at"),
            )
        },
        "list_api_keys": lambda: {
            "api_keys": enterprise.list_api_keys(
                str(body.get("org_id") or ""), actor_user_id=_actor(body)
            )
        },
        "rotate_api_key": lambda: {
            "api_key": enterprise.rotate_api_key(
                str(body.get("org_id") or ""),
                str(body.get("key_id") or body.get("api_key_id") or ""),
                actor_user_id=_actor(body),
            )
        },
        "revoke_api_key": lambda: {
            "api_key": enterprise.disable_api_key(
                str(body.get("org_id") or ""),
                str(body.get("key_id") or body.get("api_key_id") or ""),
                actor_user_id=_actor(body),
            )
        },
        "record_usage": lambda: _record_usage(enterprise, body),
        "usage": lambda: enterprise.usage_snapshot(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "feature_limits": lambda: _feature_limits(enterprise, overlay, body),
        "customer_portal": lambda: enterprise.customer_portal(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "list_audit": lambda: {
            "audit": enterprise.list_audit(
                str(body.get("org_id") or ""),
                actor_user_id=_actor(body),
            )
        },
    }

    if act not in handlers:
        raise ValueError(f"Unknown saas action: {action!r}")
    try:
        result = handlers[act]()
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001
        # Map enterprise domain errors to honest envelopes
        name = type(exc).__name__
        if name in {"ValidationError", "NotFoundError", "ForbiddenError", "EnterpriseError"}:
            return {
                "ok": False,
                "action": act,
                "message": UNAVAILABLE_MESSAGE,
                "error": str(exc),
                "error_type": name,
            }
        return {
            "ok": False,
            "action": act,
            "message": UNAVAILABLE_MESSAGE,
            "error": str(exc),
        }
    return {
        "ok": True,
        "action": act,
        "result": _json_safe(result),
        "message": None,
        "provenance": {
            "schema_version": SAAS_SCHEMA_VERSION,
            "service_version": SAAS_SERVICE_VERSION,
            "orchestration_only": True,
            "domain": "enterprise",
            "payments_executed": False,
        },
    }


def _enterprise() -> Any:
    from enterprise import get_enterprise_service

    return get_enterprise_service()


def _actor(body: dict[str, Any]) -> str:
    actor = str(body.get("actor_user_id") or body.get("user_id") or "").strip()
    if not actor:
        raise ValueError("actor_user_id required")
    return actor


def _require_org(
    enterprise: Any, org_id: str, actor: str | None = None
) -> dict[str, Any]:
    """Resolve org; with actor enforce membership (P1-07)."""
    if actor:
        org = enterprise.get_organization(org_id, actor_user_id=actor)
    else:
        org = enterprise.get_organization(org_id)
    if org is None:
        raise ValueError("organization not found")
    return {"organization": org}


def _merge_prefs(incoming: dict[str, Any] | None) -> dict[str, Any]:
    prefs = dict(DEFAULT_ORG_PREFERENCES)
    if incoming:
        prefs.update(incoming)
    return prefs


def _merge_branding(incoming: dict[str, Any] | None) -> dict[str, Any]:
    branding = dict(DEFAULT_BRANDING)
    if incoming:
        branding.update(incoming)
    return branding


def _create_org(enterprise: Any, overlay: Any, body: dict[str, Any]) -> dict[str, Any]:
    org = enterprise.create_organization(
        name=str(body.get("name") or ""),
        slug=str(body.get("slug") or ""),
        owner_user_id=str(body.get("owner_user_id") or body.get("actor_user_id") or ""),
        org_id=body.get("org_id"),
        seat_limit=body.get("seat_limit"),
        branding=_merge_branding(body.get("branding")),
        preferences=_merge_prefs(body.get("preferences")),
        metadata=body.get("metadata"),
    )
    plan_id = str(body.get("plan_id") or "starter").lower()
    if plan_id in PLAN_IDS:
        _create_subscription(
            enterprise,
            overlay,
            {
                "org_id": org["org_id"],
                "plan_id": plan_id,
                "actor_user_id": org["owner_user_id"],
                "status": "trialing",
            },
        )
    return {"organization": org}


def _update_org(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    org = enterprise.update_organization(
        str(body.get("org_id") or ""),
        actor_user_id=_actor(body),
        name=body.get("name"),
        status=body.get("status"),
        branding=body.get("branding"),
        preferences=body.get("preferences"),
        metadata=body.get("metadata"),
        seat_limit=body.get("seat_limit"),
    )
    return {"organization": org}


def _archive_org(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    org = enterprise.update_organization(
        str(body.get("org_id") or ""),
        actor_user_id=_actor(body),
        status="archived",
    )
    return {"organization": org, "archived": True}


def _delete_org(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    """Soft-delete: archive org. Hard removal is not fabricated for active orgs."""
    org_id = str(body.get("org_id") or "")
    actor = _actor(body)
    org = enterprise.get_organization(org_id, actor_user_id=actor)
    if org is None:
        raise ValueError("organization not found")
    hard = bool(body.get("hard"))
    if org.get("status") != "archived" and not hard:
        org = enterprise.update_organization(
            org_id, actor_user_id=actor, status="archived"
        )
        return {
            "organization": org,
            "deleted": False,
            "archived": True,
            "message": "Organization archived. Pass hard=true only for archived orgs.",
        }
    # Hard delete via store (enterprise domain) when already archived or hard=true
    try:
        if hasattr(enterprise, "delete_organization"):
            enterprise.delete_organization(org_id, actor_user_id=actor)
        else:
            # Fallback: mark metadata deleted — never invent a parallel org store
            meta = dict(org.get("metadata") or {})
            meta["deleted"] = True
            org = enterprise.update_organization(
                org_id,
                actor_user_id=actor,
                status="archived",
                metadata=meta,
            )
            return {
                "organization": org,
                "deleted": True,
                "hard": False,
                "message": "Marked deleted in metadata (soft).",
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "organization": org,
            "deleted": False,
            "message": UNAVAILABLE_MESSAGE,
            "error": str(exc),
        }
    return {"organization": None, "deleted": True, "org_id": org_id}


def _org_settings(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    actor = _actor(body)
    org = enterprise.get_organization(
        str(body.get("org_id") or ""), actor_user_id=actor
    )
    if org is None:
        raise ValueError("organization not found")
    return {
        "org_id": org["org_id"],
        "branding": org.get("branding") or DEFAULT_BRANDING,
        "preferences": org.get("preferences") or DEFAULT_ORG_PREFERENCES,
        "seat_limit": org.get("seat_limit"),
        "status": org.get("status"),
    }


def _update_settings(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    actor = _actor(body)
    existing = enterprise.get_organization(org_id, actor_user_id=actor)
    if existing is None:
        raise ValueError("organization not found")
    branding = dict(existing.get("branding") or {})
    prefs = dict(existing.get("preferences") or {})
    if body.get("branding"):
        branding.update(body["branding"])
    if body.get("preferences"):
        prefs.update(body["preferences"])
    # Flatten common settings fields into preferences/branding
    for key in (
        "timezone",
        "country",
        "currency",
        "language",
        "market",
        "date_format",
        "number_format",
        "default_dashboard",
        "default_landing_page",
        "email_settings",
        "notification_settings",
    ):
        if key in body:
            prefs[key] = body[key]
    for key in ("logo_url", "primary_color", "theme", "workspace_name"):
        if key in body:
            branding[key] = body[key]
    org = enterprise.update_organization(
        org_id,
        actor_user_id=_actor(body),
        branding=branding,
        preferences=prefs,
        name=body.get("name"),
    )
    return {"organization": org, "settings": _org_settings(enterprise, body)}


def _create_subscription(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    plan_id = str(body.get("plan_id") or "starter").lower()
    if plan_id not in PLAN_IDS:
        raise ValueError(f"invalid plan_id: {plan_id}")
    plan = get_plan(plan_id) or {}
    # P1-07 — authorize before any overlay mutation (no cross-tenant write).
    actor = str(body.get("actor_user_id") or body.get("owner_user_id") or "").strip()
    if not actor:
        raise ValueError("actor_user_id required")
    enterprise.require_permission(org_id, actor, "license.manage")

    status = str(body.get("status") or "trialing")
    trial_ends = body.get("trial_ends_at")
    if status == "trialing" and not trial_ends:
        trial_ends = default_trial_ends(int(plan.get("trial_days") or 0))

    coupon_code = body.get("coupon_code")
    discount_pct = body.get("discount_pct")
    if coupon_code:
        coupon = overlay.get_coupon(str(coupon_code))
        if coupon and coupon.get("active"):
            discount_pct = coupon.get("discount_pct", discount_pct)

    sub = overlay.upsert_subscription(
        org_id,
        {
            "plan_id": plan_id,
            "status": status,
            "trial_ends_at": trial_ends,
            "renews_at": body.get("renews_at"),
            "coupon_code": coupon_code,
            "discount_pct": discount_pct,
        },
    )

    tier = PLAN_TO_LICENSE_TIER[plan_id]
    seats = body.get("seats") or plan.get("seat_limit") or 1
    license_row = enterprise.assign_license(
        org_id,
        tier=tier,
        seats=int(seats),
        actor_user_id=actor,
        expires_at=body.get("expires_at") or trial_ends,
        usage_limits=plan_limits(plan_id),
    )
    try:
        enterprise.update_organization(
            org_id,
            actor_user_id=actor,
            seat_limit=int(seats) if seats else None,
        )
    except Exception:  # noqa: BLE001
        pass

    billing = None
    try:
        billing = enterprise.billing_status(org_id, actor_user_id=actor)
    except Exception:  # noqa: BLE001
        billing = {
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
            "status": "unavailable",
        }

    return {
        "subscription": sub,
        "plan": plan,
        "license": license_row,
        "feature_flags": dict(plan_feature_flags(plan_id)),
        "billing": billing,
        "payments_executed": False,
        "note": "Subscription recorded locally; checkout requires a configured billing provider.",
    }


def _get_subscription(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    actor = str(body.get("actor_user_id") or body.get("user_id") or "").strip()
    if actor:
        enterprise.require_permission(org_id, actor, "org.view")
    sub = overlay.get_subscription(org_id)
    if sub is None:
        return {
            "available": False,
            "subscription": None,
            "message": UNAVAILABLE_MESSAGE,
        }
    plan = get_plan(str(sub.get("plan_id") or ""))
    return {
        "available": True,
        "subscription": sub,
        "plan": plan,
        "feature_flags": dict(plan_feature_flags(str(sub.get("plan_id") or ""))),
        "limits": plan_limits(str(sub.get("plan_id") or "")),
    }


def _billing_profile(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    enterprise.require_permission(org_id, _actor(body), "billing.view")
    profile = overlay.get_billing_profile(org_id)
    if profile is None:
        return {
            "available": False,
            "profile": None,
            "message": UNAVAILABLE_MESSAGE,
        }
    return {"available": True, "profile": profile}


def _upsert_billing_profile(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    enterprise.require_permission(org_id, _actor(body), "billing.view")
    return {
        "profile": overlay.upsert_billing_profile(org_id, body),
    }


def _checkout(enterprise: Any, overlay: Any, body: dict[str, Any]) -> dict[str, Any]:
    """Create a provider order. Amount/currency are resolved server-side only."""
    org_id = str(body.get("org_id") or "")
    plan_id = str(body.get("plan_id") or "").strip().lower()
    actor = str(body.get("actor_user_id") or body.get("user_id") or "").strip()
    billing = getattr(enterprise, "billing", None)
    if billing is None or not hasattr(billing, "create_checkout_session"):
        return {
            "ok": False,
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "Billing provider unavailable.",
        }
    if not billing.is_available():
        if actor:
            enterprise.require_permission(org_id, actor, "billing.view")
        return billing.create_checkout_session(org_id, plan=plan_id or None)
    if not actor:
        raise ValueError("actor_user_id required")
    enterprise.require_permission(org_id, actor, "billing.view")

    price = resolve_plan_checkout_price(plan_id)
    if price is None:
        return {
            "ok": False,
            "available": False,
            "checkout_enabled": False,
            "message": "Unable to calculate.",
            "detail": "Plan is not available for purchase.",
        }

    receipt = f"dsp_{uuid4().hex[:24]}"
    notes = {
        "org_id": org_id,
        "plan_id": plan_id,
        "actor_user_id": actor,
    }
    created = billing.create_checkout_session(
        org_id,
        plan=plan_id,
        amount_paise=price["amount_paise"],
        currency=price["currency"],
        receipt=receipt,
        notes=notes,
    )
    order_id = str(created.get("order_id") or "").strip()
    if not created.get("ok") or not order_id:
        created.pop("key_secret", None)
        created.pop("webhook_secret", None)
        return created
    overlay.record_checkout_intent(
        {
            "order_id": order_id,
            "org_id": org_id,
            "plan_id": plan_id,
            "amount_paise": price["amount_paise"],
            "currency": price["currency"],
            "actor_user_id": actor,
            "receipt": receipt,
            "status": "created",
        }
    )
    return {
        "ok": True,
        "available": True,
        "provider": created.get("provider") or billing.provider_name(),
        "key_id": created.get("key_id"),
        "order_id": order_id,
        "amount": price["amount_paise"],
        "currency": price["currency"],
        "plan_id": plan_id,
    }


def _checkout_verify(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    """Verify Checkout HMAC, then entitle only if the payment is captured."""
    actor = _actor(body)
    order_id = str(body.get("razorpay_order_id") or "").strip()
    payment_id = str(body.get("razorpay_payment_id") or "").strip()
    signature = str(body.get("razorpay_signature") or "").strip()
    billing = getattr(enterprise, "billing", None)
    if billing is None or not hasattr(billing, "verify_checkout_signature"):
        return {
            "ok": False,
            "verified": False,
            "message": "Billing provider unavailable.",
        }
    if not billing.is_available():
        return billing.verify_checkout_signature(
            order_id=order_id, payment_id=payment_id, signature=signature
        )
    check = billing.verify_checkout_signature(
        order_id=order_id, payment_id=payment_id, signature=signature
    )
    if not check.get("verified"):
        return {
            "ok": False,
            "verified": False,
            "entitled": False,
            "message": check.get("message") or "Invalid payment signature.",
        }
    intent = overlay.get_checkout_intent(order_id)
    if intent is None:
        return {
            "ok": False,
            "verified": True,
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "checkout intent not found",
        }
    intent_org = str(intent.get("org_id") or "")
    claimed_org = str(body.get("org_id") or "").strip()
    if claimed_org and claimed_org != intent_org:
        return {
            "ok": False,
            "verified": True,
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "organization mismatch",
        }
    enterprise.require_permission(intent_org, actor, "billing.view")
    payment_entity: dict[str, Any] = {}
    if hasattr(billing, "fetch_payment"):
        fetched = billing.fetch_payment(payment_id)
        if not isinstance(fetched, dict) or not fetched.get("ok"):
            return {
                "ok": False,
                "verified": True,
                "entitled": False,
                "message": UNAVAILABLE_MESSAGE,
                "detail": "payment unavailable",
            }
        inner = fetched.get("payment")
        if isinstance(inner, dict):
            payment_entity = inner
    paid_order = str(payment_entity.get("order_id") or "").strip()
    if not paid_order or paid_order != order_id:
        return {
            "ok": False,
            "verified": True,
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "order mismatch",
        }
    status = str(payment_entity.get("status") or "").strip().lower()
    if status != "captured":
        return {
            "ok": True,
            "verified": True,
            "entitled": False,
            "pending": True,
            "status": status or "pending",
            "message": "Payment not captured yet.",
        }
    mismatch = _amount_mismatch(intent, payment_entity)
    if mismatch is not None:
        return mismatch
    applied = _apply_paid_entitlement(
        enterprise,
        overlay,
        order_id=order_id,
        payment_id=payment_id,
        source_event="checkout.verify",
    )
    applied["ok"] = True
    applied["verified"] = True
    return applied


def _payment_entity(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payment = payload.get("payment") if isinstance(payload, dict) else None
    if isinstance(payment, dict):
        entity = payment.get("entity")
        if isinstance(entity, dict):
            return entity
        if payment.get("id"):
            return payment
    return {}


def _order_entity(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    order = payload.get("order") if isinstance(payload, dict) else None
    if isinstance(order, dict):
        entity = order.get("entity")
        if isinstance(entity, dict):
            return entity
        if order.get("id"):
            return order
    return {}


def _amount_mismatch(
    intent: dict[str, Any], entity: Mapping[str, Any]
) -> dict[str, Any] | None:
    rejected = {
        "ok": False,
        "verified": True,
        "entitled": False,
        "message": "Unable to calculate.",
        "detail": "Payment amount mismatch.",
    }
    if "amount" not in entity or "currency" not in entity:
        return rejected
    try:
        paid = int(entity.get("amount") or 0)
    except (TypeError, ValueError):
        return rejected
    expected = int(intent.get("amount_paise") or 0)
    currency = str(entity.get("currency") or "").strip().upper()
    expected_ccy = str(intent.get("currency") or "").strip().upper()
    if paid != expected or not currency or not expected_ccy or currency != expected_ccy:
        return rejected
    return None


def _apply_paid_entitlement(
    enterprise: Any,
    overlay: Any,
    *,
    order_id: str,
    payment_id: str,
    source_event: str,
) -> dict[str, Any]:
    intent = overlay.get_checkout_intent(order_id)
    if overlay.has_processed_payment(payment_id):
        return {
            "entitled": True,
            "duplicate": True,
            "org_id": (intent or {}).get("org_id"),
            "plan_id": (intent or {}).get("plan_id"),
            "payment_id": payment_id,
            "order_id": order_id,
        }
    if intent is None:
        return {
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "checkout intent not found",
        }
    if str(intent.get("status") or "") == "entitled":
        overlay.mark_payment_processed(
            payment_id, order_id=order_id, org_id=str(intent.get("org_id") or "")
        )
        return {
            "entitled": True,
            "duplicate": True,
            "org_id": intent.get("org_id"),
            "plan_id": intent.get("plan_id"),
            "payment_id": payment_id,
            "order_id": order_id,
        }
    org_id = str(intent.get("org_id") or "")
    plan_id = str(intent.get("plan_id") or "").strip().lower()
    plan = get_plan(plan_id) or {}
    tier = PLAN_TO_LICENSE_TIER.get(plan_id)
    if not org_id or not tier:
        return {
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "plan or organization unavailable",
        }
    if not overlay.claim_payment(payment_id, order_id=order_id, org_id=org_id):
        return {
            "entitled": True,
            "duplicate": True,
            "org_id": org_id,
            "plan_id": plan_id,
            "payment_id": payment_id,
            "order_id": order_id,
        }
    seats = int(plan.get("seat_limit") or 1)
    overlay.upsert_subscription(
        org_id,
        {
            "plan_id": plan_id,
            "status": "active",
            "coupon_code": None,
        },
    )
    license_row = enterprise.apply_paid_license(
        org_id,
        tier=str(tier),
        seats=seats,
        usage_limits=plan_limits(plan_id),
        metadata={
            "source": "razorpay",
            "provider": "razorpay",
            "order_id": order_id,
            "payment_id": payment_id,
            "event": source_event,
        },
    )
    org = enterprise.get_organization(org_id)
    owner = str((org or {}).get("owner_user_id") or "")
    if owner:
        try:
            enterprise.update_organization(
                org_id, actor_user_id=owner, seat_limit=seats
            )
        except Exception:  # noqa: BLE001 — license already applied
            pass
    overlay.update_checkout_intent(
        order_id, {"status": "entitled", "payment_id": payment_id}
    )
    overlay.mark_payment_processed(payment_id, order_id=order_id, org_id=org_id)
    return {
        "entitled": True,
        "duplicate": False,
        "org_id": org_id,
        "plan_id": plan_id,
        "payment_id": payment_id,
        "order_id": order_id,
        "license": license_row,
    }


def _handle_razorpay_event(
    enterprise: Any, overlay: Any, event: dict[str, Any]
) -> dict[str, Any]:
    event_name = str(event.get("event") or "").strip()
    payment = _payment_entity(event)
    order = _order_entity(event)
    order_id = str(
        payment.get("order_id") or order.get("id") or ""
    ).strip()
    payment_id = str(payment.get("id") or "").strip()

    if event_name not in _RAZORPAY_LIFECYCLE_EVENTS:
        return {"handled": False, "ignored": True, "reason": "event not implemented"}

    if event_name == "payment.authorized":
        if order_id:
            overlay.update_checkout_intent(
                order_id, {"status": "authorized", "payment_id": payment_id or None}
            )
        return {"handled": True, "entitled": False, "status": "authorized"}

    if event_name == "payment.failed":
        if order_id:
            overlay.update_checkout_intent(
                order_id,
                {
                    "status": "failed",
                    "payment_id": payment_id or None,
                    "failure_reason": str(payment.get("error_description") or "failed"),
                },
            )
        return {"handled": True, "entitled": False, "status": "failed"}

    if event_name not in _RAZORPAY_ENTITLEMENT_EVENTS:
        return {"handled": True, "entitled": False}

    if not order_id:
        return {
            "handled": True,
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "order_id missing",
        }
    intent = overlay.get_checkout_intent(order_id)
    if intent is None:
        return {
            "handled": True,
            "entitled": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "checkout intent not found",
        }
    entity_for_amount = payment or order
    mismatch = _amount_mismatch(intent, entity_for_amount)
    if mismatch is not None:
        overlay.update_checkout_intent(
            order_id, {"status": "amount_mismatch", "payment_id": payment_id or None}
        )
        return mismatch
    if not payment_id:
        payment_id = f"order:{order_id}"
    applied = _apply_paid_entitlement(
        enterprise,
        overlay,
        order_id=order_id,
        payment_id=payment_id,
        source_event=event_name,
    )
    applied["handled"] = True
    return applied


def handle_razorpay_webhook(
    raw_body: bytes,
    signature: str | None,
    *,
    enterprise: Any | None = None,
    overlay: Any | None = None,
) -> dict[str, Any]:
    """Verify Razorpay webhook HMAC and apply entitlements idempotently."""
    enterprise = enterprise or _enterprise()
    overlay = overlay or get_saas_overlay_store()
    billing = getattr(enterprise, "billing", None)
    if billing is None or not hasattr(billing, "verify_webhook"):
        return {
            "ok": False,
            "verified": False,
            "message": "Billing provider unavailable.",
        }
    verification = billing.verify_webhook(raw_body, signature=signature)
    if not verification.get("verified"):
        return {
            "ok": False,
            "verified": False,
            "message": verification.get("message") or "Invalid webhook signature.",
        }
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return {
            "ok": False,
            "verified": True,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "invalid webhook payload",
        }
    if not isinstance(event, dict):
        return {
            "ok": False,
            "verified": True,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "invalid webhook payload",
        }
    event_id = str(event.get("id") or "").strip()
    event_name = str(event.get("event") or "").strip()
    if event_id and not overlay.claim_billing_event(event_id, event_name):
        _LOG.info("razorpay webhook duplicate event=%s", event_name)
        return {
            "ok": True,
            "verified": True,
            "duplicate": True,
            "event": event_name,
            "entitled": False,
        }
    result = _handle_razorpay_event(enterprise, overlay, event)
    _LOG.info(
        "razorpay webhook event=%s entitled=%s duplicate=%s",
        event_name,
        bool(result.get("entitled")),
        bool(result.get("duplicate")),
    )
    return {
        **result,
        "ok": True,
        "verified": True,
        "duplicate": bool(result.get("duplicate")),
        "event": event_name,
    }


def _assign_license(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    plan_id = body.get("plan_id")
    tier = body.get("tier")
    if plan_id and not tier:
        tier = PLAN_TO_LICENSE_TIER.get(str(plan_id).lower())
    if not tier:
        tier = "research"
    seats = int(body.get("seats") or 1)
    limits = body.get("usage_limits")
    if plan_id and not limits:
        limits = plan_limits(str(plan_id))
    lic = enterprise.assign_license(
        org_id,
        tier=str(tier),
        seats=seats,
        actor_user_id=_actor(body),
        expires_at=body.get("expires_at"),
        usage_limits=limits,
    )
    if plan_id:
        overlay.upsert_subscription(
            org_id,
            {
                "plan_id": str(plan_id).lower(),
                "status": body.get("status") or "active",
                "trial_ends_at": body.get("trial_ends_at"),
            },
        )
    return {"license": lic}


def _activate_license(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    key = str(body.get("license_key") or "")
    activated = overlay.activate_license_key(key, org_id=org_id)
    plan_id = str(activated.get("plan_id") or "enterprise")
    tier = PLAN_TO_LICENSE_TIER.get(plan_id, "enterprise")
    lic = enterprise.assign_license(
        org_id,
        tier=tier,
        seats=int(activated.get("seats") or 1),
        actor_user_id=_actor(body),
        expires_at=activated.get("expires_at"),
        usage_limits=plan_limits(plan_id),
    )
    # Activation audit via enterprise
    try:
        enterprise.record_audit(
            org_id=org_id,
            actor_user_id=_actor(body),
            action="license.activate_key",
            resource_type="license_key",
            resource_id=key,
        )
    except Exception:  # noqa: BLE001
        pass
    overlay.upsert_subscription(
        org_id, {"plan_id": plan_id, "status": "active"}
    )
    return {
        "license_key": activated,
        "license": lic,
        "organization_activated": True,
    }


def _record_usage(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    actor = _actor(body)
    metric = str(body.get("metric") or "api_requests")
    amount = int(body.get("amount") or 1)
    enterprise.increment_usage(org_id, metric, amount, actor_user_id=actor)
    try:
        enterprise.record_audit(
            org_id=org_id,
            actor_user_id=actor,
            action=f"usage.{metric}",
            resource_type="usage",
            resource_id=org_id,
            metadata={"amount": amount, "metric": metric},
        )
    except Exception:  # noqa: BLE001
        pass
    return {"org_id": org_id, "metric": metric, "amount": amount, "recorded": True}


def _feature_limits(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    enterprise.require_permission(org_id, _actor(body), "org.view")
    sub = overlay.get_subscription(org_id)
    plan_id = str((sub or {}).get("plan_id") or body.get("plan_id") or "starter")
    return {
        "org_id": org_id or None,
        "plan_id": plan_id,
        "limits": plan_limits(plan_id),
        "feature_flags": dict(plan_feature_flags(plan_id)),
        "features": (get_plan(plan_id) or {}).get("features") or {},
        "note": "Limits are packaging + license usage_limits; engines remain unchanged.",
    }


def _admin_dashboard(
    enterprise: Any, overlay: Any, body: dict[str, Any]
) -> dict[str, Any]:
    """Member-scoped SaaS dashboard — never leaks foreign org state (P1-07)."""
    actor = str(body.get("actor_user_id") or body.get("user_id") or "").strip()
    orgs = enterprise.list_organizations(user_id=actor) if actor else []
    member_org_ids = {o["org_id"] for o in orgs}
    overview = {
        "organizations": len(orgs),
        "scoped_to_actor": actor,
        "note": "Dashboard aggregates are limited to organizations the actor belongs to.",
    }
    usage = enterprise.platform_usage_analytics()
    subs = [
        s
        for s in overlay.list_subscriptions()
        if str(s.get("org_id") or "") in member_org_ids
    ]
    plan_distribution: dict[str, int] = {p: 0 for p in PLAN_IDS}
    for sub in subs:
        pid = str(sub.get("plan_id") or "")
        if pid in plan_distribution:
            plan_distribution[pid] += 1

    # Most active orgs by usage counters (honest zeros when empty)
    activity: list[dict[str, Any]] = []
    for org in orgs:
        oid = org["org_id"]
        counters = getattr(enterprise.store, "usage_counters", {}).get(oid) or {}
        total = sum(int(v) for v in counters.values() if isinstance(v, int))
        activity.append(
            {
                "org_id": oid,
                "name": org.get("name"),
                "status": org.get("status"),
                "activity_score": total,
                "plan_id": (overlay.get_subscription(oid) or {}).get("plan_id"),
            }
        )
    activity.sort(key=lambda r: r["activity_score"], reverse=True)

    licenses_active = 0
    for org in orgs:
        try:
            v = enterprise.validate_license(org["org_id"])
            if v.get("valid"):
                licenses_active += 1
        except Exception:  # noqa: BLE001
            pass

    return {
        "subscription_overview": {
            "organizations": len(orgs),
            "subscriptions_tracked": len(subs),
            "plan_distribution": plan_distribution,
            "licenses_active": licenses_active,
        },
        "revenue": {
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
            "note": "Revenue requires a live billing provider. No fabricated KPIs.",
            "mrr": None,
            "arr": None,
        },
        "organizations": orgs[:50],
        "users": {
            "available": True,
            "note": "Member counts per org via enterprise IAM — no separate user DB here.",
            "org_member_totals": _member_totals(enterprise, orgs),
        },
        "license_usage": {
            "active": licenses_active,
            "organizations": len(orgs),
        },
        "storage_usage": {
            "storage_bytes": usage.get("storage_bytes", 0),
            "available": usage.get("available", True),
        },
        "most_active_organizations": activity[:10],
        "plan_distribution": plan_distribution,
        "growth_metrics": {
            "available": True,
            "organizations": len(orgs),
            "research": usage.get("research", 0),
            "exports": usage.get("exports", 0),
            "api_usage": usage.get("api_usage", 0),
            "note": "Growth figures are observed usage counters only — not projections.",
        },
        "usage": usage,
        "admin_overview": overview,
        "billing_provider": {
            "available": bool(
                getattr(getattr(enterprise, "billing", None), "is_available", lambda: False)()
            ),
            "provider": getattr(
                getattr(enterprise, "billing", None), "provider_name", lambda: "null"
            )(),
            "message": (
                None
                if getattr(
                    getattr(enterprise, "billing", None), "is_available", lambda: False
                )()
                else "Billing provider unavailable."
            ),
        },
    }


def _member_totals(enterprise: Any, orgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for org in orgs[:50]:
        oid = org["org_id"]
        try:
            members = [
                m
                for m in enterprise.store.members.values()
                if m.org_id == oid and m.status == "active"
            ]
            rows.append(
                {
                    "org_id": oid,
                    "name": org.get("name"),
                    "active_members": len(members),
                }
            )
        except Exception:  # noqa: BLE001
            rows.append(
                {
                    "org_id": oid,
                    "name": org.get("name"),
                    "active_members": None,
                    "message": UNAVAILABLE_MESSAGE,
                }
            )
    return rows
