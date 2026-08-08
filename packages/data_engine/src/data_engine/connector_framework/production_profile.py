"""P1-03 — production connector profile (fail closed, no silent Null).

``data_engine`` cannot import ``production_platform``; production is detected
from ``DSP_ENVIRONMENT`` only. Test/demo doubles remain available when the
environment is not production.
"""

from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

from data_engine.connector_framework.registry import PriorityProviderRegistry
from data_engine.exceptions import ConnectorConfigurationError

__all__ = [
    "ConnectorConfigurationError",
    "is_production_environment",
    "memory_adapter_allowed",
    "require_authenticated_http_adapter",
    "finalize_provider_registry",
    "assert_production_investment_connectors_configured",
    "classify_provider_id",
    "adapter_is_production_unsafe",
    "adapter_is_production_unsafe_name",
]

P = TypeVar("P")


def is_production_environment(
    environ: dict[str, str] | None = None,
) -> bool:
    env_map = environ if environ is not None else os.environ
    return str(env_map.get("DSP_ENVIRONMENT") or "").strip().lower() == "production"


def classify_provider_id(provider_id: str) -> str:
    """Return SAFE classification label for audits."""
    pid = str(provider_id or "").strip().lower()
    if pid.startswith("null_") or pid == "null":
        return "NULL_UNAVAILABLE"
    if "memory" in pid or pid.endswith("_memory"):
        return "TEST_MEMORY"
    if any(tok in pid for tok in ("demo", "sample", "seed", "fake", "fixture")):
        return "DEMO_OR_FAKE"
    return "PRODUCTION_CANDIDATE"


def memory_adapter_allowed(
    flag_name: str,
    *,
    connector: str,
    environ: dict[str, str] | None = None,
) -> bool:
    """True when an in-memory/seed adapter may be selected (never in production)."""
    env_map = environ if environ is not None else os.environ
    enabled = str(env_map.get(flag_name) or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled:
        return False
    if is_production_environment(env_map):
        raise ConnectorConfigurationError(
            f"P1-03: production refuses in-memory/seed adapter for {connector} "
            f"({flag_name}=true). Configure authenticated provider credentials."
        )
    return True


def require_authenticated_http_adapter(
    *,
    connector: str,
    api_key: str,
    base_url: str,
    api_key_env: str,
    base_url_env: str,
    environ: dict[str, str] | None = None,
) -> None:
    """Fail closed in production when HTTP credentials are incomplete."""
    if not is_production_environment(environ):
        return
    if api_key.strip() and base_url.strip():
        return
    from data_engine.fmp_investment import resolve_fmp_api_key

    if resolve_fmp_api_key(environ):
        return
    raise ConnectorConfigurationError(
        f"P1-03: production requires authenticated {connector} provider; "
        f"set {api_key_env} and {base_url_env}, "
        "or DSP_FMP_API_KEY / DSP_INVESTMENT_FMP_API_KEY (single-key FMP route). "
        "Null/demo/seed adapters are not permitted on the production path."
    )


def finalize_provider_registry(
    registry: PriorityProviderRegistry[P],
    *,
    connector: str,
    null_factory: Callable[[], P],
    null_provider_id: str,
    environ: dict[str, str] | None = None,
) -> PriorityProviderRegistry[P]:
    """Attach Null only outside production; refuse Null-only production registries."""
    env_map = environ if environ is not None else os.environ
    real_ids = [
        pid
        for pid in registry.all_ids()
        if classify_provider_id(pid) == "PRODUCTION_CANDIDATE"
    ]
    if is_production_environment(env_map):
        if not real_ids:
            raise ConnectorConfigurationError(
                f"P1-03: production {connector} registry has no real provider "
                "configured; refusing silent Null/memory fallback. "
                "Configure vendor credentials or explicit enable flags."
            )
        # Production: never register Null as a silent last resort.
        return registry

    registry.register(
        null_factory(),
        provider_id=null_provider_id,
        priority=1000,
    )
    return registry


def assert_production_investment_connectors_configured() -> dict[str, str]:
    """Eager production gate for investment-critical connectors (quote + statements).

    Returns a map of connector → selected provider class name. Raises
    :class:`ConnectorConfigurationError` when production would select Null/memory.
    No-op outside ``DSP_ENVIRONMENT=production``.
    """
    if not is_production_environment():
        return {}

    from data_engine.financial_statement.adapters import (
        build_default_statement_adapter_from_env,
    )
    from data_engine.market_quote.adapters import build_default_quote_adapter_from_env

    quote = build_default_quote_adapter_from_env()
    statements = build_default_statement_adapter_from_env()
    selected = {
        "market_quote": type(quote).__name__,
        "financial_statement": type(statements).__name__,
    }
    for name, cls_name in selected.items():
        if adapter_is_production_unsafe_name(cls_name):
            raise ConnectorConfigurationError(
                f"P1-03: production selected unsafe {name} adapter {cls_name}"
            )
    return selected


def adapter_is_production_unsafe_name(class_name: str) -> bool:
    name = str(class_name or "").lower()
    return any(
        token in name
        for token in ("null", "memory", "demo", "sample", "seed", "fake", "fixture")
    )


def adapter_is_production_unsafe(adapter: Any) -> bool:
    """True when an adapter instance is Null/memory/demo class."""
    return adapter_is_production_unsafe_name(type(adapter).__name__)
