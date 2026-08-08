import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { SUPPORT_CONTACT } from "@/lib/commercial";

export default function SupportPage() {
  return (
    <div>
      <PageHeader
        title="Customer support"
        description="Channels, hours, and severity guidance for DSP AI Indicator (P6.1)."
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardHeader title="Contact" />
          <CardBody className="space-y-2 text-sm text-[var(--muted)]">
            <p>
              Support:{" "}
              <a
                className="text-[var(--accent)] underline"
                href={`mailto:${SUPPORT_CONTACT.email}`}
              >
                {SUPPORT_CONTACT.email}
              </a>
            </p>
            <p>
              Security:{" "}
              <a
                className="text-[var(--accent)] underline"
                href={`mailto:${SUPPORT_CONTACT.securityEmail}`}
              >
                {SUPPORT_CONTACT.securityEmail}
              </a>
            </p>
            <p>
              Sales:{" "}
              <a
                className="text-[var(--accent)] underline"
                href={`mailto:${SUPPORT_CONTACT.salesEmail}`}
              >
                {SUPPORT_CONTACT.salesEmail}
              </a>
            </p>
            <p>Hours: {SUPPORT_CONTACT.hours}</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Knowledge base" />
          <CardBody className="space-y-2 text-sm">
            <Link className="block text-[var(--accent)] underline" href="/docs">
              Documentation index
            </Link>
            <Link className="block text-[var(--accent)] underline" href="/docs/faq">
              FAQ
            </Link>
            <Link
              className="block text-[var(--accent)] underline"
              href="/docs/user-guide"
            >
              User guide
            </Link>
            <Link
              className="block text-[var(--accent)] underline"
              href="/docs/quick-start"
            >
              Quick start
            </Link>
            <p className="text-[var(--muted)]">{SUPPORT_CONTACT.statusPageNote}</p>
          </CardBody>
        </Card>
      </div>

      <h2 className="mt-8 font-[family-name:var(--font-display)] text-xl tracking-tight">
        Severity & response targets
      </h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
        <li>
          <strong className="text-[var(--fg)]">S1 Critical</strong> — service
          down / security breach · acknowledge ≤1h · continuous work (Enterprise SLA)
        </li>
        <li>
          <strong className="text-[var(--fg)]">S2 High</strong> — major feature
          impaired · acknowledge ≤4 business hours
        </li>
        <li>
          <strong className="text-[var(--fg)]">S3 Medium</strong> — partial
          degradation · acknowledge ≤1 business day
        </li>
        <li>
          <strong className="text-[var(--fg)]">S4 Low</strong> — questions /
          cosmetic · acknowledge ≤2 business days
        </li>
      </ul>
      <p className="mt-4 text-sm text-[var(--muted)]">
        Escalate via in-app Feedback (bug report) then email support. Security
        issues: contact security@ directly — do not include secrets in tickets.
      </p>
    </div>
  );
}
