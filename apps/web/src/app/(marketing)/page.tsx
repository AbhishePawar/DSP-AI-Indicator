import type { Metadata } from "next";

import { MarketingLanding } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: `${env.appName} — Complex Analysis. Simple Decisions.`,
  alternates: { canonical: "/" },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: env.appName,
  applicationCategory: "FinanceApplication",
  operatingSystem: "Web",
  description:
    "Institutional investment research platform with explainability, governed AI, and Research Mode.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
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
