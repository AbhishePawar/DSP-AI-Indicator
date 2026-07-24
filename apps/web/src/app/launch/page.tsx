import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { LaunchDashboardWorkspace } from "@/components/launch/PublicLaunch";
import { LaunchReadinessWorkspace } from "@/components/launch/LaunchWorkspaces";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function LaunchPage() {
  return (
    <div>
      <PageHeader
        title="Launch Dashboard"
        description="Web 1.0.0 public release — deployment status, quality gates, and release health. No investment logic changes."
      />
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="text-[var(--accent)] underline" href="/launch/report">
          Post-launch report
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch/performance">
          Performance
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch/health">
          Health & build
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch/checklist">
          QA checklists
        </Link>
        <Link className="text-[var(--accent)] underline" href="/docs">
          Documentation
        </Link>
        <Link className="text-[var(--accent)] underline" href="/health">
          API Health
        </Link>
      </div>
      <SectionErrorBoundary title="Launch dashboard">
        <LaunchDashboardWorkspace />
      </SectionErrorBoundary>
      <section className="mt-10 space-y-4" aria-labelledby="readiness-detail">
        <h2 id="readiness-detail" className="font-[family-name:var(--font-display)] text-xl">
          Readiness detail
        </h2>
        <SectionErrorBoundary title="Launch readiness section">
          <LaunchReadinessWorkspace />
        </SectionErrorBoundary>
      </section>
    </div>
  );
}
