"""RC1 Milestone 9 — Commercial SaaS Platform orchestration.

Reuses packages/enterprise (orgs, teams, licenses, API keys, usage, audit,
billing ports). Never duplicates authentication, organizations, or payments.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.saas_platform.plans import (
    PLAN_IDS,
    PLAN_TO_LICENSE_TIER,
    SAAS_PLANS,
    compare_plans,
    get_plan,
    plan_feature_flags,
    plan_limits,
)
from dsp_platform.saas_platform.store import (
    default_trial_ends,
    get_saas_overlay_store,
)

UNAVAILABLE_MESSAGE = "Data unavailable."
SAAS_SCHEMA_VERSION = "1.0.0"
SAAS_SERVICE_VERSION = "0.1.0"

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
        "billing_note": "Payment gateway interfaces only until a provider is available.",
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
        "dashboard": lambda: _admin_dashboard(enterprise, overlay),
        "list_organizations": lambda: {
            "organizations": enterprise.list_organizations(
                user_id=body.get("user_id") or body.get("actor_user_id")
            )
        },
        "get_organization": lambda: _require_org(
            enterprise, str(body.get("org_id") or "")
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
            "roles": enterprise.list_roles(str(body.get("org_id") or ""))
        },
        "create_subscription": lambda: _create_subscription(
            enterprise, overlay, body
        ),
        "get_subscription": lambda: _get_subscription(overlay, body),
        "billing_profile": lambda: _billing_profile(overlay, body),
        "upsert_billing_profile": lambda: {
            "profile": overlay.upsert_billing_profile(
                str(body.get("org_id") or ""), body
            )
        },
        "billing_status": lambda: enterprise.billing_status(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "list_invoices": lambda: enterprise.list_invoices(
            str(body.get("org_id") or ""), actor_user_id=_actor(body)
        ),
        "checkout": lambda: _checkout(enterprise, body),
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
        "validate_license": lambda: enterprise.validate_license(
            str(body.get("org_id") or "")
        ),
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
        "feature_limits": lambda: _feature_limits(overlay, body),
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


def _require_org(enterprise: Any, org_id: str) -> dict[str, Any]:
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
    org = enterprise.get_organization(org_id)
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
    org = enterprise.get_organization(str(body.get("org_id") or ""))
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
    existing = enterprise.get_organization(org_id)
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

    # Bind seats/limits via existing license system (no duplicate licensing)
    actor = body.get("actor_user_id") or body.get("owner_user_id")
    license_row = None
    if actor:
        tier = PLAN_TO_LICENSE_TIER[plan_id]
        seats = body.get("seats") or plan.get("seat_limit") or 1
        license_row = enterprise.assign_license(
            org_id,
            tier=tier,
            seats=int(seats),
            actor_user_id=str(actor),
            expires_at=body.get("expires_at") or trial_ends,
            usage_limits=plan_limits(plan_id),
        )
        # Align org seat_limit with plan
        try:
            enterprise.update_organization(
                org_id,
                actor_user_id=str(actor),
                seat_limit=int(seats) if seats else None,
            )
        except Exception:  # noqa: BLE001
            pass

    billing = None
    try:
        if actor:
            billing = enterprise.billing_status(org_id, actor_user_id=str(actor))
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


def _get_subscription(overlay: Any, body: dict[str, Any]) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
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


def _billing_profile(overlay: Any, body: dict[str, Any]) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
    profile = overlay.get_billing_profile(org_id)
    if profile is None:
        return {
            "available": False,
            "profile": None,
            "message": UNAVAILABLE_MESSAGE,
        }
    return {"available": True, "profile": profile}


def _checkout(enterprise: Any, body: dict[str, Any]) -> dict[str, Any]:
    """Never fake payments — delegate to BillingPort checkout if present."""
    org_id = str(body.get("org_id") or "")
    billing = getattr(enterprise, "billing", None)
    if billing is None or not hasattr(billing, "create_checkout_session"):
        return {
            "ok": False,
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
            "detail": "Billing provider unavailable.",
        }
    if not billing.is_available():
        return billing.create_checkout_session(
            org_id, plan=body.get("plan_id")
        )
    return billing.create_checkout_session(org_id, plan=body.get("plan_id"))


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
    metric = str(body.get("metric") or "api_requests")
    amount = int(body.get("amount") or 1)
    enterprise.increment_usage(org_id, metric, amount)
    # Also append audit for usage events (reuse audit logger — no duplicate)
    try:
        enterprise.record_audit(
            org_id=org_id,
            actor_user_id=body.get("actor_user_id") or "system",
            action=f"usage.{metric}",
            resource_type="usage",
            resource_id=org_id,
            metadata={"amount": amount, "metric": metric},
        )
    except Exception:  # noqa: BLE001
        pass
    return {"org_id": org_id, "metric": metric, "amount": amount, "recorded": True}


def _feature_limits(overlay: Any, body: dict[str, Any]) -> dict[str, Any]:
    org_id = str(body.get("org_id") or "")
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


def _admin_dashboard(enterprise: Any, overlay: Any) -> dict[str, Any]:
    """Admin SaaS dashboard — honest aggregates; no fake revenue KPIs."""
    overview = enterprise.admin_overview()
    usage = enterprise.platform_usage_analytics()
    orgs = enterprise.list_organizations()
    subs = overlay.list_subscriptions()
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
