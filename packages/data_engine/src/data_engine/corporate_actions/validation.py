"""Validate authenticated corporate actions — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.corporate_actions.models import (
    ACTION_TYPES,
    AuthenticatedCorporateAction,
    AuthenticatedCorporateActions,
    CorporateActionField,
)

__all__ = ["validate_authenticated_corporate_actions"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _check_field(name: str, field: CorporateActionField) -> None:
    if field.available and field.value is None:
        raise InvalidProviderDataError(
            f"corporate action field '{name}' marked available with null value"
        )
    if not field.available and field.value is not None:
        raise InvalidProviderDataError(
            f"corporate action field '{name}' has value but marked unavailable"
        )


def _validate_event(event: AuthenticatedCorporateAction, index: int) -> None:
    prefix = f"events[{index}]"
    if not event.action_id or not str(event.action_id).strip():
        raise InvalidProviderDataError(f"{prefix} missing action_id")
    if event.action_type not in ACTION_TYPES:
        raise InvalidProviderDataError(
            f"{prefix}.action_type must be one of {sorted(ACTION_TYPES)}, "
            f"got {event.action_type!r}"
        )
    if not event.symbol or not str(event.symbol).strip():
        raise InvalidProviderDataError(f"{prefix} missing symbol")
    # At least one date must be present for a historical event
    if not any(
        (
            event.effective_date,
            event.ex_date,
            event.record_date,
            event.payment_date,
            event.announcement_date,
        )
    ):
        raise InvalidProviderDataError(
            f"{prefix} requires at least one of effective/ex/record/payment/announcement date"
        )
    if event.currency is not None:
        code = event.currency.strip().upper()
        if len(code) != 3:
            raise InvalidProviderDataError(
                f"{prefix}.currency must be ISO 4217 or null, got {event.currency!r}"
            )
    for name in ("ratio_from", "ratio_to", "amount", "shares"):
        _check_field(f"{prefix}.{name}", getattr(event, name))


def validate_authenticated_corporate_actions(
    bundle: AuthenticatedCorporateActions,
) -> None:
    """Reject structurally invalid corporate action bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("corporate actions missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError(
            "corporate actions missing provider_id provenance"
        )
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError(
            "corporate actions missing provider_name provenance"
        )
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.events:
        raise InvalidProviderDataError(
            "authenticated corporate actions must include at least one event "
            "(use None from adapter when unavailable)"
        )
    for i, event in enumerate(bundle.events):
        _validate_event(event, i)
