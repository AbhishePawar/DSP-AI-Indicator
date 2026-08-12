/**
 * EPIC-F008 — Export helpers for backend admin payloads only.
 * No client-side aggregation or invented metrics.
 */

export function downloadText(
  filename: string,
  content: string,
  mime = "text/plain;charset=utf-8",
): void {
  if (typeof document === "undefined") return;
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function toJsonSnapshot(payload: unknown): string {
  return `${JSON.stringify(payload ?? { message: "Data unavailable." }, null, 2)}\n`;
}

/** Flatten a list of records into CSV using union of top-level keys only. */
export function recordsToCsv(records: unknown[]): string {
  if (!Array.isArray(records) || records.length === 0) {
    return "message\nData unavailable.\n";
  }
  const rows = records.filter(
    (r): r is Record<string, unknown> =>
      typeof r === "object" && r !== null && !Array.isArray(r),
  );
  if (rows.length === 0) {
    return "message\nData unavailable.\n";
  }
  const keys = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((k) => set.add(k));
      return set;
    }, new Set<string>()),
  );
  const escape = (value: unknown) => {
    const text =
      value === null || value === undefined
        ? "Data unavailable."
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);
    if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
    return text;
  };
  const lines = [
    keys.join(","),
    ...rows.map((row) => keys.map((k) => escape(row[k])).join(",")),
  ];
  return `${lines.join("\n")}\n`;
}

export function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Data unavailable.";
  }
  if (typeof value === "boolean" || typeof value === "number") {
    return String(value);
  }
  if (typeof value === "string") return value || "Data unavailable.";
  try {
    return JSON.stringify(value);
  } catch {
    return "Data unavailable.";
  }
}
