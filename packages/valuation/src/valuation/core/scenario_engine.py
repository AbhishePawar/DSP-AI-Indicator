"""Reusable scenario framework for valuation engines."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from valuation.core.errors import ScenarioError
from valuation.core.interfaces import ScenarioProvider
from valuation.core.result_models import ScenarioKind, ScenarioOutcome

__all__ = ["ScenarioEngine", "ScenarioSpec"]

Evaluator = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class ScenarioSpec:
    """Specification for one scenario overlay."""

    __slots__ = ("kind", "overrides")

    def __init__(self, kind: ScenarioKind, overrides: Mapping[str, Any] | None = None) -> None:
        self.kind = kind
        self.overrides = dict(overrides or {})


class ScenarioEngine(ScenarioProvider):
    """Run bear/base/bull/custom scenarios via a caller-supplied evaluator.

    The evaluator receives merged context (base + overrides) and must return
    a mapping with optional keys: intrinsic_value, equity_value,
    intrinsic_value_per_share, notes, extras.
    """

    def default_specs(
        self,
        *,
        bear: Mapping[str, Any] | None = None,
        base: Mapping[str, Any] | None = None,
        bull: Mapping[str, Any] | None = None,
    ) -> tuple[ScenarioSpec, ...]:
        """Build standard Bear/Base/Bull specs."""
        return (
            ScenarioSpec(ScenarioKind.bear(), bear),
            ScenarioSpec(ScenarioKind.base(), base),
            ScenarioSpec(ScenarioKind.bull(), bull),
        )

    def scenarios(
        self,
        context: Mapping[str, Any],
        *,
        specs: Sequence[ScenarioSpec] | None = None,
        evaluator: Evaluator | None = None,
    ) -> tuple[ScenarioOutcome, ...]:
        """Evaluate scenarios.

        If ``evaluator`` is omitted, returns empty intrinsic placeholders
        for each spec (infrastructure smoke path).
        """
        if specs is None:
            specs = self.default_specs()
        if evaluator is None:
            return tuple(
                ScenarioOutcome(
                    kind=s.kind,
                    intrinsic_value=None,
                    equity_value=None,
                    intrinsic_value_per_share=None,
                    notes="No evaluator provided",
                )
                for s in specs
            )

        outcomes: list[ScenarioOutcome] = []
        for spec in specs:
            merged = {**dict(context), **spec.overrides}
            try:
                raw = evaluator(merged)
            except Exception as exc:  # noqa: BLE001 — wrap as ScenarioError
                raise ScenarioError(
                    f"scenario {spec.kind.name} failed: {exc}"
                ) from exc
            outcomes.append(
                ScenarioOutcome(
                    kind=spec.kind,
                    intrinsic_value=_opt_float(raw.get("intrinsic_value")),
                    equity_value=_opt_float(raw.get("equity_value")),
                    intrinsic_value_per_share=_opt_float(
                        raw.get("intrinsic_value_per_share")
                    ),
                    notes=str(raw.get("notes") or ""),
                    extras=dict(raw.get("extras") or {}),
                )
            )
        return tuple(outcomes)


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
