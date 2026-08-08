"""Validate authenticated ESG bundles — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.connector_framework.models import ConnectorField
from data_engine.esg.models import CONTROVERSY_LEVELS, AuthenticatedEsgScore
from data_engine.exceptions import InvalidProviderDataError

__all__ = ["validate_authenticated_esg_score"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _check_field(name: str, f: ConnectorField) -> None:
    if f.available and f.value is None:
        raise InvalidProviderDataError(f"esg field '{name}' marked available with null value")
    if not f.available and f.value is not None:
        raise InvalidProviderDataError(f"esg field '{name}' has value but marked unavailable")


def validate_authenticated_esg_score(bundle: AuthenticatedEsgScore) -> None:
    """Reject structurally invalid ESG bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("esg score missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("esg score missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("esg score missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if bundle.controversy_level is not None and bundle.controversy_level not in CONTROVERSY_LEVELS:
        raise InvalidProviderDataError(
            f"controversy_level must be one of {sorted(CONTROVERSY_LEVELS)} or null, "
            f"got {bundle.controversy_level!r}"
        )
    for name in ("environmental_score", "social_score", "governance_score", "total_score"):
        _check_field(name, getattr(bundle, name))
    if not any(
        getattr(bundle, name).available
        for name in ("environmental_score", "social_score", "governance_score", "total_score")
    ):
        raise InvalidProviderDataError(
            "authenticated esg score must include at least one available score "
            "(use None from adapter when unavailable)"
        )
