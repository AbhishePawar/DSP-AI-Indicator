"use client";

import { useCallback } from "react";
import { Download } from "lucide-react";
import { downloadCsv, buildSectionCsvRows } from "@/lib/analysis/csvExport";

interface CsvExportButtonProps {
  sectionTitle: string;
  ticker?: string;
  data: Array<{ label: string; value: string | number | null | undefined; note?: string }>;
  className?: string;
}

export function CsvExportButton({ sectionTitle, ticker, data, className }: CsvExportButtonProps) {
  const handleExport = useCallback(() => {
    if (!data.length) return;
    const rows = buildSectionCsvRows(sectionTitle, data);
    const slug = sectionTitle.toLowerCase().replace(/\s+/g, "_");
    const tickerPart = ticker ? `${ticker.toUpperCase()}_` : "";
    const filename = `${tickerPart}${slug}.csv`;
    downloadCsv(filename, rows);
  }, [sectionTitle, ticker, data]);

  if (!data.length) return null;

  return (
    <button
      type="button"
      onClick={handleExport}
      title={`Export ${sectionTitle} as CSV`}
      aria-label={`Export ${sectionTitle} as CSV`}
      className={[
        "inline-flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface-2)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)] hover:text-[var(--fg)] hover:bg-[var(--surface)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]",
        className ?? "",
      ].join(" ")}
    >
      <Download className="size-3" aria-hidden />
      CSV
    </button>
  );
}
