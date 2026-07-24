"""Peer eligibility framework tests."""

from __future__ import annotations

import pytest
from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass

from industry import (
    EligibilityOptions,
    GroupEligibilityStatus,
    IndustryError,
    IndustryMethodologyRegistry,
    InstrumentIndustryAssignment,
    InstrumentIndustryRegistry,
    InvestmentCharacteristicsRegistry,
    PeerEligibilityEvaluator,
    PeerEligibilityPolicyRegistry,
    PeerEligibilityStatus,
    IndustryTaxonomy,
    seed_peer_eligibility_context,
)


def _ctx() -> tuple[
    IndustryTaxonomy,
    InstrumentIndustryRegistry,
    IndustryMethodologyRegistry,
    PeerEligibilityPolicyRegistry,
    PeerEligibilityEvaluator,
]:
    tax = IndustryTaxonomy()
    chars = InvestmentCharacteristicsRegistry()
    methods = IndustryMethodologyRegistry(tax, chars)
    policies = PeerEligibilityPolicyRegistry(tax)
    assignments = InstrumentIndustryRegistry(tax)
    seed_peer_eligibility_context(tax, chars, methods, policies, assignments)
    evaluator = PeerEligibilityEvaluator(
        assignments=assignments,
        methodologies=methods,
        policies=policies,
    )
    return tax, assignments, methods, policies, evaluator


class TestDirectRelatedRefusal:
    def test_direct_peers(self) -> None:
        *_, evaluator = _ctx()
        result = evaluator.evaluate_pair("HDFCBANK", "ICICIBANK")
        assert result.status is PeerEligibilityStatus.DIRECT_PEER
        assert result.comparable is True
        assert result.reasons

    def test_related_peers(self) -> None:
        *_, evaluator = _ctx()
        result = evaluator.evaluate_pair(
            "HDFCBANK",
            "BAJFINANCE",
            options=EligibilityOptions(allow_related=True),
        )
        assert result.status is PeerEligibilityStatus.RELATED_PEER
        assert result.comparable is True
        # Related not accepted by default options
        strict = evaluator.evaluate_pair("HDFCBANK", "BAJFINANCE")
        assert strict.status is PeerEligibilityStatus.RELATED_PEER
        assert strict.comparable is False

    def test_not_comparable_bank_vs_software(self) -> None:
        *_, evaluator = _ctx()
        result = evaluator.evaluate_pair("HDFCBANK", "TCS")
        assert result.status is PeerEligibilityStatus.NOT_COMPARABLE
        assert result.comparable is False
        assert any("refuse" in r.message.lower() or "not_comparable" in r.code
                   or "refuses" in r.message.lower()
                   for r in result.reasons)


class TestResolutionFailures:
    def test_missing_industry_binding(self) -> None:
        *_, assignments, methods, policies, evaluator = _ctx()
        with pytest.raises(IndustryError, match="no IndustryIdentity binding"):
            evaluator.resolve("UNKNOWN")

        result = evaluator.evaluate_pair("HDFCBANK", "UNKNOWN")
        assert result.status is PeerEligibilityStatus.INSUFFICIENT_DATA
        assert result.comparable is False

    def test_missing_methodology(self) -> None:
        tax, assignments, methods, policies, _ = _ctx()
        # Bind to life insurance which has identity but no methodology
        assignments.register(
            InstrumentIndustryAssignment(
                symbol="LICI",
                industry_id="dsp.industry.life_insurance",
            )
        )
        evaluator = PeerEligibilityEvaluator(
            assignments=assignments,
            methodologies=methods,
            policies=policies,
        )
        with pytest.raises(IndustryError, match="no active IndustryMethodology"):
            evaluator.resolve("LICI")

    def test_resolve_instrument_object(self) -> None:
        *_, evaluator = _ctx()
        instrument = Instrument(
            symbol="TCS",
            asset_class=AssetClass.EQUITY,
            currency="INR",
        )
        resolved = evaluator.resolve(instrument)
        assert resolved.industry_id == "dsp.industry.software"
        assert resolved.peer_policy_id == "dsp.peer_policy.software"


class TestGroupEligibility:
    def test_eligible_group(self) -> None:
        *_, evaluator = _ctx()
        group = evaluator.evaluate_group(("HDFCBANK", "ICICIBANK"))
        assert group.status is GroupEligibilityStatus.ELIGIBLE
        assert group.exclusions == ()

    def test_ineligible_group(self) -> None:
        *_, evaluator = _ctx()
        group = evaluator.evaluate_group(("HDFCBANK", "TCS"))
        assert group.status is GroupEligibilityStatus.INELIGIBLE
        assert group.exclusions

    def test_mixed_universe(self) -> None:
        *_, evaluator = _ctx()
        group = evaluator.evaluate_group(
            ("HDFCBANK", "ICICIBANK", "TCS", "NTPC"),
            options=EligibilityOptions(allow_related=True),
        )
        assert group.status is GroupEligibilityStatus.MIXED
        # Bank×bank pair is comparable; cross-industry pairs are not.
        assert any(p.comparable for p in group.pair_results)
        assert any(not p.comparable for p in group.pair_results)
        assert group.exclusions
        assert set(group.ineligible_keys) >= {"TCS", "NTPC", "HDFCBANK", "ICICIBANK"}

    def test_scale_pairs(self) -> None:
        tax, assignments, methods, policies, evaluator = _ctx()
        # Add more bank peers
        for i in range(10):
            sym = f"BANK{i:02d}"
            assignments.register(
                InstrumentIndustryAssignment(
                    symbol=sym,
                    industry_id="dsp.industry.commercial_banking",
                )
            )
        symbols = tuple(f"BANK{i:02d}" for i in range(10))
        group = evaluator.evaluate_group(symbols)
        assert group.status is GroupEligibilityStatus.ELIGIBLE
        assert len(group.pair_results) == 45  # C(10,2)
