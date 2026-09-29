import type { Metadata } from "next";
import Link from "next/link";

import { SUPPORT_CONTACT } from "@/lib/commercial";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Contact",
  description: `Contact ${env.appName} for research access and programme guidance.`,
  alternates: { canonical: "/contact" },
};

export default function ContactPage() {
  const published = SUPPORT_CONTACT.channelsPublished;

  return (
    <div>
      <section className="px-4 py-16 text-center sm:px-6 sm:py-20">
        <h1 className="font-[family-name:var(--font-heading)] text-[clamp(32px,5vw,48px)] font-medium tracking-tight text-[var(--fg)]">
          Get in touch
        </h1>
        <p className="mx-auto mt-3 max-w-md text-[15px] text-[var(--muted)]">
          Programme and access guidance. Not a brokerage order desk.
        </p>
      </section>
      <section className="mx-auto grid max-w-[680px] gap-10 px-4 pb-20 sm:px-6 md:grid-cols-2">
        <div>
          <h2 className="font-[family-name:var(--font-heading)] text-[22px] font-medium text-[var(--fg)]">
            Contact
          </h2>
          {published ? (
            <dl className="mt-5 space-y-4 text-sm">
              <div>
                <dt className="font-mono text-[11px] uppercase tracking-wider text-[var(--muted)]">
                  Support
                </dt>
                <dd className="mt-1">
                  <a className="text-[var(--accent)] underline" href={`mailto:${SUPPORT_CONTACT.email}`}>
                    {SUPPORT_CONTACT.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="font-mono text-[11px] uppercase tracking-wider text-[var(--muted)]">
                  Sales
                </dt>
                <dd className="mt-1">
                  <a className="text-[var(--accent)] underline" href={`mailto:${SUPPORT_CONTACT.salesEmail}`}>
                    {SUPPORT_CONTACT.salesEmail}
                  </a>
                </dd>
              </div>
            </dl>
          ) : (
            <p role="status" className="mt-5 text-sm leading-relaxed text-[var(--muted)]">
              {SUPPORT_CONTACT.unpublishedNote}
            </p>
          )}
        </div>
        <div className="space-y-4 text-sm text-[var(--muted)]">
          <h2 className="font-[family-name:var(--font-heading)] text-[22px] font-medium text-[var(--fg)]">
            Access
          </h2>
          <p>
            Existing users can{" "}
            <Link className="text-[var(--accent)] underline" href="/login">
              sign in
            </Link>
            . New users can{" "}
            <Link className="text-[var(--accent)] underline" href="/register">
              create an account
            </Link>
            {" or "}
            <Link className="text-[var(--accent)] underline" href="/signup">
              request access
            </Link>
            .
          </p>
          <p>
            <Link className="text-[var(--accent)] underline" href={SUPPORT_CONTACT.knowledgeBasePath}>
              Product docs
            </Link>
            {" · "}
            <Link className="text-[var(--accent)] underline" href={SUPPORT_CONTACT.faqPath}>
              FAQ
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
