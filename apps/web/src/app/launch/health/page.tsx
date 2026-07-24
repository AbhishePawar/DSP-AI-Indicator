import { PageHeader } from "@/components/layout/PageHeader";
import { HealthStatusWorkspace } from "@/components/launch/LaunchWorkspaces";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function LaunchHealthPage() {
  return (
    <div>
      <PageHeader
        title="Health Status Workspace"
        description="Build, version, environment, and monitoring placeholders."
      />
      <SectionErrorBoundary title="Health ops section">
        <HealthStatusWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
