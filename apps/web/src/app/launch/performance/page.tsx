import { PageHeader } from "@/components/layout/PageHeader";
import { PerformanceWorkspace } from "@/components/launch/LaunchWorkspaces";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function LaunchPerformancePage() {
  return (
    <div>
      <PageHeader
        title="Performance Workspace"
        description="Client Web Vitals sampling + audit notes. Does not change research engines."
      />
      <SectionErrorBoundary title="Performance section">
        <PerformanceWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
