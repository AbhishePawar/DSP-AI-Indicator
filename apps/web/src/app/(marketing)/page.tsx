import type { Metadata } from "next";

import { MarketingLanding } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: `${env.appName} — Complex Analysis. Simple Decisions.`,
  alternates: { canonical: "/" },
};

/** RC3-002 — No fake free Offer. Pricing is not publicly purchasable on this release. */
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: env.appName,
  applicationCategory: "FinanceApplication",
  operatingSystem: "Web",
  description:
    "Institutional investment research platform with explainability, governed AI, and Research Mode. Access is administrator-provisioned; pricing is not offered as a public checkout on this release.",
};

export default function MarketingHomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <MarketingLanding />
    </>
  );
}
