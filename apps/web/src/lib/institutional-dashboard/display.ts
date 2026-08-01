/** CV-001 display helpers — never invent numbers. */

import type {
  ConfidenceLevel,
  SourceKind,
  ValueCategory,
} from "@/lib/trust/labels";
import {
  DATA_UNAVAILABLE,
  UNABLE_TO_CALCULATE,
  type DashboardField,
} from "@/lib/institutional-dashboard/types";

export function unavailableField<T = string>(): DashboardField<T> {
  return {
    presence: "unavailable",
    value: null,
    category: "unavailable",
    source: "unavailable",
    display: DATA_UNAVAILABLE,
  };
}

export function unableToCalculateField<T = string>(): DashboardField<T> {
  return {
    presence: "unable_to_calculate",
    value: null,
    category: "unavailable",
    source: "unavailable",
    display: UNABLE_TO_CALCULATE,
  };
}

export function availableField<T>(
  value: T,
  category: ValueCategory,
  source: SourceKind,
  format?: (v: T) => string,
): DashboardField<T> {
  const display = format ? format(value) : String(value);
  return {
    presence: "available",
    value,
    category,
    source,
    display: display.trim() ? display : DATA_UNAVAILABLE,
  };
}

export function fieldFromUnknown(
  value: unknown,
  category: ValueCategory,
  source: SourceKind,
  opts?: { money?: boolean; pct?: boolean; unable?: boolean },
): DashboardField {
  if (value === null || value === undefined || value === "") {
    return opts?.unable ? unableToCalculateField() : unavailableField();
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    if (opts?.money) {
      return availableField(
        value.toLocaleString(undefined, {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 2,
        }),
        category,
        source,
      );
    }
    if (opts?.pct) {
      return availableField(
        `${(value <= 1 && value >= -1 ? value * 100 : value).toFixed(1)}%`,
        category,
        source,
      );
    }
    return availableField(String(value), category, source);
  }
  if (typeof value === "string" && value.trim()) {
    return availableField(value.trim(), category, source);
  }
  return opts?.unable ? unableToCalculateField() : unavailableField();
}

export function emptyExplainability() {
  return {
    formula: unavailableField(),
    inputs: unavailableField<string[]>(),
    weights: unavailableField(),
    calculation: unavailableField(),
    engines: unavailableField<string[]>(),
    confidence: unavailableField(),
    supportingData: unavailableField<string[]>(),
    reasoning: unavailableField(),
    contribution: unavailableField(),
  };
}

export function presenceOk(field: DashboardField): boolean {
  return field.presence === "available" && field.value != null;
}

export function mapConfidenceLevel(
  value: number | null | undefined,
): ConfidenceLevel | null {
  if (value == null || !Number.isFinite(value)) return null;
  if (value >= 0.85) return "very_high";
  if (value >= 0.7) return "high";
  if (value >= 0.5) return "moderate";
  if (value > 0) return "low";
  return "insufficient_evidence";
}
