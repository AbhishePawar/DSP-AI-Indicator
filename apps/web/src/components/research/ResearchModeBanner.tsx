"use client";

import { isResearchOnly } from "@/lib/featureFlags";
import { RESEARCH_DISCLAIMER } from "@/lib/product";

/** Research Mode banner — shown when SEBI recommendation UI is inactive.
 *  Typography and accent-border aligned to the institutional data-table
 *  and section-header pattern used across /research and /analysis.
 */
export function ResearchModeBanner() {
  if (!isResearchOnly()) return null;
  return (
    <div
      role="alert"
      className="border-l-2 border-[var(--accent)] bg-[var(--surface-2)] px-3 py-2"
    >
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        Research Mode
      </p>
      <p className="mt-1 text-xs text-[var(--fg)] leading-relaxed">
        {RESEARCH_DISCLAIMER}
      </p>
    </div>
  );
}
