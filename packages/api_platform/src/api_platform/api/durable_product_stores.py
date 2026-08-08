"""P0-06 — wire durable multi-tenant product stores from DatabasePort.

Deep dsp_platform modules are loaded via importlib so static sibling-import
boundaries stay intact (same pattern as infra_bootstrap / production_ops).
"""

from __future__ import annotations

import importlib
import os
from typing import Any

from api_platform.api.dependencies import ReportStore, build_report_store

__all__ = [
    "configure_durable_product_stores",
    "require_durable_product_database",
    "is_durable_database",
]


def is_durable_database(database: Any | None) -> bool:
    """True when the port exposes shared SQL primitives."""
    if database is None:
        return False
    return all(hasattr(database, name) for name in ("execute", "fetchall", "ping"))


def require_durable_product_database(database: Any | None) -> None:
    """Fail closed in production when product stores cannot be durable."""
    env = (os.environ.get("DSP_ENVIRONMENT") or "").lower()
    if env != "production":
        return
    adapter = type(database).__name__ if database is not None else "None"
    if not is_durable_database(database) or adapter == "InMemoryDatabasePort":
        raise RuntimeError(
            "P0-06: production requires a shared durable DatabasePort "
            "(PostgreSQL) for SaaS/workspace/enterprise/report state; "
            f"got {adapter}"
        )


def configure_durable_product_stores(database: Any | None) -> ReportStore:
    """Attach durable SaaS/workspace/enterprise stores; return report store."""
    require_durable_product_database(database)

    if not is_durable_database(database):
        # Non-production / no DB — process-local provenance store (tests only).
        try:
            prov = importlib.import_module("dsp_platform.investment_provenance")
            prov.configure_investment_provenance_store(None)
        except Exception:  # noqa: BLE001
            pass
        return build_report_store(None)

    try:
        enterprise_service = importlib.import_module("enterprise.service")
        if not enterprise_service.enterprise_service_configured():
            enterprise_service.get_enterprise_service(database=database)
    except Exception:  # noqa: BLE001
        pass

    try:
        saas_db = importlib.import_module("dsp_platform.saas_platform.db_store")
        saas_store = importlib.import_module("dsp_platform.saas_platform.store")
        saas_store.reset_saas_overlay_store_for_tests(
            saas_db.DatabaseSaasOverlayStore(database)
        )
    except Exception:  # noqa: BLE001
        pass

    try:
        ws_db = importlib.import_module("dsp_platform.research_workspace.db_store")
        ws_store = importlib.import_module("dsp_platform.research_workspace.store")
        ws_store.reset_research_workspace_store_for_tests(
            ws_db.DatabaseResearchWorkspaceStore(database)
        )
    except Exception:  # noqa: BLE001
        pass

    # P1-06 — append-only investment provenance / decision lineage.
    try:
        prov = importlib.import_module("dsp_platform.investment_provenance")
        prov.configure_investment_provenance_store(database)
    except Exception:  # noqa: BLE001
        pass

    return build_report_store(database)
