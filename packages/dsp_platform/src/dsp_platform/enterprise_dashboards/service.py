"""Enterprise role dashboard aggregation (RC1 Milestone 6).

Thin composition over existing engines — no valuation, scoring, or
recommendation logic. Missing inputs surface as ``Data unavailable.``
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

UNAVAILABLE_MESSAGE = "Data unavailable."

DASHBOARD_ROLES: tuple[str, ...] = (
    "research",
    "portfolio-manager",
    "wealth-advisor",
    "family-office",
    "executive",
)

DASHBOARD_SCHEMA_VERSION = "1.0.0"
DASHBOARD_SERVICE_VERSION = "0.1.0"


def enterprise_dashboard_schema() -> dict[str, Any]:
    return {
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "service_version": DASHBOARD_SERVICE_VERSION,
        "roles": list(DASHBOARD_ROLES),
        "routes": [
            "/dashboards/research",
            "/dashboards/portfolio-manager",
            "/dashboards/wealth-advisor",
            "/dashboards/family-office",
            "/dashboards/executive",
        ],
        "rules": [
            "aggregation_only",
            "no_duplicated_calculations",
            "reuse_existing_engines",
            "missing_is_data_unavailable",
            "no_browser_valuation",
            "thin_api_routers",
        ],
        "engines_reused": [
            "research_engine",
            "research_intelligence",
            "research_monitoring",
            "portfolio_intelligence",
            "institutional_committee",
            "institutional_workflow",
            "portfolio_store_persistence",
            "admin_ops",
            "data_connector_news",
            "platform_health",
        ],
    }


def get_enterprise_dashboard(
    role: str,
    *,
    platform: Any,
    portfolio_id: str | None = None,
    symbols: list[str] | None = None,
    watchlist_id: str | None = None,
    client_portfolio_ids: list[str] | None = None,
    workflow_id: str | None = None,
) -> dict[str, Any]:
    """Build a role dashboard payload by aggregating existing platform APIs."""
    normalized = (role or "").strip().lower()
    if normalized not in DASHBOARD_ROLES:
        raise ValueError(f"Unknown dashboard role: {role!r}")

    generated_at = datetime.now(tz=UTC).isoformat()
    builders = {
        "research": _research_dashboard,
        "portfolio-manager": _portfolio_manager_dashboard,
        "wealth-advisor": _wealth_advisor_dashboard,
        "family-office": _family_office_dashboard,
        "executive": _executive_dashboard,
    }
    widgets = builders[normalized](
        platform,
        portfolio_id=portfolio_id,
        symbols=_normalize_symbols(symbols),
        watchlist_id=watchlist_id,
        client_portfolio_ids=client_portfolio_ids or [],
        workflow_id=workflow_id,
    )
    return {
        "role": normalized,
        "generated_at": generated_at,
        "schema_version": DASHBOARD_SCHEMA_VERSION,
        "widgets": widgets,
        "provenance": {
            "aggregation_only": True,
            "engines_called": True,
            "calculations_performed": False,
            "message": None,
        },
    }


def _normalize_symbols(symbols: list[str] | None) -> list[str]:
    if not symbols:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        sym = str(raw or "").strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _section(
    *,
    available: bool,
    source: str,
    data: Any = None,
    message: str | None = None,
) -> dict[str, Any]:
    return {
        "available": available,
        "source": source,
        "data": data if available else None,
        "message": None if available else (message or UNAVAILABLE_MESSAGE),
    }


def _try_admin_dashboard(platform: Any) -> dict[str, Any] | None:
    try:
        payload = platform.admin_dashboard()
    except Exception:  # noqa: BLE001 — honest unavailable
        return None
    return payload if isinstance(payload, dict) else None


def _try_health(platform: Any) -> dict[str, Any] | None:
    try:
        result = platform.health_check()
    except Exception:  # noqa: BLE001
        return None
    if result is None:
        return None
    payload = getattr(result, "payload", None)
    status = getattr(payload, "status", None)
    return {
        "ok": bool(getattr(result, "ok", False)),
        "ready": bool(getattr(payload, "ready", getattr(result, "ok", False))),
        "status": getattr(status, "value", str(status) if status is not None else "unknown"),
        "checks": [
            {
                "name": getattr(c, "name", "unknown"),
                "status": getattr(getattr(c, "status", None), "value", "unknown"),
                "message": getattr(c, "message", ""),
            }
            for c in (getattr(payload, "checks", ()) or ())
        ],
    }


def _try_persisted(platform: Any, kind: str, entity_id: str | None) -> dict[str, Any] | None:
    if not entity_id:
        return None
    try:
        row = platform.get_persisted_entity(kind, entity_id)
    except Exception:  # noqa: BLE001
        return None
    return row if isinstance(row, dict) else None


def _portfolio_from_store(
    platform: Any,
    portfolio_id: str | None,
    *,
    symbols: list[str] | None = None,
) -> dict[str, Any] | None:
    """Load portfolio payload from persistence metadata, or synthesize holdings from symbols.

    Persistence ENTITY_KINDS does not include a dedicated portfolio kind; callers
    may store portfolio JSON under ``metadata``. When only symbols are supplied,
    a holdings shell is returned so Portfolio Intelligence can report missing
    research honestly (no invented weights/scores).
    """
    for kind in ("metadata", "research_ref"):
        entity = _try_persisted(platform, kind, portfolio_id)
        if entity is None:
            continue
        payload = entity.get("payload")
        if isinstance(payload, dict):
            # Prefer nested portfolio object when present
            nested = payload.get("portfolio")
            if isinstance(nested, dict):
                return nested
            if "holdings" in payload or "portfolio_id" in payload:
                return payload
        if isinstance(entity, dict) and "holdings" in entity:
            return entity

    if symbols:
        return {
            "portfolio_id": portfolio_id or "query-symbols",
            "holdings": [{"symbol": sym} for sym in symbols],
        }
    return None


def _try_portfolio_intelligence(
    platform: Any,
    *,
    portfolio: Mapping[str, Any] | None,
    watchlist: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if portfolio is None and watchlist is None:
        return None
    try:
        return platform.evaluate_portfolio_intelligence(
            portfolio=dict(portfolio) if portfolio else None,
            watchlist=dict(watchlist) if watchlist else None,
        )
    except Exception:  # noqa: BLE001
        return None


def _try_workflow(platform: Any, *, workflow_id: str | None) -> dict[str, Any] | None:
    if not workflow_id:
        return None
    try:
        return platform.apply_institutional_workflow(
            action="get",
            workflow_id=workflow_id,
        )
    except Exception:  # noqa: BLE001
        return None


def _try_workflow_templates(platform: Any) -> list[dict[str, Any]]:
    try:
        rows = platform.list_workflow_templates()
    except Exception:  # noqa: BLE001
        return []
    return list(rows) if isinstance(rows, list) else []


def _try_committee_agents(platform: Any) -> list[dict[str, str]]:
    try:
        rows = platform.list_committee_agents()
    except Exception:  # noqa: BLE001
        return []
    return list(rows) if isinstance(rows, list) else []


def _try_research_intelligence_schema(platform: Any) -> dict[str, Any] | None:
    try:
        schema = platform.research_intelligence_schema()
    except Exception:  # noqa: BLE001
        return None
    return schema if isinstance(schema, dict) else None


def _try_monitoring_schema(platform: Any) -> dict[str, Any] | None:
    try:
        schema = platform.research_monitoring_schema()
    except Exception:  # noqa: BLE001
        return None
    return schema if isinstance(schema, dict) else None


def _recent_news(platform: Any, symbols: list[str]) -> dict[str, Any]:
    if not symbols:
        return _section(
            available=False,
            source="data_connector_news",
            message=UNAVAILABLE_MESSAGE,
        )
    articles: list[dict[str, Any]] = []
    for symbol in symbols[:5]:
        try:
            feed = platform.get_authenticated_news(symbol, limit=5)
        except Exception:  # noqa: BLE001
            feed = None
        if not isinstance(feed, dict):
            continue
        items = feed.get("articles") or feed.get("items") or []
        if isinstance(items, list):
            for item in items[:5]:
                if isinstance(item, dict):
                    articles.append({"symbol": symbol, **item})
    if not articles:
        return _section(
            available=False,
            source="data_connector_news",
            message=UNAVAILABLE_MESSAGE,
        )
    return _section(
        available=True,
        source="data_connector_news",
        data={"articles": articles[:20], "symbol_count": len(symbols)},
    )


def _research_dashboard(
    platform: Any,
    *,
    portfolio_id: str | None,
    symbols: list[str],
    watchlist_id: str | None,
    client_portfolio_ids: list[str],
    workflow_id: str | None,
) -> dict[str, Any]:
    del portfolio_id, client_portfolio_ids
    ri_schema = _try_research_intelligence_schema(platform)
    mon_schema = _try_monitoring_schema(platform)
    agents = _try_committee_agents(platform)
    workflow = _try_workflow(platform, workflow_id=workflow_id)
    admin = _try_admin_dashboard(platform)

    coverage_available = ri_schema is not None or mon_schema is not None
    coverage_data = {
        "research_intelligence": ri_schema,
        "research_monitoring": mon_schema,
        "symbols_in_scope": symbols or None,
        "note": "Coverage descriptors from Research Intelligence / Monitoring schemas only.",
    }

    under_review = _section(
        available=workflow is not None,
        source="institutional_workflow",
        data=workflow,
    )
    pending = _section(
        available=bool(_try_workflow_templates(platform)) or workflow is not None,
        source="institutional_workflow",
        data={
            "templates": _try_workflow_templates(platform),
            "workflow": workflow,
            "note": "Pending research uses workflow stage state when a workflow_id is supplied.",
        },
    )

    recent_reports = _section(
        available=admin is not None and int(admin.get("research_refs_count") or 0) >= 0,
        source="admin_research_archive_metadata",
        data={
            "research_refs_count": (admin or {}).get("research_refs_count"),
            "note": "Archive reference counts only — report bodies remain on /report/{id}.",
        }
        if admin
        else None,
    )

    research_score = _section(
        available=ri_schema is not None,
        source="research_intelligence",
        data={
            "schema": ri_schema,
            "score": UNAVAILABLE_MESSAGE,
            "note": "No aggregate research score is invented; open Research Intelligence for measured snapshots.",
        },
    )

    committee = _section(
        available=bool(agents),
        source="institutional_committee",
        data={
            "agents": agents,
            "summary": UNAVAILABLE_MESSAGE,
            "note": "Run POST /committee/run per subject — dashboard never fabricates committee outcomes.",
        },
    )

    watchlist = _section(
        available=bool(symbols) or bool(watchlist_id),
        source="research_monitoring_watchlist",
        data={
            "watchlist_id": watchlist_id,
            "symbols": symbols,
        },
    )

    return {
        "research_coverage": _section(
            available=coverage_available,
            source="research_engine",
            data=coverage_data if coverage_available else None,
        ),
        "companies_under_review": under_review,
        "pending_research": pending,
        "recent_reports": recent_reports
        if recent_reports["available"]
        else _section(available=False, source="admin_research_archive_metadata"),
        "research_score": research_score,
        "ai_committee_summary": committee,
        "watchlist": watchlist
        if watchlist["available"]
        else _section(available=False, source="research_monitoring_watchlist"),
        "recent_news": _recent_news(platform, symbols),
    }


def _pi_widgets(pi: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(pi, dict):
        unavailable = _section(available=False, source="portfolio_intelligence")
        return {
            "portfolio_health_score": unavailable,
            "asset_allocation": unavailable,
            "risk_summary": unavailable,
            "diversification": unavailable,
            "top_opportunities": unavailable,
            "valuation_heatmap": unavailable,
            "portfolio_performance": unavailable,
        }

    summary = pi.get("portfolio_summary") if isinstance(pi.get("portfolio_summary"), dict) else {}
    allocation = pi.get("sector_allocation") if isinstance(pi.get("sector_allocation"), dict) else {}
    risk = pi.get("portfolio_risk_summary") if isinstance(pi.get("portfolio_risk_summary"), dict) else {}
    divers = (
        pi.get("diversification_summary")
        if isinstance(pi.get("diversification_summary"), dict)
        else {}
    )
    mos = (
        pi.get("margin_of_safety_summary")
        if isinstance(pi.get("margin_of_safety_summary"), dict)
        else {}
    )

    return {
        "portfolio_health_score": _section(
            available=True,
            source="portfolio_intelligence.portfolio_summary",
            data={
                "linked_research_count": summary.get("linked_research_count"),
                "missing_research_count": summary.get("missing_research_count"),
                "holding_count": summary.get("holding_count"),
                "health_score": UNAVAILABLE_MESSAGE,
                "note": "Health is expressed via linked/missing research counts — no invented score.",
            },
        ),
        "asset_allocation": _section(
            available=bool(allocation),
            source="portfolio_intelligence.sector_allocation",
            data=allocation or None,
        ),
        "risk_summary": _section(
            available=bool(risk),
            source="portfolio_intelligence.portfolio_risk_summary",
            data=risk or None,
        ),
        "diversification": _section(
            available=bool(divers),
            source="portfolio_intelligence.diversification_summary",
            data=divers or None,
        ),
        "top_opportunities": _section(
            available=False,
            source="portfolio_intelligence",
            message=UNAVAILABLE_MESSAGE,
        ),
        "valuation_heatmap": _section(
            available=bool(mos),
            source="portfolio_intelligence.margin_of_safety_summary",
            data={
                "positions": mos.get("positions"),
                "note": "Pass-through MoS from linked research — not a computed heatmap score.",
            }
            if mos
            else None,
        ),
        "portfolio_performance": _section(
            available=False,
            source="portfolio_intelligence",
            message=UNAVAILABLE_MESSAGE,
        ),
    }


def _alerts_from_monitoring(platform: Any, symbols: list[str]) -> dict[str, Any]:
    schema = _try_monitoring_schema(platform)
    if schema is None and not symbols:
        return _section(available=False, source="research_monitoring")
    return _section(
        available=True,
        source="research_monitoring",
        data={
            "schema": schema,
            "symbols": symbols or None,
            "alerts": UNAVAILABLE_MESSAGE,
            "note": "Alert evaluation requires POST /research/monitoring/evaluate with snapshots.",
        },
    )


def _portfolio_manager_dashboard(
    platform: Any,
    *,
    portfolio_id: str | None,
    symbols: list[str],
    watchlist_id: str | None,
    client_portfolio_ids: list[str],
    workflow_id: str | None,
) -> dict[str, Any]:
    del client_portfolio_ids, workflow_id
    portfolio = _portfolio_from_store(platform, portfolio_id, symbols=symbols)
    watchlist = (
        {"watchlist_id": watchlist_id, "symbols": symbols}
        if watchlist_id or symbols
        else None
    )
    pi = _try_portfolio_intelligence(platform, portfolio=portfolio, watchlist=watchlist)
    widgets = _pi_widgets(pi)
    widgets["alerts"] = _alerts_from_monitoring(platform, symbols)
    widgets["portfolio_id"] = _section(
        available=bool(portfolio_id) or bool(symbols),
        source="portfolio_store",
        data={
            "portfolio_id": portfolio_id,
            "loaded": portfolio is not None,
            "symbols": symbols or None,
        },
    )
    return widgets


def _wealth_advisor_dashboard(
    platform: Any,
    *,
    portfolio_id: str | None,
    symbols: list[str],
    watchlist_id: str | None,
    client_portfolio_ids: list[str],
    workflow_id: str | None,
) -> dict[str, Any]:
    del watchlist_id
    ids = list(client_portfolio_ids)
    if portfolio_id and portfolio_id not in ids:
        ids.append(portfolio_id)

    client_rows: list[dict[str, Any]] = []
    for pid in ids[:20]:
        entity = _portfolio_from_store(platform, pid, symbols=symbols if pid == portfolio_id else None)
        client_rows.append(
            {
                "portfolio_id": pid,
                "available": entity is not None,
                "payload": entity if entity is not None else UNAVAILABLE_MESSAGE,
            }
        )

    primary = _portfolio_from_store(
        platform,
        portfolio_id or (ids[0] if ids else None),
        symbols=symbols,
    )
    pi = _try_portfolio_intelligence(
        platform,
        portfolio=primary,
        watchlist={"symbols": symbols} if symbols else None,
    )
    pi_widgets = _pi_widgets(pi)
    workflow = _try_workflow(platform, workflow_id=workflow_id)
    templates = _try_workflow_templates(platform)

    return {
        "client_portfolios": _section(
            available=bool(client_rows),
            source="portfolio_store",
            data={"portfolios": client_rows} if client_rows else None,
        ),
        "portfolio_health": pi_widgets["portfolio_health_score"],
        "risk_warnings": pi_widgets["risk_summary"],
        "recommended_actions": _section(
            available=False,
            source="workflow_automation",
            message=UNAVAILABLE_MESSAGE,
        ),
        "upcoming_reviews": _section(
            available=bool(templates) or workflow is not None,
            source="workflow_automation",
            data={
                "templates": templates,
                "workflow": workflow,
                "note": "Reviews reflect workflow templates / supplied workflow_id only.",
            },
        ),
        "workflow_notifications": _section(
            available=workflow is not None,
            source="workflow_automation",
            data=workflow,
        )
        if workflow is not None
        else _section(available=False, source="workflow_automation"),
    }


def _family_office_dashboard(
    platform: Any,
    *,
    portfolio_id: str | None,
    symbols: list[str],
    watchlist_id: str | None,
    client_portfolio_ids: list[str],
    workflow_id: str | None,
) -> dict[str, Any]:
    del watchlist_id, client_portfolio_ids, workflow_id
    portfolio = _portfolio_from_store(platform, portfolio_id, symbols=symbols)
    pi = _try_portfolio_intelligence(
        platform,
        portfolio=portfolio,
        watchlist={"symbols": symbols} if symbols else None,
    )
    pi_widgets = _pi_widgets(pi)
    holdings = None
    if isinstance(portfolio, dict):
        holdings = portfolio.get("holdings")
    cash = None
    if isinstance(portfolio, dict):
        cash = portfolio.get("cash") or portfolio.get("cash_position")

    return {
        "net_worth_summary": _section(
            available=False,
            source="portfolio_store",
            message=UNAVAILABLE_MESSAGE,
        ),
        "asset_allocation": pi_widgets["asset_allocation"],
        "portfolio_intelligence": _section(
            available=pi is not None,
            source="portfolio_intelligence",
            data=pi,
        ),
        "holdings_overview": _section(
            available=isinstance(holdings, list),
            source="portfolio_store",
            data={"holdings": holdings} if isinstance(holdings, list) else None,
        ),
        "risk": pi_widgets["risk_summary"],
        "opportunities": pi_widgets["top_opportunities"],
        "cash_position": _section(
            available=cash is not None,
            source="portfolio_store",
            data={"cash": cash} if cash is not None else None,
        ),
    }


def _executive_dashboard(
    platform: Any,
    *,
    portfolio_id: str | None,
    symbols: list[str],
    watchlist_id: str | None,
    client_portfolio_ids: list[str],
    workflow_id: str | None,
) -> dict[str, Any]:
    del portfolio_id, symbols, watchlist_id, client_portfolio_ids
    admin = _try_admin_dashboard(platform)
    health = _try_health(platform)
    ri = _try_research_intelligence_schema(platform)
    templates = _try_workflow_templates(platform)
    workflow = _try_workflow(platform, workflow_id=workflow_id)

    kpis = None
    if admin is not None:
        kpis = {
            "users_count": admin.get("users_count"),
            "sessions_count": admin.get("sessions_count"),
            "active_sessions_count": admin.get("active_sessions_count"),
            "audit_records_count": admin.get("audit_records_count"),
            "workflow_records_count": admin.get("workflow_records_count"),
            "research_refs_count": admin.get("research_refs_count"),
            "roles_count": admin.get("roles_count"),
            "permissions_count": admin.get("permissions_count"),
        }

    return {
        "platform_kpis": _section(
            available=kpis is not None,
            source="admin_dashboard",
            data=kpis,
        ),
        "research_coverage": _section(
            available=ri is not None or (admin is not None),
            source="research_intelligence+admin",
            data={
                "research_refs_count": (admin or {}).get("research_refs_count"),
                "research_intelligence_schema": ri,
            },
        ),
        "portfolio_coverage": _section(
            available=admin is not None,
            source="admin_dashboard",
            data={
                "note": "Portfolio coverage counts require persisted portfolio entities; KPI panel shows platform activity only.",
                "workflow_records_count": (admin or {}).get("workflow_records_count"),
            },
        ),
        "workflow_status": _section(
            available=bool(templates) or workflow is not None or admin is not None,
            source="workflow_automation",
            data={
                "templates": templates,
                "workflow": workflow,
                "workflow_records_count": (admin or {}).get("workflow_records_count"),
            },
        ),
        "alert_statistics": _section(
            available=False,
            source="research_monitoring",
            message=UNAVAILABLE_MESSAGE,
        ),
        "user_activity": _section(
            available=admin is not None,
            source="admin_dashboard",
            data={
                "users_count": (admin or {}).get("users_count"),
                "sessions_count": (admin or {}).get("sessions_count"),
                "active_sessions_count": (admin or {}).get("active_sessions_count"),
            }
            if admin
            else None,
        ),
        "system_health": _section(
            available=health is not None,
            source="platform_health",
            data=health,
        ),
    }
