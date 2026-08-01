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
  description: `${env.appName} editions and pricing — research use; not investment advice.`,
  alternates: { canonical: "/pricing" },
};

function formatPrice(edition: (typeof PRODUCT_EDITIONS)[number]): string {
  if (edition.monthlyPriceUsd === null) return "Contact for access";
  if (edition.monthlyPriceUsd === 0) return "Illustrative · Free tier sketch";
  return `Illustrative · $${edition.monthlyPriceUsd}/mo · $${edition.annualPriceUsd}/yr`;
}

export default function MarketingPricingPage() {
  return (
    <Section
      id="pricing"
      eyebrow="Pricing"
      title="Product editions"
      lead={`${env.appName} commercial packaging for research use. Trial and subscription details are summarised in FAQ.`}
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
            <p className="mt-3 text-sm">
              Illustrative trial:{" "}
              {edition.trialDays > 0 ? `${edition.trialDays} days` : "N/A"} ·
              Seats sketch: {edition.seatsIncluded}
            </p>
          </li>
        ))}
      </ul>

      <h3 className="mt-12 font-[family-name:var(--font-display)] text-2xl font-medium tracking-tight">
        Feature matrix
      </h3>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <caption className="sr-only">
            Feature availability by product edition
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
                    typeof value === "boolean" ? (value ? "Yes" : "No") : String(value);
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
        <Link className="text-[var(--accent)] underline" href="/docs/pricing">
          In-app pricing docs
        </Link>
      </p>
    </Section>
  );
}
