"use client";

import { Button } from "@/components/ds";
import type { InstitutionalDashboardView } from "@/lib/institutional-dashboard/types";
import { researchStandardsPass } from "@/lib/institutional-dashboard/rsValidation";

export function ExportBar({ view }: { view: InstitutionalDashboardView }) {
  const rsOk = researchStandardsPass(view.rsValidation);

  function onCopyJson() {
    const payload = {
      ticker: view.ticker,
      generatedAt: view.executive.reportTimestamp.display,
      rsValidation: view.rsValidation,
      executive: {
        price: view.executive.currentMarketPrice.display,
        intrinsic: view.executive.intrinsicValue.display,
        mos: view.executive.marginOfSafety.display,
      },
    };
    void navigator.clipboard?.writeText(JSON.stringify(payload, null, 2));
  }

  function onPrint() {
    window.print();
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <p className="text-sm text-[var(--muted)]">
        RS panel-structure check (not report completeness):{" "}
        <span className={rsOk ? "text-[var(--accent)]" : "text-[var(--danger-fg)]"}>
          {rsOk ? "STRUCTURE OK" : "STRUCTURE GAP"}
        </span>
      </p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" onClick={onCopyJson}>
          Copy summary JSON
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onPrint}>
          Print
        </Button>
      </div>
    </div>
  );
}
