"""Startup validation and readiness reporting (PEP-004.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


__all__ = [
    "ReadinessCheck",
    "ReadinessReport",
    "StartupValidation",
    "build_readiness_report",
    "validate_enterprise_startup",
]


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    ready: bool
    checks: tuple[ReadinessCheck, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StartupValidation:
    ok: bool
    checks: tuple[ReadinessCheck, ...]
    errors: tuple[str, ...] = ()


def validate_enterprise_startup(platform: Any) -> StartupValidation:
    """Validate composed enterprise bundles without touching business engines."""
    checks: list[ReadinessCheck] = []
    errors: list[str] = []

    def _add(name: str, ok: bool, detail: str = "") -> None:
        checks.append(ReadinessCheck(name=name, ok=ok, detail=detail))
        if not ok:
            errors.append(f"{name}: {detail or 'failed'}")

    infra = getattr(platform, "infrastructure", None)
    _add("infrastructure", infra is not None and infra.database.ping())
    if infra is not None:
        probes = infra.health_checks()
        _add(
            "database",
            bool(probes.get("database")),
            detail=str(probes.get("database_adapter", "")),
        )
        redis = probes.get("redis") or {}
        redis_status = str(redis.get("status", "skip"))
        _add(
            "redis",
            redis_status in {"pass", "skip", "degraded"},
            detail=f"status={redis_status}",
        )

    obs = getattr(platform, "observability", None)
    _add(
        "observability",
        obs is not None,
        detail=type(obs).__name__ if obs else "missing",
    )
    if obs is not None:
        retention = obs.settings.cert_in_log_retention_days
        _add(
            "cert_in_log_retention",
            retention >= 180,
            detail=f"days={retention}",
        )

    security = getattr(platform, "security", None)
    _add("security", security is not None and security.identity is not None)

    compliance = getattr(platform, "compliance", None)
    _add("compliance", compliance is not None)
    if compliance is not None:
        _add(
            "research_mode_default",
            compliance.flags.research_mode is True and compliance.flags.sebi_mode is False,
            detail=f"research={compliance.flags.research_mode} sebi={compliance.flags.sebi_mode}",
        )
        policy = compliance.audit_retention.policy()
        _add(
            "audit_retention_floor",
            policy.retention_days >= 180,
            detail=f"days={policy.retention_days}",
        )
        disclosures = compliance.disclosures.list_active(mode="research")
        _add("research_disclosures", len(disclosures) >= 1, detail=f"count={len(disclosures)}")

    production = getattr(platform, "production", None)
    _add("production", production is not None)
    if production is not None:
        live = production.liveness()
        ready = production.readiness()
        _add("liveness", live.live is True)
        _add("readiness", ready.ready is True)

    consent_aligned = getattr(platform, "consent_aligned", False)
    _add(
        "consent_alignment",
        bool(consent_aligned),
        detail="compliance ConsentPort backing identity"
        if consent_aligned
        else "identity using local consent store",
    )

    return StartupValidation(
        ok=not errors,
        checks=tuple(checks),
        errors=tuple(errors),
    )


def build_readiness_report(platform: Any) -> ReadinessReport:
    validation = validate_enterprise_startup(platform)
    notes = [
        "PEP-001…004 composition via platform_runtime",
        "Investment engines not loaded by composition root",
        f"consent SoT: {getattr(platform, 'consent_source_of_truth', 'unknown')}",
    ]
    return ReadinessReport(
        ready=validation.ok,
        checks=validation.checks,
        notes=tuple(notes),
    )
