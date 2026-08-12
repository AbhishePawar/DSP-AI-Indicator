import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { SUPPORT_CONTACT } from "@/lib/commercial";

const FAQS = [
  {
    q: "Is DSP personalised investment advice?",
    a: "No. Reports are research and educational. See the Investment Research Disclaimer.",
  },
  {
    q: "How do trials work?",
    a: "Professional includes a 14-day trial; Enterprise may offer up to 30 days. Research edition is free with usage limits.",
  },
  {
    q: "Can I upgrade or downgrade?",
    a: "Contact sales@. Changes take effect at the next billing cycle unless otherwise contracted.",
  },
  {
    q: "What is the refund policy?",
    a: "Unused prepaid Professional annual seats may be refunded within 14 days of purchase if no Enterprise features were provisioned. Contact support@.",
  },
  {
    q: "How do I migrate from closed beta?",
    a: "Export beta snapshots, confirm invites, then disable closed-beta flags for production. See docs/commercial/BETA_TO_PRODUCTION_MIGRATION.md.",
  },
  {
    q: "Where is the knowledge base?",
    a: "Start at /docs — quick start, user guide, FAQ, pricing, and support.",
  },
] as const;

export default function FaqPage() {
  return (
    <div>
      <PageHeader
        title="FAQ"
        description="Commercial and product questions for DSP AI Indicator."
      />
      <div className="space-y-4">
        {FAQS.map((item) => (
          <section key={item.q}>
            <h2 className="font-[family-name:var(--font-display)] text-lg tracking-tight">
              {item.q}
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{item.a}</p>
          </section>
        ))}
      </div>
      <p className="mt-8 text-sm text-[var(--muted)]">
        More:{" "}
        <Link className="text-[var(--accent)] underline" href="/docs/support">
          Support
        </Link>{" "}
        ·{" "}
        <a
          className="text-[var(--accent)] underline"
          href={`mailto:${SUPPORT_CONTACT.email}`}
        >
          {SUPPORT_CONTACT.email}
        </a>
      </p>
    </div>
  );
}
