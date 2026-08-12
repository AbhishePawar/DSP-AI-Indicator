/** Presentation helpers — never invent metrics (CV-001). */

export const DATA_UNAVAILABLE = "Data unavailable.";

export function displayMetric(value: unknown): string {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    value === "Unavailable" ||
    value === DATA_UNAVAILABLE
  ) {
    return DATA_UNAVAILABLE;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    if (Math.abs(value) <= 1 && value !== 0) {
      return `${(value * 100).toFixed(1)}%`;
    }
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function displayText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return DATA_UNAVAILABLE;
  }
  return String(value);
}
