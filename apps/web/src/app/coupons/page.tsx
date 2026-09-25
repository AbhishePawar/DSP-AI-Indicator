"use client";

import { PageHeader } from "@/components/layout/PageHeader";

export default function CouponsPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Coupons & Offers"
        description="Plan offers are provisioned by administrators. This page does not invent discounts."
      />
      <section className="dsp-card">
        <p className="section-label">Offers</p>
        <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--fg)]">
          Offers unavailable.
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          No certified commercial offer is published on this release. Pricing
          remains administrator-provisioned. Referral totals and claimed
          discounts are not fabricated.
        </p>
      </section>
    </div>
  );
}
