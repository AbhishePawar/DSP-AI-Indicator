"""Investment Policy & Compliance Engine (EPIC-A006)."""

from __future__ import annotations

from dsp_platform.investment_policy.loader import (
    DEFAULT_POLICY_ID,
    default_institutional_policy,
    load_investment_policy,
)
from dsp_platform.investment_policy.models import (
    POLICY_SCHEMA_VERSION,
    POLICY_SERVICE_VERSION,
    RULE_KINDS,
    RULE_OUTCOMES,
    UNAVAILABLE_MESSAGE,
    ComplianceResult,
    InvestmentPolicy,
    PolicyException,
    PolicyRule,
    RuleResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.investment_policy.registry import ExceptionRegistry, RuleRegistry
from dsp_platform.investment_policy.serde import (
    compliance_result_from_dict,
    compliance_result_to_dict,
)
from dsp_platform.investment_policy.service import (
    ComplianceChecker,
    evaluate_investment_policy,
)
from dsp_platform.investment_policy.validation import (
    InvestmentPolicyValidationError,
    validate_compliance_result,
)

__all__ = [
    "DEFAULT_POLICY_ID",
    "POLICY_SCHEMA_VERSION",
    "POLICY_SERVICE_VERSION",
    "RULE_KINDS",
    "RULE_OUTCOMES",
    "UNAVAILABLE_MESSAGE",
    "ComplianceChecker",
    "ComplianceResult",
    "ExceptionRegistry",
    "InvestmentPolicy",
    "InvestmentPolicyValidationError",
    "PolicyException",
    "PolicyRule",
    "RuleRegistry",
    "RuleResult",
    "compliance_result_from_dict",
    "compliance_result_to_dict",
    "default_institutional_policy",
    "evaluate_investment_policy",
    "freeze_mapping",
    "load_investment_policy",
    "utc_now",
    "validate_compliance_result",
]
