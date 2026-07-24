import Link from "next/link";

import {
  AnalyticsPlaceholderCard,
  BetaDashboardWorkspace,
  FeedbackWorkspace,
} from "@/components/beta/BetaWorkspaces";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function BetaPage() {
  return (
    <div>
      <PageHeader
        title="Private Beta"
        description="Feedback and usability signals — Web 1.0.0 stable; engines unchanged."
      />
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="text-[var(--accent)] underline" href="/beta/issues">
          Issue tracker
        </Link>
        <Link className="text-[var(--accent)] underline" href="/beta/rc">
          RC history
        </Link>
        <Link className="text-[var(--accent)] underline" href="/launch">
          Launch Dashboard
        </Link>
      </div>
      <div className="space-y-8">
        <SectionErrorBoundary title="Beta dashboard">
          <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
            Beta dashboard
          </h2>
          <BetaDashboardWorkspace />
        </SectionErrorBoundary>
        <SectionErrorBoundary title="Feedback workspace">
          <h2 className="font-[family-name:var(--font-display)] text-xl tracking-tight">
            Feedback workspace
          </h2>
          <FeedbackWorkspace />
        </SectionErrorBoundary>
        <SectionErrorBoundary title="Analytics placeholders">
          <AnalyticsPlaceholderCard />
        </SectionErrorBoundary>
      </div>
    </div>
  );
}
