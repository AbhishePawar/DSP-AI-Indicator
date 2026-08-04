"""Investment Policy & Compliance models (EPIC-A006)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "POLICY_SCHEMA_VERSION",
    "POLICY_SERVICE_VERSION",
    "RULE_KINDS",
    "RULE_OUTCOMES",
    "UNAVAILABLE_MESSAGE",
    "ComplianceResult",
    "InvestmentPolicy",
    "PolicyException",
    "PolicyRule",
    "RuleResult",
    "freeze_mapping",
    "utc_now",
]

POLICY_SCHEMA_VERSION = "1.0.0"
POLICY_SERVICE_VERSION = "1.0.0"

RULE_KINDS = (
    "require_section_available",
    "require_source_present",
    "require_committee_stance",
    "forbid_committee_stance",
    "forbid_missing_research",
    "forbid_alert_severity",
    "require_diff_identical",
    "require_report_present",
)

RULE_OUTCOMES = ("pass", "warning", "violation", "unavailable", "waived")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    kind: str
    severity: str  # violation | warning
    description: str
    params: Mapping[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "kind": self.kind,
            "severity": self.severity,
            "description": self.description,
            "params": dict(self.params),
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class PolicyException:
    exception_id: str
    rule_id: str
    reason: str
    expires_at: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exception_id": self.exception_id,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class InvestmentPolicy:
    policy_id: str
    name: str
    version: str
    rules: tuple[PolicyRule, ...]
    exceptions: tuple[PolicyException, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "version": self.version,
            "rules": [r.to_dict() for r in self.rules],
            "exceptions": [e.to_dict() for e in self.exceptions],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class RuleResult:
    rule_id: str
    kind: str
    outcome: str
    severity: str
    message: str
    citations: tuple[Mapping[str, Any], ...]
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "rule_id": self.rule_id,
            "kind": self.kind,
            "outcome": self.outcome,
            "severity": self.severity,
            "message": self.message,
            "citations": [_plain(c) for c in self.citations],
            "evidence": _plain(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class ComplianceResult:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    subject: str
    policy: Mapping[str, Any]
    rule_results: tuple[RuleResult, ...]
    summary: Mapping[str, Any]
    violations: tuple[Mapping[str, Any], ...]
    warnings: tuple[Mapping[str, Any], ...]
    audit_trail: tuple[Mapping[str, Any], ...]
    citations: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    audit: Mapping[str, Any]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "subject": self.subject,
            "policy": _plain(self.policy),
            "rule_results": [r.to_dict() for r in self.rule_results],
            "summary": _plain(self.summary),
            "violations": [_plain(v) for v in self.violations],
            "warnings": [_plain(w) for w in self.warnings],
            "audit_trail": [_plain(a) for a in self.audit_trail],
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
