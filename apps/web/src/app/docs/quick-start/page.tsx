import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { SAMPLE_ANALYSIS_SYMBOL, SUPPORT_CONTACT } from "@/lib/commercial";

export default function QuickStartPage() {
  return (
    <div>
      <PageHeader
        title="Quick start"
        description="First successful research session in under ten minutes."
      />
      <ol className="list-decimal space-y-3 pl-5 text-sm text-[var(--muted)]">
        <li>
          <Link className="text-[var(--accent)] underline" href="/login">
            Sign in
          </Link>{" "}
          with your organisation credentials (or closed-beta invite).
        </li>
        <li>
          Complete the welcome tour (skip anytime; restart from Beta hub).
        </li>
        <li>
          Open{" "}
          <Link
            className="text-[var(--accent)] underline"
            href={`/analysis?symbol=${SAMPLE_ANALYSIS_SYMBOL}`}
          >
            Company Analysis ({SAMPLE_ANALYSIS_SYMBOL})
          </Link>
          .
        </li>
        <li>
          Acknowledge the research disclaimer on first report generation.
        </li>
        <li>
          Review Summary → Ratings → Explainability → Valuation Transparency →
          Buffett Indicator. Treat Unavailable as honest missing data.
        </li>
        <li>
          Send Feedback if something is unclear — never paste secrets or
          holdings.
        </li>
      </ol>
      <p className="mt-6 text-sm text-[var(--muted)]">
        Need help?{" "}
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
