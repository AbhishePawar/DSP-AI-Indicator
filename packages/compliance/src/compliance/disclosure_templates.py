"""Versioned Research Mode disclosure templates — IST / INR (PEP-004)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

from compliance.disclaimer_engine import Disclaimer, default_research_disclaimer
from compliance.disclosures import Disclosure, DisclosurePort
from compliance.feature_flags import FeatureFlags

__all__ = [
    "DisclosureTemplateCatalog",
    "InMemoryDisclosurePort",
    "ResearchModeDisclosureEngine",
    "format_inr",
    "format_ist",
]


# Asia/Kolkata without requiring tzdata package (Windows CI / empty deps).
IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def format_ist(moment: datetime | None = None) -> str:
    """Format a moment in Asia/Kolkata for disclosure footers."""
    dt = moment or datetime.now(tz=UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def format_inr(amount: float | int | str, *, symbol: str = "₹") -> str:
    """Simple INR presentation helper (not a FX engine)."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return f"{symbol}{amount}"
    # Indian-style grouping approximation for display
    negative = value < 0
    value = abs(value)
    whole = int(value)
    frac = f"{value - whole:.2f}"[1:]
    s = str(whole)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts: list[str] = []
        while rest:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(parts + [last3]) if parts else last3
    out = f"{symbol}{grouped}{frac}"
    return f"-{out}" if negative else out


@dataclass(frozen=True, slots=True)
class DisclosureTemplateCatalog:
    """Versioned disclosure set for Research Mode."""

    version: str
    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    disclosures: tuple[Disclosure, ...] = ()


def research_mode_templates(*, version: str = "2026.1") -> DisclosureTemplateCatalog:
    as_of = format_ist()
    body_research = (
        "This platform operates in Research Mode by default. Outputs are educational "
        "investment research and decision-support materials. They are not Buy, Sell, "
        "or Hold recommendations under SEBI Research Analyst / Investment Adviser "
        "regulations unless SEBI Mode is explicitly activated under a separate legal epic.\n\n"
        f"Presentation timezone: Asia/Kolkata (IST). Currency presentation: INR (₹).\n"
        f"Disclosure version: {version}. Generated: {as_of}."
    )
    body_data = (
        "Personal data is processed under the Digital Personal Data Protection Act, 2023 "
        "for specified purposes with versioned consent. You may request export or erasure "
        "subject to legal retention overrides (including CERT-In audit retention)."
    )
    body_ai = (
        "AI language features explain engine outputs; they do not override deterministic "
        "valuation, quality, or committee scores. Always verify numbers against sourced data."
    )
    return DisclosureTemplateCatalog(
        version=version,
        disclosures=(
            Disclosure(
                disclosure_id=f"research_mode_{version}",
                title="Research Mode disclosure",
                body=body_research,
                audience="retail",
                mandatory=True,
                version=version,
            ),
            Disclosure(
                disclosure_id=f"dpdp_notice_{version}",
                title="DPDP privacy notice (summary)",
                body=body_data,
                audience="retail",
                mandatory=True,
                version=version,
            ),
            Disclosure(
                disclosure_id=f"ai_governance_{version}",
                title="AI explanation boundaries",
                body=body_ai,
                audience="retail",
                mandatory=True,
                version=version,
            ),
        ),
    )


class InMemoryDisclosurePort:
    """DisclosurePort reference — mode-aware Research Mode templates."""

    def __init__(self, catalog: DisclosureTemplateCatalog | None = None) -> None:
        self._catalog = catalog or research_mode_templates()

    def list_active(self, *, mode: str) -> tuple[Disclosure, ...]:
        mode_l = mode.strip().lower()
        if mode_l in {"research", "research_mode", "default"}:
            return self._catalog.disclosures
        if mode_l in {"sebi", "sebi_mode"}:
            # SEBI Mode still gated — return research disclosures plus a placeholder notice.
            extra = Disclosure(
                disclosure_id="sebi_mode_gated",
                title="SEBI Mode not activated",
                body=(
                    "SEBI Mode remains gated pending registration and legal activation. "
                    "Research Mode disclosures continue to apply."
                ),
                audience="retail",
                mandatory=True,
                version=self._catalog.version,
            )
            return self._catalog.disclosures + (extra,)
        return self._catalog.disclosures


class ResearchModeDisclosureEngine:
    """Combines DisclosurePort + disclaimer engine for Research Mode."""

    def __init__(
        self,
        disclosures: DisclosurePort | None = None,
        *,
        flags: FeatureFlags | None = None,
    ) -> None:
        self._disclosures = disclosures or InMemoryDisclosurePort()
        self._flags = flags or FeatureFlags()

    def for_flags(self, flags: FeatureFlags) -> tuple[Disclaimer, ...]:
        base = (default_research_disclaimer(),)
        if flags.sebi_mode and not flags.recommendation_mode:
            return base + (
                Disclaimer(
                    disclaimer_id="sebi_inconsistent",
                    text="SEBI Mode flag is on without Recommendation Mode — configuration invalid.",
                    severity="high",
                ),
            )
        return base

    def list_disclosures(self, *, mode: str | None = None) -> tuple[Disclosure, ...]:
        if mode is not None:
            return self._disclosures.list_active(mode=mode)
        if self._flags.sebi_mode:
            return self._disclosures.list_active(mode="sebi")
        return self._disclosures.list_active(mode="research")
