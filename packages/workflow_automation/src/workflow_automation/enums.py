"""workflow_automation enumerations."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AlertRuleType",
    "AlertStatus",
    "NotificationKind",
    "ScheduleFormat",
    "ScheduleFrequency",
]


class AlertRuleType(StrEnum):
    """Which already-computed signal an alert rule is evaluated against."""

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VALUATION_FLIP = "valuation_flip"
    RESEARCH_STALE = "research_stale"
    EARNINGS_UPCOMING = "earnings_upcoming"


class AlertStatus(StrEnum):
    """Outcome of evaluating one alert rule."""

    TRIGGERED = "triggered"
    NOT_TRIGGERED = "not_triggered"
    UNAVAILABLE = "unavailable"


class ScheduleFrequency(StrEnum):
    """Declared cadence of a Scheduled Report definition."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduleFormat(StrEnum):
    """Serialization format for a Scheduled Report / Export run."""

    JSON = "json"
    CSV = "csv"


class NotificationKind(StrEnum):
    """Category of a Notification Center entry."""

    ALERT = "alert"
    SCHEDULED_REPORT = "scheduled_report"
    SYSTEM = "system"
