import Link from "next/link";

import { ReleaseCandidateWorkspace } from "@/components/beta/BetaWorkspaces";
import { PageHeader } from "@/components/layout/PageHeader";
import { SectionErrorBoundary } from "@/components/reliability/GlobalErrorBoundary";

export default function BetaRcPage() {
  return (
    <div>
      <PageHeader
        title="Release Candidate"
        description="Web 0.9.5 stabilization — score, resolutions, version freeze, a11y & cross-browser matrices. No engine changes."
        actions={
          <div className="flex flex-wrap gap-2 text-sm">
            <Link className="text-[var(--accent)] underline" href="/beta">
              Beta
            </Link>
            <Link className="text-[var(--accent)] underline" href="/beta/issues">
              Issues
            </Link>
            <Link className="text-[var(--accent)] underline" href="/launch">
              Launch
            </Link>
          </div>
        }
      />
      <SectionErrorBoundary title="RC dashboard">
        <ReleaseCandidateWorkspace />
      </SectionErrorBoundary>
    </div>
  );
}
