"use client";

import type { ResearchCitationId } from "@/lib/copilot/types";

const SECTION_HREF: Record<ResearchCitationId, string> = {
  Valuation: "valuation",
  "Economic Moat": "economic-moat",
  "Management Quality": "management-quality",
  "Financial Strength": "financial-strength",
  "Earnings Quality": "earnings-quality",
  "Growth Quality": "growth-quality",
  "Investment Committee": "investment-committee",
  Recommendation: "recommendation",
  Overview: "overview",
};

export function ResearchCitationList({
  citations,
  ticker,
}: {
  citations?: ResearchCitationId[];
  ticker?: string | null;
}) {
  if (!citations?.length) return null;

  const unique = [...new Set(citations)];
  const researchBase = ticker
    ? `/research/${encodeURIComponent(ticker)}`
    : "/research";

  return (
    <div className="mt-2" aria-label="Research references">
      <p className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
        Research references
      </p>
      <ul className="mt-1 flex flex-wrap gap-1.5">
        {unique.map((citation) => (
          <li key={citation}>
            <a
              href={`${researchBase}#${SECTION_HREF[citation]}`}
              className="inline-block rounded border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--fg)] hover:bg-[var(--surface-2)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              {citation}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
