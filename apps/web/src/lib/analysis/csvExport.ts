/**
 * CSV export utility for analysis sections.
 * Converts section data to CSV and triggers browser download.
 */

export function downloadCsv(filename: string, rows: Record<string, string | number | null | undefined>[]) {
  if (!rows.length) return;

  const headers = Object.keys(rows[0]);
  const escape = (v: string | number | null | undefined): string => {
    if (v == null) return "";
    const s = String(v);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };

  const lines = [
    headers.map(escape).join(","),
    ...rows.map((row) => headers.map((h) => escape(row[h])).join(",")),
  ];

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function buildSectionCsvRows(
  sectionTitle: string,
  data: Array<{ label: string; value: string | number | null | undefined; note?: string }>,
): Record<string, string | number | null | undefined>[] {
  return data.map((item) => ({
    Section: sectionTitle,
    Metric: item.label,
    Value: item.value ?? "—",
    Note: item.note ?? "",
  }));
}
