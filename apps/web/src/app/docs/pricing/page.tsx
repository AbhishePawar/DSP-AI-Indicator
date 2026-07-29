import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import {
  FEATURE_MATRIX_ROWS,
  PRODUCT_EDITIONS,
  SUPPORT_CONTACT,
} from "@/lib/commercial";
import { env } from "@/lib/env";

function formatPrice(edition: (typeof PRODUCT_EDITIONS)[number]): string {
  if (edition.monthlyPriceUsd === null) return "Contact sales";
  if (edition.monthlyPriceUsd === 0) return "Free";
  return `$${edition.monthlyPriceUsd}/mo · $${edition.annualPriceUsd}/yr`;
}

export default function PricingPage() {
  return (
    <div>
      <PageHeader
        title="Product editions & pricing"
        description={`${env.appName} commercial packaging (P6.1) — research use; not investment advice.`}
      />
      <p className="mb-4 text-sm text-[var(--muted)]">
        Trial, refund, and subscription terms are summarised in{" "}
        <Link className="text-[var(--accent)] underline" href="/docs/faq">
          FAQ
        </Link>
        . Sales:{" "}
        <a
          className="text-[var(--accent)] underline"
          href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
        >
          {SUPPORT_CONTACT.salesEmail}
        </a>
        .
      </p>
      <div className="grid gap-3 lg:grid-cols-3">
        {PRODUCT_EDITIONS.map((edition) => (
          <Card key={edition.id} className="dsp-interactive">
            <CardHeader title={edition.name} description={edition.tagline} />
            <CardBody className="space-y-2 text-sm">
              <p className="font-[family-name:var(--font-display)] text-lg">
                {formatPrice(edition)}
              </p>
              <p className="text-[var(--muted)]">{edition.audience}</p>
              <p>
                Trial: {edition.trialDays > 0 ? `${edition.trialDays} days` : "N/A"}
              </p>
              <p>
                Seats: {edition.seatsIncluded} · Analyses/mo:{" "}
                {String(edition.analysesPerMonth)} · Exports/mo:{" "}
                {String(edition.exportsPerMonth)}
              </p>
            </CardBody>
          </Card>
        ))}
      </div>

      <h2 className="mt-8 font-[family-name:var(--font-display)] text-xl tracking-tight">
        Feature matrix
      </h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)]">
              <th className="py-2 pr-3">Capability</th>
              {PRODUCT_EDITIONS.map((e) => (
                <th key={e.id} className="py-2 px-2">
                  {e.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FEATURE_MATRIX_ROWS.map((row) => (
              <tr key={row.key} className="border-b border-[var(--border)]">
                <td className="py-2 pr-3">{row.label}</td>
                {PRODUCT_EDITIONS.map((edition) => {
                  const value = edition.features[row.key];
                  const label =
                    typeof value === "boolean"
                      ? value
                        ? "Yes"
                        : "No"
                      : String(value ?? "Unavailable");
                  return (
                    <td key={edition.id} className="py-2 px-2 text-[var(--muted)]">
                      {label}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
