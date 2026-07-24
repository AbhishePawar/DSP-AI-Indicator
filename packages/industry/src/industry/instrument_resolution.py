"""Instrument → industry → methodology → peer policy resolution."""

from __future__ import annotations

from contracts.domain.instrument import Instrument

from industry.exceptions import IndustryError
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.peer_eligibility import InstrumentMethodologyResolution
from industry.peer_registry import (
    InstrumentIndustryRegistry,
    PeerEligibilityPolicyRegistry,
)
from industry.profile_registry import IndustryProfileRegistry

__all__ = ["resolve_methodology_for_instrument"]


def resolve_methodology_for_instrument(
    instrument: Instrument | str,
    *,
    assignments: InstrumentIndustryRegistry,
    methodologies: IndustryMethodologyRegistry,
    policies: PeerEligibilityPolicyRegistry,
    profiles: IndustryProfileRegistry | None = None,
) -> InstrumentMethodologyResolution:
    """Resolve Instrument → IndustryIdentity → Methodology → PeerEligibilityPolicy.

    Rejects unresolved instruments, missing methodologies, and missing peer
    policy references explicitly (never invents an industry).
    """
    symbol = (
        instrument.symbol
        if isinstance(instrument, Instrument)
        else instrument.strip().upper()
    )
    if not symbol:
        msg = "instrument symbol must not be empty"
        raise IndustryError(msg)

    try:
        assignment = assignments.get(symbol)
    except IndustryError as exc:
        msg = (
            f"cannot resolve methodology: instrument {symbol!r} has no "
            f"IndustryIdentity binding"
        )
        raise IndustryError(msg) from exc

    try:
        methodology = methodologies.lookup_active_for_industry(
            assignment.industry_id
        )
    except IndustryError as exc:
        msg = (
            f"cannot resolve methodology: industry {assignment.industry_id!r} "
            f"for instrument {symbol!r} has no active IndustryMethodology"
        )
        raise IndustryError(msg) from exc

    if methodology.peer_policy is None:
        msg = (
            f"cannot resolve peer policy: methodology {methodology.id!r} "
            f"version {methodology.version!r} has no peer_policy reference"
        )
        raise IndustryError(msg)

    policy_id = methodology.peer_policy.policy_id
    if not policies.contains(policy_id):
        msg = (
            f"cannot resolve peer policy: unknown policy {policy_id!r} "
            f"referenced by methodology {methodology.id!r}"
        )
        raise IndustryError(msg)

    policy = policies.lookup_active(policy_id)
    if policy.subject_industry_id != methodology.industry_id:
        msg = (
            f"peer policy {policy.id!r} subject industry "
            f"{policy.subject_industry_id!r} does not match methodology "
            f"industry {methodology.industry_id!r}"
        )
        raise IndustryError(msg)

    profile_version: str | None = None
    if profiles is not None:
        try:
            profile = profiles.lookup_active(assignment.industry_id)
            profile_version = profile.version
        except IndustryError:
            profile_version = None

    return InstrumentMethodologyResolution(
        symbol=symbol,
        industry_id=assignment.industry_id,
        business_model_id=assignment.business_model_id,
        methodology_id=methodology.id,
        methodology_version=methodology.version,
        peer_policy_id=policy.id,
        peer_policy_version=policy.version,
        profile_version=profile_version,
    )
