import type { Metadata } from "next";
import Link from "next/link";

import { MarketingFaqList } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "FAQ",
  description: `Frequently asked questions about ${env.appName}.`,
  alternates: { canonical: "/faq" },
};

export default function MarketingFaqPage() {
  return (
    <div>
      <section className="px-4 py-16 text-center sm:px-6 sm:py-20">
        <h1 className="font-[family-name:var(--font-heading)] text-[clamp(32px,5vw,48px)] font-medium tracking-tight text-[var(--fg)]">
          Frequently asked questions
        </h1>
        <p className="mx-auto mt-3 max-w-md text-[15px] text-[var(--muted)]">
          Research boundaries, architecture, and access.
        </p>
      </section>
      <section className="px-4 pb-20 sm:px-6">
        <MarketingFaqList />
        <p className="mx-auto mt-8 max-w-[680px] text-sm text-[var(--muted)]">
          <Link className="text-[var(--accent)] underline" href="/docs/faq">
            In-app FAQ
          </Link>
          {" · "}
          <Link className="text-[var(--accent)] underline" href="/docs/disclaimer">
            Disclaimer
          </Link>
        </p>
      </section>
    </div>
  );
}
