"""Peer eligibility evaluator — structural gate before any comparison."""

from __future__ import annotations

from contracts.domain.instrument import Instrument

from industry.enums import GroupEligibilityStatus, PeerEligibilityStatus
from industry.exceptions import IndustryError
from industry.instrument_resolution import resolve_methodology_for_instrument
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.peer_eligibility import (
    EligibilityOptions,
    GroupEligibilityResult,
    InstrumentMethodologyResolution,
    PeerEligibilityReason,
    PeerEligibilityResult,
    stricter_status,
)
from industry.peer_registry import (
    InstrumentIndustryRegistry,
    PeerEligibilityPolicyRegistry,
)
from industry.profile_registry import IndustryProfileRegistry

__all__ = ["PeerEligibilityEvaluator"]


class PeerEligibilityEvaluator:
    """Evaluates whether instruments are legitimate comparison candidates.

    Does not compare fundamentals, scores, or ranks.
    """

    def __init__(
        self,
        *,
        assignments: InstrumentIndustryRegistry,
        methodologies: IndustryMethodologyRegistry,
        policies: PeerEligibilityPolicyRegistry,
        profiles: IndustryProfileRegistry | None = None,
    ) -> None:
        self._assignments = assignments
        self._methodologies = methodologies
        self._policies = policies
        self._profiles = profiles

    def resolve(
        self, instrument: Instrument | str
    ) -> InstrumentMethodologyResolution:
        return resolve_methodology_for_instrument(
            instrument,
            assignments=self._assignments,
            methodologies=self._methodologies,
            policies=self._policies,
            profiles=self._profiles,
        )

    def evaluate_pair(
        self,
        left: Instrument | str,
        right: Instrument | str,
        *,
        options: EligibilityOptions | None = None,
    ) -> PeerEligibilityResult:
        """Bidirectional structural eligibility; stricter status wins."""
        opts = options or EligibilityOptions()
        left_key = _symbol(left)
        right_key = _symbol(right)
        if left_key == right_key:
            reason = PeerEligibilityReason(
                code="same_instrument",
                message="An instrument is not a peer of itself.",
            )
            return PeerEligibilityResult(
                left_key=left_key,
                right_key=right_key,
                status=PeerEligibilityStatus.NOT_COMPARABLE,
                reasons=(reason,),
                comparable=False,
            )

        left_res, left_err = self._try_resolve(left)
        right_res, right_err = self._try_resolve(right)

        if left_res is None or right_res is None:
            reasons: list[PeerEligibilityReason] = []
            if left_err is not None:
                reasons.append(left_err)
            if right_err is not None:
                reasons.append(right_err)
            status = PeerEligibilityStatus.INSUFFICIENT_DATA
            return PeerEligibilityResult(
                left_key=left_key,
                right_key=right_key,
                status=status,
                reasons=tuple(reasons),
                left_industry_id=(
                    None if left_res is None else left_res.industry_id
                ),
                right_industry_id=(
                    None if right_res is None else right_res.industry_id
                ),
                comparable=False,
            )

        left_policy = self._policies.get(
            left_res.peer_policy_id, version=left_res.peer_policy_version
        )
        right_policy = self._policies.get(
            right_res.peer_policy_id, version=right_res.peer_policy_version
        )

        left_status, left_reason = left_policy.evaluate_candidate(
            candidate_industry_id=right_res.industry_id,
            subject_business_model_id=left_res.business_model_id,
            candidate_business_model_id=right_res.business_model_id,
        )
        right_status, right_reason = right_policy.evaluate_candidate(
            candidate_industry_id=left_res.industry_id,
            subject_business_model_id=right_res.business_model_id,
            candidate_business_model_id=left_res.business_model_id,
        )
        status = stricter_status(left_status, right_status)
        return PeerEligibilityResult(
            left_key=left_key,
            right_key=right_key,
            status=status,
            reasons=(left_reason, right_reason),
            left_industry_id=left_res.industry_id,
            right_industry_id=right_res.industry_id,
            left_policy_id=left_res.peer_policy_id,
            right_policy_id=right_res.peer_policy_id,
            comparable=opts.accepts(status),
        )

    def evaluate_group(
        self,
        instruments: tuple[Instrument | str, ...] | list[Instrument | str],
        *,
        options: EligibilityOptions | None = None,
    ) -> GroupEligibilityResult:
        """Evaluate all unordered pairs; classify group as eligible/mixed/ineligible."""
        opts = options or EligibilityOptions()
        keys = tuple(dict.fromkeys(_symbol(i) for i in instruments))
        if len(keys) < 2:
            return GroupEligibilityResult(
                status=GroupEligibilityStatus.INELIGIBLE,
                pair_results=(),
                eligible_keys=(),
                ineligible_keys=keys,
                exclusions=(
                    "Group eligibility requires at least two distinct instruments.",
                ),
                options=opts,
            )

        pairs: list[PeerEligibilityResult] = []
        for i, left in enumerate(keys):
            for right in keys[i + 1 :]:
                pairs.append(self.evaluate_pair(left, right, options=opts))

        comparable_count = sum(1 for p in pairs if p.comparable)
        if comparable_count == len(pairs):
            group_status = GroupEligibilityStatus.ELIGIBLE
        elif comparable_count == 0:
            group_status = GroupEligibilityStatus.INELIGIBLE
        else:
            group_status = GroupEligibilityStatus.MIXED

        # A key is eligible if every pair involving it is comparable.
        pair_by_key: dict[str, list[PeerEligibilityResult]] = {k: [] for k in keys}
        for pair in pairs:
            pair_by_key[pair.left_key].append(pair)
            pair_by_key[pair.right_key].append(pair)

        eligible_keys = tuple(
            k
            for k in keys
            if pair_by_key[k] and all(p.comparable for p in pair_by_key[k])
        )
        ineligible_keys = tuple(k for k in keys if k not in set(eligible_keys))

        exclusions = tuple(
            f"{p.left_key}×{p.right_key}: {p.status.value} — {p.reasons[0].message}"
            for p in pairs
            if not p.comparable
        )
        return GroupEligibilityResult(
            status=group_status,
            pair_results=tuple(pairs),
            eligible_keys=eligible_keys,
            ineligible_keys=ineligible_keys,
            exclusions=exclusions,
            options=opts,
        )

    def _try_resolve(
        self, instrument: Instrument | str
    ) -> tuple[InstrumentMethodologyResolution | None, PeerEligibilityReason | None]:
        try:
            return self.resolve(instrument), None
        except IndustryError as exc:
            return None, PeerEligibilityReason(
                code="resolution_failed",
                message=str(exc),
            )


def _symbol(instrument: Instrument | str) -> str:
    if isinstance(instrument, Instrument):
        return instrument.symbol
    return instrument.strip().upper()
