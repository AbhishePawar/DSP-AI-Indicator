import { PageHeader } from "@/components/layout/PageHeader";
import { PostLaunchReportWorkspace } from "@/components/launch/PublicLaunch";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function LaunchReportPage() {
  return (
    <div>
      <PageHeader
        title="Post Launch Review"
        description="Outcome, known issues, lessons learned, and future roadmap for Web 1.0.0."
      />
      <SectionErrorBoundary title="Post-launch report">
        <PostLaunchReportWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
