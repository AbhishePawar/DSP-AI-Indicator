import type { Metadata } from "next";
import Link from "next/link";

import { Section } from "@/components/marketing";
import { SUPPORT_CONTACT } from "@/lib/commercial";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contact ${env.appName} for research access and programme guidance.`,
  alternates: { canonical: "/contact" },
};

/**
 * RC3-002 — Respect channelsPublished. Never show .example mailto as live contact.
 */
export default function ContactPage() {
  const published = SUPPORT_CONTACT.channelsPublished;

  return (
    <Section
      id="contact"
      eyebrow="Contact"
      title="Talk to the research desk"
      lead="Programme and access guidance for institutional research use. Not a brokerage order desk."
    >
      {published ? (
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
      ) : (
        <div className="max-w-xl space-y-4 text-sm">
          <p
            role="status"
            className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-[var(--muted)]"
          >
            Contact channels are not yet publicly available.
          </p>
          <p className="text-[var(--muted)]">
            {SUPPORT_CONTACT.unpublishedNote}
          </p>
          <dl className="grid gap-4">
            <div>
              <dt className="font-medium text-[var(--fg)]">Platform access</dt>
              <dd className="mt-1 text-[var(--muted)]">
                Existing provisioned users can{" "}
                <Link className="text-[var(--accent)] underline" href="/login">
                  sign in
                </Link>
                . New desks should{" "}
                <Link className="text-[var(--accent)] underline" href="/signup">
                  prepare an access request
                </Link>{" "}
                and contact their programme administrator.
              </dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--fg)]">Documentation</dt>
              <dd className="mt-1 text-[var(--muted)]">
                <Link
                  className="text-[var(--accent)] underline"
                  href={SUPPORT_CONTACT.knowledgeBasePath}
                >
                  Product docs
                </Link>
                {" · "}
                <Link
                  className="text-[var(--accent)] underline"
                  href={SUPPORT_CONTACT.faqPath}
                >
                  FAQ
                </Link>
              </dd>
            </div>
          </dl>
        </div>
      )}
    </Section>
  );
}
