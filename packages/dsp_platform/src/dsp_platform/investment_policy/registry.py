"""Rule registry and exception registry (EPIC-A006)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy.models import PolicyException, PolicyRule

__all__ = [
    "ExceptionRegistry",
    "RuleRegistry",
]


class RuleRegistry:
    """Ordered registry of policy rules."""

    def __init__(self, rules: tuple[PolicyRule, ...] | list[PolicyRule] = ()) -> None:
        self._rules: dict[str, PolicyRule] = {r.rule_id: r for r in rules}

    def register(self, rule: PolicyRule) -> None:
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> PolicyRule | None:
        return self._rules.get(rule_id)

    def list_rules(self) -> tuple[PolicyRule, ...]:
        return tuple(sorted(self._rules.values(), key=lambda r: r.rule_id))

    def enabled_rules(self) -> tuple[PolicyRule, ...]:
        return tuple(r for r in self.list_rules() if r.enabled)


class ExceptionRegistry:
    """Waivers keyed by rule_id — does not mutate artifacts."""

    def __init__(
        self, exceptions: tuple[PolicyException, ...] | list[PolicyException] = ()
    ) -> None:
        self._by_rule: dict[str, list[PolicyException]] = {}
        for exc in exceptions:
            self._by_rule.setdefault(exc.rule_id, []).append(exc)

    def register(self, exc: PolicyException) -> None:
        self._by_rule.setdefault(exc.rule_id, []).append(exc)

    def for_rule(self, rule_id: str) -> tuple[PolicyException, ...]:
        rows = self._by_rule.get(rule_id) or []
        return tuple(sorted(rows, key=lambda e: e.exception_id))

    def is_waived(self, rule_id: str) -> PolicyException | None:
        rows = self.for_rule(rule_id)
        return rows[0] if rows else None

    def to_list(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for rule_id in sorted(self._by_rule.keys()):
            for exc in self.for_rule(rule_id):
                out.append(exc.to_dict())
        return out
