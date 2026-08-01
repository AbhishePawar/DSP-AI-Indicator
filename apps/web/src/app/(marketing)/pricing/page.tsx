import type { Metadata } from "next";
import Link from "next/link";

import { Section } from "@/components/marketing";
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
    <Section
      id="pricing"
      eyebrow="Pricing"
      title="Product editions"
      lead={`${env.appName} edition packaging is shown for planning only. These plans are not available for public purchase on this release.`}
    >
      <p
        role="note"
        className="mb-6 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--muted)]"
      >
        {COMMERCIAL_PRICING_DISCLOSURE}
      </p>
      <ul className="grid gap-6 lg:grid-cols-3">
        {PRODUCT_EDITIONS.map((edition) => (
          <li
            key={edition.id}
            className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] p-6"
          >
            <h3 className="font-[family-name:var(--font-display)] text-xl font-medium">
              {edition.name}
            </h3>
            <p className="mt-1 text-sm text-[var(--muted)]">{edition.tagline}</p>
            <p className="mt-4 font-[family-name:var(--font-display)] text-2xl font-medium">
              {formatPrice(edition)}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)]">{edition.audience}</p>
            <p className="mt-3 text-sm text-[var(--muted)]">
              Illustrative seats: {edition.seatsIncluded}
              {edition.trialDays > 0
                ? ` · Illustrative trial length: ${edition.trialDays} days`
                : null}
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
        <Link className="text-[var(--accent)] underline" href="/signup">
          Request access
        </Link>
      </p>
    </Section>
  );
}
