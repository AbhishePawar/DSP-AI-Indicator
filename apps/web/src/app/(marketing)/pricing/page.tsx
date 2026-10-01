import type { Metadata } from "next";
import Link from "next/link";

import {
  COMMERCIAL_PRICING_DISCLOSURE,
  FEATURE_MATRIX_ROWS,
  PRODUCT_EDITIONS,
  SUPPORT_CONTACT,
} from "@/lib/commercial";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${env.appName} illustrative product editions — not a live commercial offer.`,
  alternates: { canonical: "/pricing" },
};

function formatPrice(edition: (typeof PRODUCT_EDITIONS)[number]): string {
  if (edition.monthlyPriceUsd === null) return "Contact administrator for access";
  if (edition.monthlyPriceUsd === 0) {
    return "Illustrative · not available for purchase";
  }
  return `Illustrative · $${edition.monthlyPriceUsd}/mo · not available for purchase`;
}

export default function MarketingPricingPage() {
  return (
    <div>
      <section className="px-4 py-16 text-center sm:px-6 sm:py-20">
        <h1 className="font-[family-name:var(--font-heading)] text-[clamp(32px,5vw,52px)] font-medium tracking-tight text-[var(--fg)]">
          Product editions
        </h1>
        <p className="mx-auto mt-4 max-w-md text-base text-[var(--muted)]">
          Packaging for planning only. These plans are not available for public purchase.
        </p>
      </section>
      <section className="px-4 pb-16 sm:px-6">
      <p
        role="note"
        className="mx-auto mb-6 max-w-[920px] rounded-[14px] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--muted)]"
      >
        {COMMERCIAL_PRICING_DISCLOSURE}
      </p>
      <ul className="mx-auto grid max-w-[920px] gap-5 lg:grid-cols-3">
        {PRODUCT_EDITIONS.map((edition) => (
          <li
            key={edition.id}
            className={`rounded-2xl border p-7 ${
              edition.id === "professional"
                ? "border-[rgba(124,106,247,0.4)] bg-[linear-gradient(160deg,rgba(124,106,247,0.12),rgba(45,212,191,0.06))]"
                : "border-[var(--border)] bg-[var(--surface)]"
            }`}
          >
            <p className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
              {edition.name}
            </p>
            <p className="mt-3 font-[family-name:var(--font-heading)] text-4xl font-medium text-[var(--fg)]">
              {formatPrice(edition)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">{edition.tagline}</p>
            <p className="mt-2 text-sm text-[var(--muted)]">{edition.audience}</p>
            <p className="mt-3 text-sm text-[var(--muted)]">
              Illustrative seats: {edition.seatsIncluded}
              {edition.trialDays > 0
                ? ` · Illustrative trial length: ${edition.trialDays} days`
                : null}
            </p>
            <Link
              href={edition.monthlyPriceUsd === 0 ? "/register" : "/contact"}
              className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-[10px] bg-[var(--c-dsp)] px-4 text-sm font-medium text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            >
              {edition.monthlyPriceUsd === 0
                ? "Create account"
                : edition.monthlyPriceUsd === null
                  ? "Contact sales"
                  : "Request access"}
            </Link>
            <p className="mt-2 text-xs text-[var(--muted)]">
              This does not start a payment. Purchase is not available on this release.
            </p>
          </li>
        ))}
      </ul>

      <h3 className="mt-12 font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight">
        Capability matrix (illustrative)
      </h3>
      <p className="mt-2 max-w-2xl text-sm text-[var(--muted)]">
        Matrix cells describe intended packaging — not live entitlements or
        checkout. Features marked Yes may still require administrator
        provisioning.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <caption className="sr-only">
            Illustrative feature packaging by product edition
          </caption>
          <thead>
            <tr className="border-b border-[var(--border)]">
              <th scope="col" className="py-2 pr-3 font-medium">
                Capability
              </th>
              {PRODUCT_EDITIONS.map((e) => (
                <th scope="col" key={e.id} className="px-2 py-2 font-medium">
                  {e.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FEATURE_MATRIX_ROWS.map((row) => (
              <tr key={row.key} className="border-b border-[var(--border)]">
                <th scope="row" className="py-2 pr-3 font-normal text-[var(--fg)]">
                  {row.label}
                </th>
                {PRODUCT_EDITIONS.map((edition) => {
                  const value = edition.features[row.key];
                  const label =
                    typeof value === "boolean"
                      ? value
                        ? "Planned"
                        : "Not in edition"
                      : String(value);
                  return (
                    <td key={edition.id} className="px-2 py-2 text-[var(--muted)]">
                      {label}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-8 text-sm text-[var(--muted)]">
        {SUPPORT_CONTACT.channelsPublished ? (
          <>
            Sales:{" "}
            <a
              className="text-[var(--accent)] underline"
              href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
            >
              {SUPPORT_CONTACT.salesEmail}
            </a>
            {" · "}
          </>
        ) : (
          <>{SUPPORT_CONTACT.unpublishedNote}{" · "}</>
        )}
        <Link className="text-[var(--accent)] underline" href="/login">
          Sign in
        </Link>
        {" · "}
        <Link className="text-[var(--accent)] underline" href="/register">
          Create account
        </Link>
      </p>
      </section>
    </div>
  );
}
