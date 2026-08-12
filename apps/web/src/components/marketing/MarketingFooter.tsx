import Link from "next/link";

import { SUPPORT_CONTACT } from "@/lib/commercial";
import { env } from "@/lib/env";

export function MarketingFooter() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto grid max-w-[72rem] gap-8 px-4 py-12 sm:px-6 md:grid-cols-3">
        <div>
          <p className="font-[family-name:var(--font-display)] text-lg font-medium tracking-tight">
            {env.appName}
          </p>
          <p className="mt-2 max-w-sm text-sm text-[var(--muted)]">
            {env.tagline}. Professional investment research for everyone —
            research use, not investment advice.
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Explore
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/#features"
              >
                Features
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/pricing"
              >
                Pricing
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/faq"
              >
                FAQ
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/about"
              >
                About
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/contact"
              >
                Contact
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
            Legal & access
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/login"
              >
                Sign in
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/docs/disclaimer"
              >
                Research disclaimer
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/docs/privacy"
              >
                Privacy
              </Link>
            </li>
            <li>
              <Link
                className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                href="/docs/terms"
              >
                Terms
              </Link>
            </li>
            <li>
              {SUPPORT_CONTACT.channelsPublished ? (
                <a
                  className="rounded-sm hover:text-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
                >
                  {SUPPORT_CONTACT.salesEmail}
                </a>
              ) : (
                <span className="text-[var(--muted)]">
                  {SUPPORT_CONTACT.unpublishedNote}
                </span>
              )}
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-[var(--border)] px-4 py-4 text-center text-xs text-[var(--muted)] sm:px-6">
        © {new Date().getFullYear()} {env.appName}. Research Mode by default.
        Not a brokerage order router.
      </div>
    </footer>
  );
}
