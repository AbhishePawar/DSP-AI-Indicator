import type { Metadata } from "next";
import Link from "next/link";

import { FAQ_ITEMS, Section } from "@/components/marketing";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "FAQ",
  description: `Frequently asked questions about ${env.appName}.`,
  alternates: { canonical: "/faq" },
};

export default function MarketingFaqPage() {
  return (
    <Section
      id="faq"
      eyebrow="FAQ"
      title="Frequently asked questions"
      lead="Research boundaries, architecture, and access — answered plainly."
    >
      <dl className="mx-auto max-w-3xl space-y-8">
        {FAQ_ITEMS.map((item) => (
          <div key={item.q}>
            <dt className="font-[family-name:var(--font-display)] text-xl font-medium tracking-tight">
              {item.q}
            </dt>
            <dd className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
              {item.a}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-10 text-sm text-[var(--muted)]">
        More product docs:{" "}
        <Link className="text-[var(--accent)] underline" href="/docs/faq">
          in-app FAQ
        </Link>
        {" · "}
        <Link className="text-[var(--accent)] underline" href="/docs/disclaimer">
          disclaimer
        </Link>
        {" · "}
        <Link className="text-[var(--accent)] underline" href="/contact">
          contact
        </Link>
      </p>
    </Section>
  );
}
