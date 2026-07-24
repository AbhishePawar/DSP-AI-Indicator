import { IssueTrackerWorkspace } from "@/components/beta/BetaWorkspaces";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function BetaIssuesPage() {
  return (
    <div>
      <PageHeader
        title="Issue Tracker"
        description="Open · In Progress · Resolved · Deferred · Duplicate — local beta store only."
      />
      <SectionErrorBoundary title="Issues">
        <IssueTrackerWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
