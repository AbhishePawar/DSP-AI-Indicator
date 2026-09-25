"use client";

import { PageHeader } from "@/components/layout/PageHeader";

export default function ScreeningPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Market Screening"
        description="Certified screening requires an authenticated market-data feed."
      />
      <section className="dsp-card">
        <p className="section-label">Results</p>
        <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
          Screening data unavailable.
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          This release does not publish a certified screening universe. Static
          catalogue ratios are not shown as live financials. Open company
          research from a ticker instead.
        </p>
      </section>
    </div>
  );
}
