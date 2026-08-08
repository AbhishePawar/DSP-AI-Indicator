"""Policy loader and default institutional policy (EPIC-A006)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy.models import (
    RULE_KINDS,
    InvestmentPolicy,
    PolicyException,
    PolicyRule,
    freeze_mapping,
)

__all__ = [
    "DEFAULT_POLICY_ID",
    "default_institutional_policy",
    "load_investment_policy",
]


DEFAULT_POLICY_ID = "institutional-default-v1"


def default_institutional_policy() -> InvestmentPolicy:
    """Deterministic built-in policy — structural presence checks only."""
    rules = (
        PolicyRule(
            rule_id="REQ-RO-PRESENT",
            kind="require_source_present",
            severity="violation",
            description="Research Object must be supplied.",
            params=freeze_mapping({"source": "research_object"}) or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-MOS-AVAILABLE",
            kind="require_section_available",
            severity="violation",
            description="margin_of_safety section must be available on Research Object.",
            params=freeze_mapping({"section": "margin_of_safety"})
            or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-QUALITY-AVAILABLE",
            kind="require_section_available",
            severity="warning",
            description="business_quality section should be available.",
            params=freeze_mapping({"section": "business_quality"})
            or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-RISK-AVAILABLE",
            kind="require_section_available",
            severity="warning",
            description="risk section should be available.",
            params=freeze_mapping({"section": "risk"}) or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-REPORT-PRESENT",
            kind="require_report_present",
            severity="warning",
            description="Institutional Report should be supplied.",
            params=freeze_mapping({}) or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-COMMITTEE-USABLE",
            kind="forbid_committee_stance",
            severity="violation",
            description="Committee consensus must not be unavailable.",
            params=freeze_mapping({"stances": ["unavailable"]}) or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="FORBID-MISSING-RESEARCH",
            kind="forbid_missing_research",
            severity="violation",
            description="Portfolio Intelligence must not list missing research links.",
            params=freeze_mapping({}) or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="FORBID-IMPORTANT-ALERTS",
            kind="forbid_alert_severity",
            severity="warning",
            description="Monitoring must not include important/unavailable alerts.",
            params=freeze_mapping({"severities": ["important", "unavailable"]})
            or freeze_mapping({}),
        ),
        PolicyRule(
            rule_id="REQ-DIFF-IDENTICAL",
            kind="require_diff_identical",
            severity="warning",
            description="Supplied research diffs should report identical_content.",
            params=freeze_mapping({}) or freeze_mapping({}),
        ),
    )
    return InvestmentPolicy(
        policy_id=DEFAULT_POLICY_ID,
        name="Institutional Default Policy",
        version="1.0.0",
        rules=rules,
        exceptions=(),
        metadata=freeze_mapping(
            {
                "read_only": True,
                "no_calculations": True,
                "no_scoring": True,
            }
        )
        or freeze_mapping({}),
    )


def load_investment_policy(
    data: Mapping[str, Any] | None = None,
    *,
    exceptions: list[Mapping[str, Any]] | None = None,
) -> InvestmentPolicy:
    """Load a policy mapping or fall back to the default institutional policy."""
    if data is None:
        policy = default_institutional_policy()
        if not exceptions:
            return policy
        data = policy.to_dict()

    if not isinstance(data, Mapping):
        raise ValueError("policy must be a mapping")

    rules_raw = data.get("rules") or []
    rules: list[PolicyRule] = []
    if isinstance(rules_raw, list):
        for row in rules_raw:
            if not isinstance(row, Mapping):
                continue
            kind = str(row.get("kind") or "")
            if kind not in RULE_KINDS:
                raise ValueError(f"unsupported rule kind {kind!r}")
            severity = str(row.get("severity") or "violation")
            if severity not in {"violation", "warning"}:
                raise ValueError(f"unsupported rule severity {severity!r}")
            rule_id = str(row.get("rule_id") or "").strip()
            if not rule_id:
                raise ValueError("rule_id is required")
            rules.append(
                PolicyRule(
                    rule_id=rule_id,
                    kind=kind,
                    severity=severity,
                    description=str(row.get("description") or rule_id),
                    params=freeze_mapping(dict(row.get("params") or {}))
                    or freeze_mapping({}),
                    enabled=bool(row.get("enabled", True)),
                )
            )

    if not rules:
        raise ValueError("policy must include at least one rule")

    exc_rows = list(data.get("exceptions") or [])
    if exceptions:
        exc_rows.extend(exceptions)
    excs: list[PolicyException] = []
    for row in exc_rows:
        if not isinstance(row, Mapping):
            continue
        eid = str(row.get("exception_id") or "").strip()
        rid = str(row.get("rule_id") or "").strip()
        if not eid or not rid:
            raise ValueError("exception_id and rule_id are required")
        excs.append(
            PolicyException(
                exception_id=eid,
                rule_id=rid,
                reason=str(row.get("reason") or "waived"),
                expires_at=row.get("expires_at"),
                created_at=row.get("created_at"),
            )
        )

    # Deterministic rule order by rule_id
    rules_sorted = tuple(sorted(rules, key=lambda r: r.rule_id))
    excs_sorted = tuple(sorted(excs, key=lambda e: (e.rule_id, e.exception_id)))

    return InvestmentPolicy(
        policy_id=str(data.get("policy_id") or DEFAULT_POLICY_ID),
        name=str(data.get("name") or "Custom Policy"),
        version=str(data.get("version") or "1.0.0"),
        rules=rules_sorted,
        exceptions=excs_sorted,
        metadata=freeze_mapping(dict(data.get("metadata") or {}))
        or freeze_mapping({}),
    )
