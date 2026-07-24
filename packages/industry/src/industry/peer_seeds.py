"""Illustrative peer eligibility policies and instrument bindings."""

from __future__ import annotations

from industry.enums import PeerEligibilityStatus
from industry.methodology_registry import IndustryMethodologyRegistry
from industry.methodology_seeds import (
    register_example_methodologies,
    seed_example_industry_context,
)
from industry.models import IndustryIdentity
from industry.peer_eligibility import (
    InstrumentIndustryAssignment,
    PeerEligibilityPolicy,
)
from industry.peer_registry import (
    InstrumentIndustryRegistry,
    PeerEligibilityPolicyRegistry,
)
from industry.characteristics_registry import InvestmentCharacteristicsRegistry
from industry.taxonomy import IndustryTaxonomy

__all__ = [
    "EXAMPLE_PEER_POLICY_IDS",
    "build_example_peer_policies",
    "register_example_peer_policies",
    "seed_peer_eligibility_context",
]

EXAMPLE_PEER_POLICY_IDS: tuple[str, ...] = (
    "dsp.peer_policy.commercial_banking",
    "dsp.peer_policy.electric_utilities",
    "dsp.peer_policy.premium_consumer_franchise",
    "dsp.peer_policy.software",
    "dsp.peer_policy.nbfc",
)

_EXTRA_INDUSTRIES: tuple[tuple[str, str], ...] = (
    ("dsp.industry.nbfc", "NBFC"),
    ("dsp.industry.software", "Software"),
    ("dsp.industry.life_insurance", "Life Insurance"),
)


def build_example_peer_policies() -> tuple[PeerEligibilityPolicy, ...]:
    return (
        PeerEligibilityPolicy(
            id="dsp.peer_policy.commercial_banking",
            version="1.0.0",
            subject_industry_id="dsp.industry.commercial_banking",
            same_industry_status=PeerEligibilityStatus.DIRECT_PEER,
            related_industry_ids=("dsp.industry.nbfc",),
            limited_industry_ids=(),
            not_comparable_industry_ids=(
                "dsp.industry.software",
                "dsp.industry.life_insurance",
                "dsp.industry.electric_utilities",
                "dsp.industry.premium_consumer_franchise",
            ),
            default_status=PeerEligibilityStatus.NOT_COMPARABLE,
            notes=(
                "Banks × Banks → DIRECT; Banks × NBFC → RELATED; "
                "Banks × Software → NOT_COMPARABLE.",
            ),
        ),
        PeerEligibilityPolicy(
            id="dsp.peer_policy.electric_utilities",
            version="1.0.0",
            subject_industry_id="dsp.industry.electric_utilities",
            same_industry_status=PeerEligibilityStatus.DIRECT_PEER,
            related_industry_ids=(),
            not_comparable_industry_ids=(
                "dsp.industry.commercial_banking",
                "dsp.industry.software",
                "dsp.industry.premium_consumer_franchise",
                "dsp.industry.nbfc",
                "dsp.industry.life_insurance",
            ),
            default_status=PeerEligibilityStatus.NOT_COMPARABLE,
            notes=("Utilities compare only within electric utilities by default.",),
        ),
        PeerEligibilityPolicy(
            id="dsp.peer_policy.premium_consumer_franchise",
            version="1.0.0",
            subject_industry_id="dsp.industry.premium_consumer_franchise",
            same_industry_status=PeerEligibilityStatus.DIRECT_PEER,
            not_comparable_industry_ids=(
                "dsp.industry.commercial_banking",
                "dsp.industry.electric_utilities",
                "dsp.industry.software",
                "dsp.industry.nbfc",
                "dsp.industry.life_insurance",
            ),
            default_status=PeerEligibilityStatus.NOT_COMPARABLE,
        ),
        PeerEligibilityPolicy(
            id="dsp.peer_policy.software",
            version="1.0.0",
            subject_industry_id="dsp.industry.software",
            same_industry_status=PeerEligibilityStatus.DIRECT_PEER,
            not_comparable_industry_ids=(
                "dsp.industry.commercial_banking",
                "dsp.industry.electric_utilities",
                "dsp.industry.premium_consumer_franchise",
                "dsp.industry.nbfc",
                "dsp.industry.life_insurance",
            ),
            default_status=PeerEligibilityStatus.NOT_COMPARABLE,
            notes=("Software × Banks must refuse — never silent compare.",),
        ),
        PeerEligibilityPolicy(
            id="dsp.peer_policy.nbfc",
            version="1.0.0",
            subject_industry_id="dsp.industry.nbfc",
            same_industry_status=PeerEligibilityStatus.DIRECT_PEER,
            related_industry_ids=("dsp.industry.commercial_banking",),
            not_comparable_industry_ids=(
                "dsp.industry.software",
                "dsp.industry.electric_utilities",
                "dsp.industry.premium_consumer_franchise",
                "dsp.industry.life_insurance",
            ),
            default_status=PeerEligibilityStatus.NOT_COMPARABLE,
            notes=("NBFC × Banks → RELATED; NBFC × Software → NOT_COMPARABLE.",),
        ),
    )


def register_example_peer_policies(
    registry: PeerEligibilityPolicyRegistry,
) -> PeerEligibilityPolicyRegistry:
    for policy in build_example_peer_policies():
        registry.register(policy)
    return registry


def seed_peer_eligibility_context(
    taxonomy: IndustryTaxonomy,
    characteristics: InvestmentCharacteristicsRegistry,
    methodologies: IndustryMethodologyRegistry,
    policies: PeerEligibilityPolicyRegistry,
    assignments: InstrumentIndustryRegistry,
) -> None:
    """Seed identities, methodologies, peer policies, and sample bindings."""
    seed_example_industry_context(taxonomy, characteristics)
    for industry_id, name in _EXTRA_INDUSTRIES:
        if not taxonomy.contains(industry_id):
            taxonomy.register(IndustryIdentity(id=industry_id, name=name))
    register_example_methodologies(methodologies)
    # Extra methodologies so related/refusal examples can resolve both sides.
    from industry.methodology import (
        IndustryMethodology,
        PeerEligibilityPolicyRef,
        ValuationProfile,
    )
    from industry.enums import ComparisonDimension

    for mid, iid, name, policy_id in (
        (
            "dsp.methodology.software",
            "dsp.industry.software",
            "Software",
            "dsp.peer_policy.software",
        ),
        (
            "dsp.methodology.nbfc",
            "dsp.industry.nbfc",
            "NBFC",
            "dsp.peer_policy.nbfc",
        ),
    ):
        if not methodologies.contains(mid):
            methodologies.register(
                IndustryMethodology(
                    id=mid,
                    industry_id=iid,
                    version="1.0.0",
                    name=name,
                    valuation=ValuationProfile(
                        preferred=("dcf", "owner_earnings"),
                        acceptable=("earnings_multiple",),
                    ),
                    dimensions=(
                        ComparisonDimension.GROWTH,
                        ComparisonDimension.QUALITY,
                        ComparisonDimension.VALUATION,
                    ),
                    peer_policy=PeerEligibilityPolicyRef(policy_id=policy_id),
                )
            )
    register_example_peer_policies(policies)

    sample_bindings = (
        InstrumentIndustryAssignment(
            symbol="HDFCBANK",
            industry_id="dsp.industry.commercial_banking",
            business_model_id="dsp.business.deposit_franchise",
        ),
        InstrumentIndustryAssignment(
            symbol="ICICIBANK",
            industry_id="dsp.industry.commercial_banking",
            business_model_id="dsp.business.deposit_franchise",
        ),
        InstrumentIndustryAssignment(
            symbol="BAJFINANCE",
            industry_id="dsp.industry.nbfc",
            business_model_id="dsp.business.retail_nbfc",
        ),
        InstrumentIndustryAssignment(
            symbol="TCS",
            industry_id="dsp.industry.software",
        ),
        InstrumentIndustryAssignment(
            symbol="INFY",
            industry_id="dsp.industry.software",
        ),
        InstrumentIndustryAssignment(
            symbol="NTPC",
            industry_id="dsp.industry.electric_utilities",
        ),
        InstrumentIndustryAssignment(
            symbol="POWERGRID",
            industry_id="dsp.industry.electric_utilities",
        ),
        InstrumentIndustryAssignment(
            symbol="TITAN",
            industry_id="dsp.industry.premium_consumer_franchise",
        ),
    )
    for binding in sample_bindings:
        if not assignments.contains(binding.symbol):
            assignments.register(binding)
