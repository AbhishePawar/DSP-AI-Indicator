import type { Metadata } from "next";
import Link from "next/link";

import { Section } from "@/components/marketing";
import { SUPPORT_CONTACT } from "@/lib/commercial";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contact ${env.appName} for research access, sales, and support.`,
  alternates: { canonical: "/contact" },
};

export default function ContactPage() {
  return (
    <Section
      id="contact"
      eyebrow="Contact"
      title="Talk to the research desk"
      lead="Sales and support contacts for editions, trials, and institutional deployment. Not a brokerage order desk."
    >
      <dl className="grid max-w-xl gap-6 text-sm">
        <div>
          <dt className="font-medium text-[var(--fg)]">Sales</dt>
          <dd className="mt-1 text-[var(--muted)]">
            <a
              className="text-[var(--accent)] underline"
              href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
            >
              {SUPPORT_CONTACT.salesEmail}
            </a>
          </dd>
        </div>
        <div>
          <dt className="font-medium text-[var(--fg)]">Support</dt>
          <dd className="mt-1 text-[var(--muted)]">
            <a
              className="text-[var(--accent)] underline"
              href={`mailto:${SUPPORT_CONTACT.email}`}
            >
              {SUPPORT_CONTACT.email}
            </a>
          </dd>
        </div>
        <div>
          <dt className="font-medium text-[var(--fg)]">Platform access</dt>
          <dd className="mt-1 text-[var(--muted)]">
            Existing users can{" "}
            <Link className="text-[var(--accent)] underline" href="/login">
              sign in
            </Link>
            . New desks should email sales for edition guidance.
          </dd>
        </div>
      </dl>
    </Section>
  );
}
