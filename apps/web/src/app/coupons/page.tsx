"use client";

import { FigmaPage, Panel } from "@/components/pages/PagePrimitives";

/**
 * Figma Make `Coupons.tsx` shell. Offers are not invented — this release
 * has no certified public coupon catalogue.
 */
export default function CouponsPage() {
  return (
    <FigmaPage title="Coupons & Offers" subtitle="Administrator-provisioned plans only">
      <Panel title="Offers" padded>
        <h2 className="font-[family-name:var(--font-display)] text-xl font-medium text-[var(--fg)]">
          Offers unavailable.
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--muted)]">
          No certified commercial offer is published on this release. Pricing
          remains administrator-provisioned. Referral totals and claimed
          discounts are not fabricated.
        </p>
      </Panel>
    </FigmaPage>
  );
}
