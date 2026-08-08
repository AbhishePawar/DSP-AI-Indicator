import type { Metadata } from "next";
import type { ReactNode } from "react";

import { MarketingShell } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: {
    default: `${env.appName} — Institutional Investment Research`,
    template: `%s · ${env.appName}`,
  },
  description:
    "DSP AI Indicator is an institutional investment research platform with evidence-first analysis, explainability, governed AI, and Research Mode by default.",
  openGraph: {
    title: `${env.appName} — Institutional Investment Research`,
    description:
      "Complex Analysis. Simple Decisions. Evidence-first research with governed AI.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: env.appName,
    description: env.tagline,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return <MarketingShell>{children}</MarketingShell>;
}
