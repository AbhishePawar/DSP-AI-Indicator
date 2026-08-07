"""Commercial subscription plan catalogue (RC1 M9).

Policy / packaging metadata only. Does not invent revenue or payments.
Limits are enforced via feature flags + license usage_limits on assign.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

__all__ = [
    "PLAN_IDS",
    "PLAN_TO_LICENSE_TIER",
    "SAAS_PLANS",
    "compare_plans",
    "get_plan",
    "plan_feature_flags",
    "plan_limits",
]

PLAN_IDS = ("starter", "professional", "enterprise", "custom")

# Map SaaS commercial plans → existing enterprise LICENSE_TIERS (no new license system)
PLAN_TO_LICENSE_TIER = MappingProxyType(
    {
        "starter": "research",
        "professional": "professional",
        "enterprise": "enterprise",
        "custom": "institutional",
    }
)

SAAS_PLANS: tuple[dict[str, Any], ...] = (
    {
        "plan_id": "starter",
        "name": "Starter",
        "tagline": "Individual research desk",
        "trial_days": 14,
        "seat_limit": 3,
        "storage_mb": 500,
        "portfolio_limit": 2,
        "research_limit_monthly": 50,
        "api_limit_monthly": 1_000,
        "copilot_limit_monthly": 100,
        "export_limit_monthly": 25,
        "features": {
            "company_workspace": True,
            "research_workspace": True,
            "portfolio_intelligence": True,
            "copilot_v2": True,
            "enterprise_dashboards": False,
            "workflow_automation": False,
            "export_engine": True,
            "admin_settings": False,
            "sso": False,
            "custom_branding": False,
        },
        "feature_flags": {
            "enterpriseDashboards": False,
            "researchWorkspacePlatform": True,
            "enterprisePortal": True,
            "enterpriseAdmin": False,
            "enterpriseOps": False,
        },
        "price_display": "Contact / packaging only — no live checkout",
    },
    {
        "plan_id": "professional",
        "name": "Professional",
        "tagline": "Team research operations",
        "trial_days": 14,
        "seat_limit": 15,
        "storage_mb": 5_000,
        "portfolio_limit": 20,
        "research_limit_monthly": 500,
        "api_limit_monthly": 20_000,
        "copilot_limit_monthly": 2_000,
        "export_limit_monthly": 200,
        "features": {
            "company_workspace": True,
            "research_workspace": True,
            "portfolio_intelligence": True,
            "copilot_v2": True,
            "enterprise_dashboards": True,
            "workflow_automation": True,
            "export_engine": True,
            "admin_settings": True,
            "sso": False,
            "custom_branding": True,
        },
        "feature_flags": {
            "enterpriseDashboards": True,
            "researchWorkspacePlatform": True,
            "enterprisePortal": True,
            "enterpriseAdmin": True,
            "enterpriseOps": False,
        },
        "price_display": "Contact / packaging only — no live checkout",
    },
    {
        "plan_id": "enterprise",
        "name": "Enterprise",
        "tagline": "Institutional multi-team deployment",
        "trial_days": 30,
        "seat_limit": 100,
        "storage_mb": 50_000,
        "portfolio_limit": 200,
        "research_limit_monthly": 10_000,
        "api_limit_monthly": 500_000,
        "copilot_limit_monthly": 50_000,
        "export_limit_monthly": 5_000,
        "features": {
            "company_workspace": True,
            "research_workspace": True,
            "portfolio_intelligence": True,
            "copilot_v2": True,
            "enterprise_dashboards": True,
            "workflow_automation": True,
            "export_engine": True,
            "admin_settings": True,
            "sso": True,
            "custom_branding": True,
        },
        "feature_flags": {
            "enterpriseDashboards": True,
            "researchWorkspacePlatform": True,
            "enterprisePortal": True,
            "enterpriseAdmin": True,
            "enterpriseOps": True,
        },
        "price_display": "Contact / packaging only — no live checkout",
    },
    {
        "plan_id": "custom",
        "name": "Custom",
        "tagline": "Negotiated institutional contract",
        "trial_days": 0,
        "seat_limit": None,
        "storage_mb": None,
        "portfolio_limit": None,
        "research_limit_monthly": None,
        "api_limit_monthly": None,
        "copilot_limit_monthly": None,
        "export_limit_monthly": None,
        "features": {
            "company_workspace": True,
            "research_workspace": True,
            "portfolio_intelligence": True,
            "copilot_v2": True,
            "enterprise_dashboards": True,
            "workflow_automation": True,
            "export_engine": True,
            "admin_settings": True,
            "sso": True,
            "custom_branding": True,
        },
        "feature_flags": {
            "enterpriseDashboards": True,
            "researchWorkspacePlatform": True,
            "enterprisePortal": True,
            "enterpriseAdmin": True,
            "enterpriseOps": True,
        },
        "price_display": "Custom contract — billing provider interface only",
    },
)


def get_plan(plan_id: str) -> dict[str, Any] | None:
    pid = (plan_id or "").strip().lower()
    for plan in SAAS_PLANS:
        if plan["plan_id"] == pid:
            return dict(plan)
    return None


def plan_limits(plan_id: str) -> dict[str, Any]:
    plan = get_plan(plan_id)
    if plan is None:
        return {}
    return {
        "seat_limit": plan.get("seat_limit"),
        "storage_mb": plan.get("storage_mb"),
        "portfolio_limit": plan.get("portfolio_limit"),
        "research_limit_monthly": plan.get("research_limit_monthly"),
        "api_limit_monthly": plan.get("api_limit_monthly"),
        "copilot_limit_monthly": plan.get("copilot_limit_monthly"),
        "export_limit_monthly": plan.get("export_limit_monthly"),
    }


def plan_feature_flags(plan_id: str) -> Mapping[str, bool]:
    plan = get_plan(plan_id)
    if plan is None:
        return {}
    return dict(plan.get("feature_flags") or {})


def compare_plans() -> dict[str, Any]:
    """Plan comparison matrix for UI — packaging only, no prices charged."""
    rows: list[dict[str, Any]] = []
    feature_keys = sorted(
        {k for p in SAAS_PLANS for k in (p.get("features") or {})}
    )
    for plan in SAAS_PLANS:
        feats = plan.get("features") or {}
        rows.append(
            {
                "plan_id": plan["plan_id"],
                "name": plan["name"],
                "limits": plan_limits(plan["plan_id"]),
                "features": {k: bool(feats.get(k)) for k in feature_keys},
                "trial_days": plan.get("trial_days"),
                "price_display": plan.get("price_display"),
                "license_tier": PLAN_TO_LICENSE_TIER.get(plan["plan_id"]),
            }
        )
    return {
        "plans": rows,
        "feature_keys": feature_keys,
        "note": "Plan matrix is packaging metadata. Live checkout requires a billing provider.",
    }
