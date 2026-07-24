import { PageHeader } from "@/components/layout/PageHeader";
import { LaunchChecklistWorkspace } from "@/components/launch/LaunchWorkspaces";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function LaunchChecklistPage() {
  return (
    <div>
      <PageHeader
        title="Launch Checklist"
        description="Smoke, regression, a11y, performance, responsive, security, browser, release gates."
      />
      <SectionErrorBoundary title="Checklist section">
        <LaunchChecklistWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
